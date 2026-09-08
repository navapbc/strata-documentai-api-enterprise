"""Tests for cli/generate_categories.py."""

from unittest.mock import patch

from typer.testing import CliRunner

from documentai_api.cli.generate_categories import app

runner = CliRunner()


def test_generate_writes_categories(tmp_path):
    """Generates a valid Python file from a directory of category folders."""
    folders = ["employer_income", "identity", "shelter"]
    for name in folders:
        d = tmp_path / name
        d.mkdir()
        (d / "managed_blueprints.json").write_text("[]")

    output = tmp_path / "constants_preclassification_category_generated.py"

    with (
        patch("documentai_api.cli.generate_categories._INFRA_DOCUMENT_TYPES", tmp_path),
        patch("documentai_api.cli.generate_categories._OUTPUT", output),
    ):
        result = runner.invoke(app)

    assert result.exit_code == 0
    content = output.read_text()
    assert "class PreclassificationCategory(StrEnum):" in content
    assert 'EMPLOYER_INCOME = "employer_income"' in content
    assert 'IDENTITY = "identity"' in content
    assert 'SHELTER = "shelter"' in content


def test_generate_excludes_hidden_dirs(tmp_path):
    """Hidden directories and folders without managed_blueprints.json are not included."""
    d = tmp_path / "employer_income"
    d.mkdir()
    (d / "managed_blueprints.json").write_text("[]")
    (tmp_path / ".hidden").mkdir()
    incomplete = tmp_path / "incomplete_category"
    incomplete.mkdir()  # no managed_blueprints.json

    output = tmp_path / "out.py"

    with (
        patch("documentai_api.cli.generate_categories._INFRA_DOCUMENT_TYPES", tmp_path),
        patch("documentai_api.cli.generate_categories._OUTPUT", output),
    ):
        runner.invoke(app)

    content = output.read_text()
    assert ".hidden" not in content
    assert "HIDDEN" not in content
    assert "incomplete_category" not in content


def test_generate_exits_when_no_folders(tmp_path):
    """Exits with code 1 when no folders are found."""
    output = tmp_path / "out.py"

    with (
        patch("documentai_api.cli.generate_categories._INFRA_DOCUMENT_TYPES", tmp_path),
        patch("documentai_api.cli.generate_categories._OUTPUT", output),
    ):
        result = runner.invoke(app)

    assert result.exit_code == 1


def test_generate_output_is_sorted(tmp_path):
    """Categories are written in alphabetical order."""
    for name in ["shelter", "identity", "employer_income"]:
        d = tmp_path / name
        d.mkdir()
        (d / "managed_blueprints.json").write_text("[]")

    output = tmp_path / "out.py"

    with (
        patch("documentai_api.cli.generate_categories._INFRA_DOCUMENT_TYPES", tmp_path),
        patch("documentai_api.cli.generate_categories._OUTPUT", output),
    ):
        runner.invoke(app)

    lines = [
        line for line in output.read_text().splitlines() if " = " in line and "StrEnum" not in line
    ]
    values = [line.split('"')[1] for line in lines]
    assert values == sorted(values)
