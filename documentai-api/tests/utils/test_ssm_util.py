"""Tests for utils/ssm.py feature-flag helpers."""

from types import SimpleNamespace

from documentai_api.utils.ssm import is_document_crop_enabled, is_textract_identity_enabled


def test_is_document_crop_enabled_defaults_off_when_unconfigured(mocker):
    """No param path configured -> cropping defaults off (opt-in)."""
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(document_crop_param=None),
    )
    assert is_document_crop_enabled() is False


def test_is_document_crop_enabled_reads_true(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(document_crop_param="/docai/dev/feature-flags/document-crop"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="true")
    assert is_document_crop_enabled() is True


def test_is_document_crop_enabled_reads_false(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(document_crop_param="/docai/dev/feature-flags/document-crop"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="false")
    assert is_document_crop_enabled() is False


def test_is_textract_identity_enabled_defaults_off_when_unconfigured(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(textract_identity_param=None),
    )
    assert is_textract_identity_enabled() is False


def test_is_textract_identity_enabled_reads_true(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(
            textract_identity_param="/docai/dev/feature-flags/textract-identity-enabled"
        ),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="true")
    assert is_textract_identity_enabled() is True


def test_is_textract_identity_enabled_reads_false(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(
            textract_identity_param="/docai/dev/feature-flags/textract-identity-enabled"
        ),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="false")
    assert is_textract_identity_enabled() is False
