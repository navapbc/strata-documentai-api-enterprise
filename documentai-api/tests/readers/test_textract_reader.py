from documentai_api.readers.textract import extract_field_values_from_textract_results


def test_extract_field_values_from_textract_results():
    stored = {
        "source": "textract",
        "fields": {
            "NAME_DETAILS.FIRST_NAME": {
                "confidence": 0.99,
                "value": "John",
                "geometry": [
                    {"boundingBox": {"Width": 0.1, "Height": 0.05, "Left": 0.4, "Top": 0.5}}
                ],
            },
            "NAME_DETAILS.LAST_NAME": {"confidence": 0.98, "value": "Doe"},
            "ID_NUMBER": {"confidence": 0.97, "value": ""},
        },
    }
    metadata, field_values, field_geometry = extract_field_values_from_textract_results(stored)

    assert len(metadata["field_confidence_map_list"]) == 3
    assert "ID_NUMBER" in metadata["empty_fields"]
    assert field_values["NAME_DETAILS.FIRST_NAME"] == "John"
    assert field_values["ID_NUMBER"] == ""

    assert "NAME_DETAILS.FIRST_NAME" in field_geometry
    assert field_geometry["NAME_DETAILS.FIRST_NAME"]["geometry"] == [
        {"boundingBox": {"Width": 0.1, "Height": 0.05, "Left": 0.4, "Top": 0.5}}
    ]
    assert "NAME_DETAILS.LAST_NAME" not in field_geometry
    assert "ID_NUMBER" not in field_geometry


def test_extract_field_values_from_textract_results_empty():
    metadata, field_values, field_geometry = extract_field_values_from_textract_results(
        {"fields": {}}
    )
    assert metadata["field_confidence_map_list"] == []
    assert metadata["empty_fields"] == []
    assert field_values == {}
    assert field_geometry == {}
