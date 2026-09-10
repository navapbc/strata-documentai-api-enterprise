from documentai_api.readers.textract import read_textract_output

TEXTRACT_OUTPUT = {
    "source": "textract",
    "fields": {
        "NAME_DETAILS.FIRST_NAME": {
            "confidence": 0.99,
            "value": "John",
            "geometry": [{"boundingBox": {"Width": 0.1, "Height": 0.05, "Left": 0.4, "Top": 0.5}}],
        },
        "NAME_DETAILS.LAST_NAME": {"confidence": 0.98, "value": "Doe"},
        "ID_NUMBER": {"confidence": 0.97, "value": ""},
    },
}


def test_read_textract_output():
    result = read_textract_output(TEXTRACT_OUTPUT)

    assert len(result.field_confidence_map_list) == 3
    assert "ID_NUMBER" in result.empty_fields
    assert result.field_values["NAME_DETAILS.FIRST_NAME"] == "John"
    assert result.field_values["ID_NUMBER"] == ""


def test_read_textract_output_geometry():
    assert read_textract_output(TEXTRACT_OUTPUT).field_geometry == {}

    result = read_textract_output(TEXTRACT_OUTPUT, include_geometry=True)
    assert "NAME_DETAILS.FIRST_NAME" in result.field_geometry
    assert "NAME_DETAILS.LAST_NAME" not in result.field_geometry
    assert "ID_NUMBER" not in result.field_geometry


def test_read_textract_output_empty():
    result = read_textract_output({"fields": {}})
    assert result.field_confidence_map_list == []
    assert result.empty_fields == []
    assert result.field_values == {}
    assert result.field_geometry == {}
