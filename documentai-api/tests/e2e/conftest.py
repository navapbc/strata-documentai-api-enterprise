# tests/e2e/conftest.py
import os
import secrets
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from documentai_api.logging import get_logger
from documentai_api.services.aws_client_factory import AWSClientFactory
from documentai_api.utils.auth import _hash_key, deactivate_api_key, generate_api_key

E2E_TENANT_BASE = "e2e-test-tenant"
logger = get_logger(__name__)


_E2E_DIR = Path(__file__).parent


@pytest.fixture(scope="session")
def e2e_tenant_id(worker_id):
    """Per-worker tenant so parallel xdist workers don't wipe each other's data.

    `worker_id` is "master" for a serial run, or "gw0"/"gw1"/... under `-n`.
    Each worker creates its key + documents under this tenant and wipes only it.
    """
    return f"{E2E_TENANT_BASE}-{worker_id}"


_COMPARE_RESULTS_DIR = _E2E_DIR / "results" / "extraction_compare"


def pytest_sessionstart(session):
    """Delete stale sidecar JSON files before the run so the summary is clean."""
    if hasattr(session.config, "workerinput"):
        return
    if _COMPARE_RESULTS_DIR.exists():
        shutil.rmtree(_COMPARE_RESULTS_DIR)
    _COMPARE_RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def pytest_sessionfinish(session, exitstatus):
    """Aggregate per-worker eval result files into a single summary.

    Only runs on the controller process (not on xdist workers).
    """
    import json
    from collections import defaultdict

    if hasattr(session.config, "workerinput"):
        return

    worker_files = sorted(
        (f for f in _COMPARE_RESULTS_DIR.glob("*.md") if f.name != "extraction_compare_summary.md"),
        key=lambda f: f.name,
    )
    if not worker_files:
        return

    # aggregate sidecar JSONs — bucket by primary_method for cost comparison
    duration_sums: dict[str, float] = defaultdict(float)
    duration_counts: dict[str, int] = defaultdict(int)
    cost_by_type: dict[str, float] = defaultdict(float)
    # per-primary-method reason totals: {primary_method: {reason: total_cost}}
    reason_totals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    rows = []
    for md_file in worker_files:
        sidecar = _COMPARE_RESULTS_DIR / md_file.with_suffix(".data.json").name
        if not sidecar.exists():
            continue
        data = json.loads(sidecar.read_text())
        filename = data["filename"]
        primary_method = data.get("primary_method", "bda")
        file_cost = sum(data["cost"].values())
        for cost_key, amount in data["cost"].items():
            cost_by_type[cost_key] += amount
        for reason, amount in (data.get("cost_by_reason") or {}).items():
            reason_totals[primary_method][reason] += amount
        for method, secs in data["durations"].items():
            if secs is not None:
                duration_sums[method] += secs
                duration_counts[method] += 1
        rows.append((filename, data["durations"], file_cost))

    avg_durations = {
        method: duration_sums[method] / duration_counts[method]
        for method in duration_sums
    }

    # build summary header
    run_ts = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"# Extraction Compare Results\n", f"\n_Run: {run_ts}_\n"]

    if avg_durations:
        lines.append("\n**Avg Durations**\n")
        for method, avg in sorted(avg_durations.items()):
            lines.append(f"- {method}: {avg:.2f}s")
        lines.append("")

    if cost_by_type:
        total_cost = sum(cost_by_type.values())
        lines.append("\n**Total Cost by Model**\n")
        for cost_key, amount in sorted(cost_by_type.items()):
            lines.append(f"- {cost_key}: ${amount:.6f}")
        lines.append(f"- **total: ${total_cost:.6f}**")
        lines.append("")

    def _cost_compare_section(label: str, primary_method_key: str) -> list[str]:
        totals = reason_totals.get(primary_method_key)
        if not totals:
            return []
        llm = totals.get("llmExtraction", 0.0)
        primary = totals.get("primary", 0.0)
        out = [f"\n**{label}**\n"]
        out.append(f"- {primary_method_key} extraction total: ${primary:.6f}")
        out.append(f"- LLM extraction total: ${llm:.6f}")
        out.append("")
        return out

    lines += _cost_compare_section("BDA vs LLM Cost (docs where primary=bda)", "bda")
    lines += _cost_compare_section("Textract vs LLM Cost (docs where primary=textract)", "textract")

    if rows:
        lines.append("\n| Document | Cost | " + " | ".join(f"{m} duration" for m in sorted(avg_durations)) + " |")
        lines.append("|---" * (2 + len(avg_durations)) + "|")
        for filename, durations, file_cost in rows:
            stem = Path(filename).stem
            link = f"[{filename}]({stem}.md)"
            dur_cells = " | ".join(
                f"{durations.get(m):.2f}s" if durations.get(m) is not None else "-"
                for m in sorted(avg_durations)
            )
            lines.append(f"| {link} | ${file_cost:.6f} | {dur_cells} |")
        lines.append("")

    header = "".join(f"{l}\n" if not l.endswith("\n") else l for l in lines)

    sections = []
    for f in worker_files:
        file_lines = f.read_text().splitlines(keepends=True)
        sections.append("".join(file_lines[1:]))  # skip "_Run: ..." line

    summary = _COMPARE_RESULTS_DIR / "extraction_compare_summary.md"
    summary.write_text(header + "".join(sections))


def pytest_collection_modifyitems(items):
    """Mark tests under tests/e2e/ as e2e so the default suite skips them.

    Also applies flaky(reruns=1) to retry environmental failures (cold starts,
    BDA latency spikes, network blips). Skipped if the test already has a flaky
    marker (e.g. per-case reruns_override in expected.json).
    """
    for item in items:
        if _E2E_DIR in Path(item.fspath).parents:
            item.add_marker(pytest.mark.e2e)

            if Path(item.fspath).name == "test_e2e_preclassification_routing.py":
                item.add_marker(pytest.mark.e2e_routing)

            if not item.get_closest_marker("flaky"):
                item.add_marker(pytest.mark.flaky(reruns=1))


@pytest.fixture(scope="session")
def monkeypatch_session():
    from _pytest.monkeypatch import MonkeyPatch

    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture(scope="session")
def api_key(reset_env, monkeypatch_session, e2e_tenant_id):
    # generate_api_key reads API_KEYS_TABLE_NAME from app config - must be set
    for k in (
        "API_KEYS_TABLE_NAME",
        "AWS_REGION",
        "AWS_PROFILE",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
        "DOCUMENTAI_DOCUMENT_METADATA_TABLE_NAME",
        "DOCUMENTAI_DOCUMENT_METADATA_JOB_ID_INDEX_NAME",
        "DOCUMENTAI_DOCUMENT_METADATA_TENANT_INDEX_NAME",
        "DOCUMENTAI_INPUT_LOCATION",
        "DOCUMENTAI_OUTPUT_LOCATION",
    ):
        if v := reset_env.get(k):
            monkeypatch_session.setenv(k, v)

    from documentai_api.config.env import get_env_config

    get_env_config.cache_clear()  # ensure config picks up monkeypatch changes

    raw_key, _ = generate_api_key(
        api_key_name=f"e2e-{secrets.token_hex(4)}",
        environment="dev",
        tenant_id=e2e_tenant_id,
        created_by="e2e-suite",
    )
    key_hash = _hash_key(raw_key)

    try:
        yield raw_key
    finally:
        deactivate_api_key(key_hash)


@pytest.fixture(scope="session")
def base_url(reset_env):
    return reset_env.get("BASE_URL", "http://localhost:8000")


def _wipe_test_tenant(tenant_id: str) -> None:
    """Delete every document and S3 object owned by the given e2e tenant.

    Best-effort: logs warnings on individual failures rather than raising,
    so a partial cleanup doesn't break the test session.
    """
    if not os.environ.get("E2E_WIPE_TENANT"):
        logger.info("e2e wipe skipped - E2E_WIPE_TENANT not set")
        return

    import boto3

    from documentai_api.config.env import get_env_config
    from documentai_api.schemas.document_metadata import DocumentMetadata
    from documentai_api.services import ddb as ddb_service
    from documentai_api.utils.s3 import parse_s3_uri

    cfg = get_env_config()
    table_name = cfg.documentai_document_metadata_table_name
    tenant_index_name = cfg.documentai_document_metadata_tenant_index_name
    input_location = cfg.documentai_input_location

    if not (table_name and tenant_index_name and input_location):
        logger.warning("e2e wipe skipped - required AWS config missing")
        return

    bucket, prefix = parse_s3_uri(input_location)
    s3 = boto3.client("s3")
    deleted_docs = 0
    deleted_objects = 0

    items = ddb_service.query_by_key(
        table_name, tenant_index_name, DocumentMetadata.TENANT_ID, tenant_id
    )

    for record in items:
        object_key = record.get(DocumentMetadata.FILE_NAME) or record.get("objectKey")
        if object_key:
            # Objects are stored under the tenant prefix; FILE_NAME is the bare key.
            tenant_object_key = f"{tenant_id}/{object_key}"
            s3_key = f"{prefix}/{tenant_object_key}" if prefix else tenant_object_key
            try:
                s3.delete_object(Bucket=bucket, Key=s3_key)
                deleted_objects += 1
            except Exception as e:
                logger.warning(f"e2e wipe: failed to delete s3://{bucket}/{s3_key}: {e}")

        try:
            ddb_service.delete_item(
                table_name,
                {DocumentMetadata.FILE_NAME: record[DocumentMetadata.FILE_NAME]},
            )
            deleted_docs += 1
        except Exception as e:
            logger.warning(
                f"e2e wipe: failed to delete doc {record.get(DocumentMetadata.FILE_NAME)}: {e}"
            )

    logger.info(f"e2e wipe: deleted {deleted_docs} doc records, {deleted_objects} s3 objects")


@pytest.fixture(scope="session", autouse=True)
def _sweep_stale_e2e_documents(_sweep_stale_e2e_keys, e2e_tenant_id):
    """Wipe this worker's e2e tenant before the run starts.

    Belt-and-suspenders - `cleanup_e2e_tenant` handles the happy path; this
    handles 'previous run crashed and left documents behind.'
    """
    _wipe_test_tenant(e2e_tenant_id)
    return


@pytest.fixture(scope="session", autouse=True)
def cleanup_e2e_tenant(e2e_tenant_id):
    """Delete every document this worker created in its e2e tenant."""
    yield
    _wipe_test_tenant(e2e_tenant_id)


@pytest.fixture(scope="session")
def compare_tenant_id() -> str | None:
    """The compare-{sub} tenant /v1/admin/extraction-compare writes to for this COMPARE_JWT.

    None when COMPARE_JWT isn't set - the extraction-compare e2e tests are skipped
    in that case, so there's nothing to clean up.
    """
    token = os.environ.get("COMPARE_JWT")
    if not token:
        return None

    import jwt

    claims = jwt.decode(token, options={"verify_signature": False})
    return f"compare-{claims.get('sub', 'unknown')}"


@pytest.fixture(scope="session", autouse=True)
def cleanup_compare_tenant(compare_tenant_id):
    """Wipe the compare-{sub} tenant used by /v1/admin/extraction-compare e2e tests.

    Sweeps before the run too (belt-and-suspenders for a previous run that
    crashed mid-session) and is a no-op when COMPARE_JWT isn't set.
    """
    if not compare_tenant_id:
        yield
        return

    _wipe_test_tenant(compare_tenant_id)
    yield
    _wipe_test_tenant(compare_tenant_id)


@pytest.fixture(scope="session", autouse=True)
def _ensure_multipage_flagging_enabled(monkeypatch_session):
    """Force FLAG_MULTIPLE_DOCUMENTS_IN_MULTIPAGE to true for the e2e session.

    Restores the original value (or deletes the parameter if it didn't exist)
    after the session. Ensures the 401 multipage test is not sensitive to
    whatever the flag is set to in the target environment.
    """
    from documentai_api.config.constants import FeatureFlags
    from documentai_api.config.env import get_env_config
    from documentai_api.services import ssm as ssm_service
    from documentai_api.utils.cache import get_cache

    get_env_config.cache_clear()
    config = get_env_config()

    if not config.ssm_prefix:
        yield
        return

    param = f"{config.ssm_prefix}/feature-flags/{FeatureFlags.FLAG_MULTIPLE_DOCUMENTS_IN_MULTIPAGE}"

    try:
        original = ssm_service.get_parameter(param)
    except Exception:
        original = None

    ssm_service.put_parameter(param, "true")
    get_cache().invalidate(f"ssm:{param}")

    try:
        yield
    finally:
        if original is not None:
            ssm_service.put_parameter(param, original)
        else:
            AWSClientFactory.get_ssm_client().delete_parameter(Name=param)

        get_cache().invalidate(f"ssm:{param}")


@pytest.fixture(scope="session", autouse=True)
def _sweep_stale_e2e_keys():
    """Delete e2e api keys orphaned by prior crashed runs.

    Runs once before any tests. Looks for keys named 'e2e-*' older than 1 hour.
    """
    from datetime import UTC, datetime, timedelta

    from documentai_api.config.env import get_env_config
    from documentai_api.schemas.api_key import ApiKeyRecord
    from documentai_api.services import ddb as ddb_service

    table_name = get_env_config().api_keys_table_name
    if not table_name:
        return

    cutoff = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    swept = 0

    # API keys table is small - full scan is fine; no GSI on api_key_name
    items = ddb_service.scan(table_name)

    for record in items:
        name = record.get(ApiKeyRecord.API_KEY_NAME, "")
        created = record.get(ApiKeyRecord.CREATED_AT, "")
        if name.startswith("e2e-") and created and created < cutoff:
            ddb_service.delete_item(
                table_name,
                {ApiKeyRecord.KEY_HASH: record[ApiKeyRecord.KEY_HASH]},
            )
            swept += 1

    if swept:
        logger.info(f"e2e: swept {swept} orphaned api keys")
