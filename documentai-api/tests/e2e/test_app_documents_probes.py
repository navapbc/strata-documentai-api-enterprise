"""Synthetic document testing

Each case uploads a committed synthetic document (see
tests/helpers/fixtures/probe-documents/README.md for the KF issue table -
numbered by tenant edge case - and fixture provenance) and asserts the behavior
the tenant spec says
the input SHOULD produce - not the behavior the API produces today. Cases
tagged with an issue id are EXPECTED TO FAIL (plain red, no xfail) until the
corresponding gate is implemented; untagged cases are green controls. Cases the
tenant has ruled out of scope are e2e_enabled=false in expected.json and are not
collected - the fixture and spec stay committed for the record.

Every case also records the observed 2026-07 behavior in expected.json; it is
echoed into the assertion message so a red test distinguishes "still failing
the known way" from "failing a NEW way" (drift) at a glance.

Assertions available per case, all collected before failing so one message
shows every violation:

- allowedResponseCodes / forbiddenResponseCodes (forbidden is the spec floor
  for anomalies the tenant code table has no code for yet: never 000)
- matchedDocumentClass
- requiredFields (not an assertion: seeds a payslip extraction rule with these
  requiredFields around exactly this case via the payslip_extraction_rule
  fixture below - KF-8a pairs it with missingRequiredFieldListContains, KF-7
  uses it so faint-but-present required fields are exercised against the gate)
- missingRequiredFieldListContains (KF-8a/8c: absent fields must be reported)
- emptyFields (KF-8b: absent fields must not be hallucinated)
- fieldEquals (KF-9: page-2-only values prove multi-page extraction)
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import requests

PROBE_DOCS_DIR = Path(__file__).parent.parent / "helpers" / "fixtures" / "probe-documents"
EXPECTED = PROBE_DOCS_DIR / "expected.json"

# Degraded inputs take BDA noticeably longer than the clean test-documents set.
# Individual cases can override via "timeoutSeconds" in expected.json (e.g. the
# password PDF, where the known failure mode is an indefinite hang).
POLL_TIMEOUT = 300
POLL_INTERVAL = 3

# Statuses that terminate a job without necessarily writing a responseCode.
# The primary terminal signal is a non-null responseCode (it only appears once
# the v1 response is persisted); jobStatus is the fallback for legacy paths.
TERMINAL_JOB_STATUSES = {
    "completed",
    "failed",
    "error",
    "rejected",
    "not_supported",
    "ai_consent_declined",
    "conversion_failed",
    "deleted",
}

# Sentinel: distinguish "expected.json omits matchedDocumentClass" (don't
# assert on class) from an explicit null (assert the class is null).
_UNSET = object()


@dataclass
class ProbeOutcome:
    job_id: str
    http_status: int  # status of the last poll
    body: dict  # last poll body (error payload when http_status >= 500)
    completed: bool  # reached a terminal state before the timeout

    def describe(self) -> str:
        return (
            f"jobId={self.job_id} http={self.http_status} "
            f"jobStatus={self.body.get('jobStatus')} "
            f"responseCode={self.body.get('responseCode')} "
            f"detail={self.body.get('detail')}"
        )


@dataclass
class ProbeCase:
    file_path: Path
    content_type: str
    category: str | None
    issue: str | None
    allowed_response_codes: list[str] | None
    forbidden_response_codes: list[str] | None
    matched_document_class: object = _UNSET
    required_fields: list[str] = field(default_factory=list)
    missing_required_contains: list[str] = field(default_factory=list)
    empty_fields: list[str] = field(default_factory=list)
    field_equals: dict = field(default_factory=dict)
    observed: str | None = None
    timeout: int = POLL_TIMEOUT

    def spec_summary(self) -> str:
        if self.allowed_response_codes is not None:
            return f"responseCode in {self.allowed_response_codes}"
        return f"responseCode NOT in {self.forbidden_response_codes}"


PAYSLIP_DOCUMENT_CLASS = "Payslip"


@pytest.fixture(autouse=True)
def payslip_extraction_rule(request, api_key, e2e_tenant_id):
    """Seed the payslip extraction rule for cases that declare requiredFields.

    Without a rule, apply_extraction_rules returns early and the 101 gate is
    unreachable - the KF-8 cases would stay red even after the API is fixed.
    The gate reads per-tenant rules from the extraction-rules table, so the
    rule is a test precondition, not tenant state we can assume exists.

    Seeding is opt-in via the case's requiredFields key (KF-8a asserts those
    fields come back as missing; KF-7 has them present-but-faint and asserts
    they do NOT trip 101). A rule marks fields required for EVERY payslip the
    tenant uploads, so an always-on rule turns the green payslip controls
    (clean scan, mixed-pages PDF, KF-17, the KF-5 declared-category guard)
    into 101s. Tests run sequentially within an xdist worker and each worker
    has its own tenant, so seeding before / deleting after one case cannot
    leak elsewhere.

    Depends on api_key for its session-level env setup (EXTRACTION_RULES_
    TABLE_NAME et al. are restored there and the config cache is cleared).
    """
    callspec = getattr(request.node, "callspec", None)
    case = callspec.params.get("case") if callspec else None
    required_fields = case.required_fields if case else []
    if not required_fields:
        yield
        return

    import documentai_api
    from documentai_api.utils import extraction_rules

    labels_path = Path(documentai_api.__file__).parent / "config" / "field_labels" / "payslip.json"
    all_fields = list(json.loads(labels_path.read_text()).keys())
    optional_fields = [f for f in all_fields if f not in required_fields]

    extraction_rules.upsert_rule(
        tenant_id=e2e_tenant_id,
        document_type=PAYSLIP_DOCUMENT_CLASS,
        required_fields=required_fields,
        optional_fields=optional_fields,
    )
    try:
        yield
    finally:
        extraction_rules.delete_rule(e2e_tenant_id, PAYSLIP_DOCUMENT_CLASS)


def load_probe_cases() -> list:
    cases = json.loads(EXPECTED.read_text())
    params = []
    for filename, expected in cases.items():
        if filename == "//" or not expected.get("e2e_enabled", False):
            continue
        issue = expected.get("issue")
        params.append(
            pytest.param(
                ProbeCase(
                    file_path=PROBE_DOCS_DIR / filename,
                    content_type=expected["content_type"],
                    category=expected.get("category"),
                    issue=issue,
                    allowed_response_codes=expected.get("allowedResponseCodes"),
                    forbidden_response_codes=expected.get("forbiddenResponseCodes"),
                    matched_document_class=expected.get("matchedDocumentClass", _UNSET),
                    required_fields=expected.get("requiredFields", []),
                    missing_required_contains=expected.get("missingRequiredFieldListContains", []),
                    empty_fields=expected.get("emptyFields", []),
                    field_equals=expected.get("fieldEquals", {}),
                    observed=expected.get("observed"),
                    timeout=expected.get("timeoutSeconds", POLL_TIMEOUT),
                ),
                id=f"{issue or 'CTRL'}:{filename}",
            )
        )
    return params


def _upload(base_url, api_key, file_path, content_type, category=None):
    data = {"category": category} if category else None
    with file_path.open("rb") as f:
        return requests.post(
            f"{base_url}/v1/documents",
            headers={"API-Key": api_key},
            files={"file": (file_path.name, f, content_type)},
            data=data,
            timeout=30,
        )


def _upload_and_poll(
    base_url, api_key, file_path, content_type, category=None, timeout=POLL_TIMEOUT
) -> ProbeOutcome:
    """Upload a document and poll until a terminal state, a 5xx, or the timeout.

    Unlike test_app_documents._upload_and_wait, a GET 5xx is returned as a
    terminal outcome rather than failing the test mid-poll: several spec cases
    currently die with HTTP 500 "Failed to retrieve results", and the outcome
    (including the error detail) belongs in the assertion message.
    """
    response = _upload(base_url, api_key, file_path, content_type, category)
    assert response.status_code == 202, f"upload failed {response.status_code}: {response.text}"
    job_id = response.json()["jobId"]

    http_status, body = 0, {}
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        # Without include_extracted_data the API serves the persisted v1
        # response, whose field values are always "<redacted>" - fieldEquals
        # (KF-9) and emptyFields (KF-8b) can only assert against real values.
        r = requests.get(
            f"{base_url}/v1/documents/{job_id}",
            headers={"API-Key": api_key},
            params={"include_extracted_data": "true"},
            timeout=30,
        )
        http_status = r.status_code
        try:
            body = r.json()
        except ValueError:
            body = {}

        if http_status >= 500:
            return ProbeOutcome(job_id, http_status, body, completed=False)
        assert http_status == 200, f"poll failed {http_status}: {r.text}"

        if (
            body.get("responseCode") is not None
            or body.get("completedAt") is not None
            or (body.get("jobStatus") or "").lower() in TERMINAL_JOB_STATUSES
        ):
            return ProbeOutcome(job_id, http_status, body, completed=True)

        time.sleep(POLL_INTERVAL)

    return ProbeOutcome(job_id, http_status, body, completed=False)


def _lookup_field(fields: dict, path: str):
    """Resolve 'Group.Leaf' or 'Leaf' in the nested v1 fields payload.

    Returns the leaf dict ({"value": ..., "confidence": ...}) or None if the
    field is absent entirely.
    """
    node = fields
    for part in path.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node if isinstance(node, dict) and "value" in node else None


def _check_case(case: ProbeCase, outcome: ProbeOutcome) -> list[str]:
    """Collect every spec violation so one failure message shows them all."""
    violations = []

    response_code = outcome.body.get("responseCode")
    if case.allowed_response_codes is not None and response_code not in case.allowed_response_codes:
        violations.append(
            f"spec expects responseCode in {case.allowed_response_codes}, got {response_code}"
        )
    if case.forbidden_response_codes is not None and response_code in case.forbidden_response_codes:
        violations.append(
            f"spec forbids responseCode {case.forbidden_response_codes} "
            f"(anomaly must not validate clean), got {response_code}"
        )

    if case.matched_document_class is not _UNSET:
        actual_class = outcome.body.get("matchedDocumentClass")
        if actual_class != case.matched_document_class:
            violations.append(
                f"expected matchedDocumentClass {case.matched_document_class}, got {actual_class}"
            )

    if case.missing_required_contains:
        reported = outcome.body.get("missingRequiredFieldList") or []
        absent = [name for name in case.missing_required_contains if name not in reported]
        if absent:
            violations.append(
                f"missingRequiredFieldList must report {absent}, got {reported or None}"
            )

    fields = outcome.body.get("fields") or {}
    for path in case.empty_fields:
        leaf = _lookup_field(fields, path)
        if leaf is not None and leaf.get("value") not in ("", None):
            violations.append(
                f"field {path} is absent from the document but was returned as "
                f"{leaf.get('value')!r} at confidence {leaf.get('confidence')} (hallucination)"
            )
    for path, expected_value in case.field_equals.items():
        leaf = _lookup_field(fields, path)
        actual = leaf.get("value") if leaf else None
        if actual != expected_value:
            violations.append(f"expected field {path} == {expected_value!r}, got {actual!r}")

    return violations


def _fail_message(case: ProbeCase, outcome: ProbeOutcome, violations: list[str]) -> str:
    tag = f"[{case.issue}] " if case.issue else ""
    lines = [f"{tag}{case.file_path.name}: " + "; ".join(violations), outcome.describe()]
    if case.observed:
        actual = outcome.body.get("responseCode")
        drift = "" if actual is None else " (compare before concluding this is the known failure)"
        lines.append(f"known 2026-07 behavior: {case.observed}{drift}")
    return "\n".join(lines)


@pytest.mark.parametrize("case", load_probe_cases())
def test_probe_document(case, base_url, api_key):
    outcome = _upload_and_poll(
        base_url, api_key, case.file_path, case.content_type, case.category, timeout=case.timeout
    )
    if not outcome.completed:
        pytest.fail(
            _fail_message(
                case,
                outcome,
                [
                    f"expected a graceful terminal outcome ({case.spec_summary()}) but the job "
                    f"never reached one within {case.timeout}s"
                ],
            )
        )

    violations = _check_case(case, outcome)
    if violations:
        pytest.fail(_fail_message(case, outcome, violations))


def test_miscategorized_declared_category(base_url, api_key):
    """KF-5 (declared-category leg) - GREEN regression guard since 2026-07-30.

    A payslip uploaded with category=identity is a categorically impossible
    pairing; the spec's declared-vs-detected comparison should reject it with
    102 MISCATEGORIZED. Through 2026-07-13 the category field was enum-validated
    at upload but otherwise inert and every declared/detected mismatch returned
    000; on 2026-07-30 this pairing returned 102 and the case went green.

    Edge case 5 is out of scope per the 2026-07-30 tenant triage, so the three
    chimera fixtures are e2e_enabled=false in expected.json. This leg is kept
    enabled anyway: it now guards working behavior rather than asserting an
    unimplemented gate.
    """
    outcome = _upload_and_poll(
        base_url,
        api_key,
        PROBE_DOCS_DIR / "synthetic-probe-payslip-clean-scan.jpg",
        "image/jpeg",
        category="identity",
    )
    assert outcome.completed, outcome.describe()
    assert outcome.body.get("responseCode") == "102", (
        f"[KF-5] spec expects 102 MISCATEGORIZED for a payslip declared as identity "
        f"({outcome.describe()}); this passed on 2026-07-30, so a failure here is a "
        f"REGRESSION in the declared-vs-detected category check, not the old known "
        f"failure (which was 000 / Payslip, category inert)"
    )


def test_invalid_category_rejected(base_url, api_key):
    """Control: an unknown category value is rejected at upload with a 422."""
    response = _upload(
        base_url,
        api_key,
        PROBE_DOCS_DIR / "synthetic-probe-payslip-clean-scan.jpg",
        "image/jpeg",
        category="not-a-category",
    )
    assert response.status_code == 422, f"{response.status_code}: {response.text}"
