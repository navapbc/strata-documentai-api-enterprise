"""Tests for mappings/textract/."""

import pytest

from documentai_api.mappings.textract import get_bda_field_map, get_document_class


def test_get_document_class_passport_falls_through():
    assert get_document_class("PASSPORT") is None


def test_get_document_class_driver_license():
    assert get_document_class("DRIVER LICENSE FRONT") == "US-drivers-licenses"


@pytest.mark.parametrize("input_val", ["UNKNOWN_TYPE", None, ""])
def test_get_document_class_returns_none(input_val):
    assert get_document_class(input_val) is None


def test_get_bda_field_map_us_drivers_licenses():
    field_map = get_bda_field_map("US-drivers-licenses")
    assert field_map["FIRST_NAME"] == "NAME_DETAILS.FIRST_NAME"
    assert field_map["DATE_OF_BIRTH"] == "DATE_OF_BIRTH"
    assert field_map["DOCUMENT_NUMBER"] == "ID_NUMBER"
    assert "SEX" not in field_map  # not returned by AnalyzeID


def test_get_bda_field_map_us_passports():
    field_map = get_bda_field_map("US-passports")
    assert field_map["FIRST_NAME"] == "name.given_name"
    assert field_map["LAST_NAME"] == "name.last_name"
    assert field_map["DOCUMENT_NUMBER"] == "document_number"
    assert field_map["MRZ_CODE"] == "mrz_code"


def test_get_bda_field_map_unknown_class_returns_empty():
    assert get_bda_field_map("unknown-class") == {}
