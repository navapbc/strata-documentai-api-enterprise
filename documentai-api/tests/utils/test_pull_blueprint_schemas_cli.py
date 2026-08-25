"""Tests for cli/pull_blueprint_schemas.py's `check` command."""

import dataclasses
import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from documentai_api.cli.pull_blueprint_schemas import app
from documentai_api.utils.schemas import extract_fields

runner = CliRunner()

_SCHEMA = {
    "description": "A Social Security card.",
    "class": "Social-Security-Card",
    "properties": {
        "social_security_number": {"type": "string", "instruction": "The SSN."},
        "name": {"type": "string", "instruction": "The full name."},
    },
}


def _matching_entry():
    """Build the blueprint_schemas.json entry that exactly matches _SCHEMA.

    Derives fields via the real extract_fields(), not a hand-copied list, so
    the fixture can't silently drift from what the production code produces.
    """
    return {
        "document_type": _SCHEMA["class"],
        "description": _SCHEMA["description"],
        "category": "identity",
        "fields": [dataclasses.asdict(f) for f in extract_fields(_SCHEMA)],
    }


@pytest.fixture
def custom_blueprint(tmp_path):
    """Write _SCHEMA as a custom blueprint under identity/, return tmp_path."""
    category_dir = tmp_path / "document-types" / "identity"
    category_dir.mkdir(parents=True)
    (category_dir / "custom-social-security-card.json").write_text(json.dumps(_SCHEMA))
    return tmp_path


def _check(tmp_path, schemas_entries):
    """Run `check`, patching in tmp_path's infra dir and schemas file.

    schemas_entries=None means don't write the schemas file at all - simulates
    it never having been generated.
    """
    schemas_file = tmp_path / "blueprint_schemas.json"
    if schemas_entries is not None:
        schemas_file.write_text(json.dumps(schemas_entries))

    with (
        patch(
            "documentai_api.cli.pull_blueprint_schemas._INFRA_DOCUMENT_TYPES",
            tmp_path / "document-types",
        ),
        patch("documentai_api.utils.schemas.SCHEMAS_FILE", schemas_file),
    ):
        return runner.invoke(app, ["check"])


def test_check_passes_when_in_sync(custom_blueprint):
    """Passes when the committed file matches infra/document-types/ exactly."""
    result = _check(custom_blueprint, {"Social-Security-Card": _matching_entry()})

    assert result.exit_code == 0


def test_check_ignores_field_order(custom_blueprint):
    """Passes even when field order differs - BDA doesn't preserve JSON property order."""
    entry = _matching_entry()
    entry["fields"] = list(reversed(entry["fields"]))

    result = _check(custom_blueprint, {"Social-Security-Card": entry})

    assert result.exit_code == 0


def test_check_fails_when_out_of_sync(custom_blueprint):
    """Fails when a field's content genuinely differs from infra/document-types/."""
    entry = _matching_entry()
    entry["description"] = "A stale description."

    result = _check(custom_blueprint, {"Social-Security-Card": entry})

    assert result.exit_code == 1
    assert "Social-Security-Card" in result.output


def test_check_fails_when_entry_missing(custom_blueprint):
    """Fails when a custom blueprint has no corresponding entry at all."""
    result = _check(custom_blueprint, {})

    assert result.exit_code == 1
    assert "missing" in result.output.lower()


def test_check_fails_when_schemas_file_missing(custom_blueprint):
    """Fails with a clear message when blueprint_schemas.json hasn't been generated yet."""
    result = _check(custom_blueprint, None)

    assert result.exit_code == 1
    assert "pull-blueprint-schemas write" in result.output


def test_check_fails_when_custom_blueprint_missing_class(tmp_path):
    """Fails loudly rather than guessing a document type for a malformed custom blueprint.

    The real fetch path (_fetch_project_schemas) falls back to BDA's registered
    blueprintName when 'class' is absent - a value this local check has no way
    to know, so guessing anything else here would just be a different, silent
    wrong answer.
    """
    category_dir = tmp_path / "document-types" / "identity"
    category_dir.mkdir(parents=True)
    (category_dir / "custom-no-class.json").write_text(
        json.dumps({"description": "x", "properties": {}})
    )

    result = _check(tmp_path, {})

    assert result.exit_code == 1
    assert "custom-no-class.json" in result.output
    assert "class" in result.output


def _write_managed_blueprints(tmp_path, category, count):
    category_dir = tmp_path / "document-types" / category
    category_dir.mkdir(parents=True, exist_ok=True)
    entries = [
        {"name": f"managed-{i}", "arn": f"arn:aws:bedrock:us-east-1:aws:blueprint/m{i}"}
        for i in range(count)
    ]
    (category_dir / "managed_blueprints.json").write_text(json.dumps(entries))


def test_check_passes_when_managed_count_matches(custom_blueprint):
    """Passes when the number of non-custom entries in a category matches managed_blueprints.json."""
    _write_managed_blueprints(custom_blueprint, "identity", count=1)
    entries = {
        "Social-Security-Card": _matching_entry(),
        "US-passports": {
            "document_type": "US-passports",
            "description": "A US passport.",
            "category": "identity",
            "fields": [],
        },
    }

    result = _check(custom_blueprint, entries)

    assert result.exit_code == 0


def test_check_fails_on_managed_blueprint_count_mismatch(custom_blueprint):
    """Fails when managed_blueprints.json's count doesn't match the committed file's."""
    _write_managed_blueprints(custom_blueprint, "identity", count=2)

    result = _check(custom_blueprint, {"Social-Security-Card": _matching_entry()})

    assert result.exit_code == 1
    assert "identity" in result.output
    assert "managed_blueprints.json lists 2" in result.output


def test_check_fails_on_orphaned_category(custom_blueprint):
    """Fails when an entry's category no longer exists under infra/document-types/."""
    entries = {
        "Social-Security-Card": _matching_entry(),
        "Ghost-Document": {
            "document_type": "Ghost-Document",
            "description": "stale",
            "category": "ghost_category",
            "fields": [],
        },
    }

    result = _check(custom_blueprint, entries)

    assert result.exit_code == 1
    assert "ghost_category" in result.output
    assert "no longer exists" in result.output
