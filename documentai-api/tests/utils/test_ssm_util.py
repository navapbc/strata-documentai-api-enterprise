"""Tests for utils/ssm.py feature-flag helpers."""

from types import SimpleNamespace

from documentai_api.utils.ssm import (
    is_document_crop_enabled,
    is_preclassification_blueprint_matching_enabled,
    is_preclassification_routing_enabled,
    is_skip_bda_if_unclassified,
    is_textract_identity_enabled,
)


def test_is_document_crop_enabled_defaults_off_when_unconfigured(mocker):
    """No ssm_prefix configured -> cropping defaults off."""
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix=None),
    )
    assert is_document_crop_enabled() is False


def test_is_document_crop_enabled_reads_true(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="true")
    assert is_document_crop_enabled() is True


def test_is_document_crop_enabled_reads_false(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="false")
    assert is_document_crop_enabled() is False


def test_is_textract_identity_enabled_defaults_off_when_unconfigured(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix=None),
    )
    assert is_textract_identity_enabled() is False


def test_is_textract_identity_enabled_reads_true(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="true")
    assert is_textract_identity_enabled() is True


def test_is_textract_identity_enabled_reads_false(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="false")
    assert is_textract_identity_enabled() is False


def test_is_preclassification_routing_enabled_defaults_off_when_unconfigured(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix=None),
    )
    assert is_preclassification_routing_enabled() is False


def test_is_preclassification_routing_enabled_reads_true(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="true")
    assert is_preclassification_routing_enabled() is True


def test_is_preclassification_routing_enabled_reads_false(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="false")
    assert is_preclassification_routing_enabled() is False


def test_is_skip_bda_if_unclassified_defaults_off_when_unconfigured(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix=None),
    )
    assert is_skip_bda_if_unclassified() is False


def test_is_skip_bda_if_unclassified_reads_true(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="true")
    assert is_skip_bda_if_unclassified() is True


def test_is_skip_bda_if_unclassified_reads_false(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="false")
    assert is_skip_bda_if_unclassified() is False


def test_is_preclassification_blueprint_matching_enabled_defaults_on_when_unconfigured(mocker):
    """No ssm_prefix configured -> blueprint matching defaults on."""
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix=None),
    )
    assert is_preclassification_blueprint_matching_enabled() is True


def test_is_preclassification_blueprint_matching_enabled_reads_true(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="true")
    assert is_preclassification_blueprint_matching_enabled() is True


def test_is_preclassification_blueprint_matching_enabled_reads_false(mocker):
    mocker.patch(
        "documentai_api.config.env.get_aws_config",
        return_value=SimpleNamespace(ssm_prefix="/docai/dev"),
    )
    mocker.patch("documentai_api.utils.ssm.get_parameter_value", return_value="false")
    assert is_preclassification_blueprint_matching_enabled() is False
