"""Tests for cli/generate_categories.py."""

from unittest.mock import patch

from typer.testing import CliRunner

from documentai_api.cli.generate_categories import app

runner = CliRunner()


def test_generate_writes_categories(tmp_path):
    """Generates a valid Python file from a directory of category folders."""
    folders = ["expenses", "identity", "assets"]
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
    assert 'EXPENSES = "expenses"' in content
    assert 'IDENTITY = "identity"' in content
    assert 'ASSETS = "assets"' in content


def test_generate_collapses_nested_leaf_folders_to_parent_category(tmp_path):
    """A nested leaf folder (e.g. income/employer_income) yields its parent category, not the leaf name."""
    leaf = tmp_path / "income" / "employer_income"
    leaf.mkdir(parents=True)
    (leaf / "managed_blueprints.json").write_text("[]")

    output = tmp_path / "out.py"

    with (
        patch("documentai_api.cli.generate_categories._INFRA_DOCUMENT_TYPES", tmp_path),
        patch("documentai_api.cli.generate_categories._OUTPUT", output),
    ):
        result = runner.invoke(app)

    assert result.exit_code == 0
    content = output.read_text()
    assert 'INCOME = "income"' in content
    assert "EMPLOYER_INCOME" not in content


def test_generate_excludes_hidden_dirs(tmp_path):
    """Hidden directories and folders without managed_blueprints.json are not included."""
    d = tmp_path / "expenses"
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
    for name in ["supporting_records", "identity", "expenses"]:
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
