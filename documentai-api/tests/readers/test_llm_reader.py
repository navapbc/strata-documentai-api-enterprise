from documentai_api.readers.llm import read_llm_output

LLM_OUTPUT = {
    "source": "llm",
    "fields": {
        "employee_name": {
            "confidence": 0.99,
            "value": "John Smith",
            "text_citation": "John Smith",
            "fieldType": "string",
            "geometry": [{"boundingBox": {"left": 0.1, "top": 0.1, "width": 0.3, "height": 0.05}}],
        },
        "employer_name": {
            "confidence": 0.95,
            "value": "Acme Corp",
            "text_citation": "Acme Corp",
            "fieldType": "string",
        },
        "pay_date": {"confidence": 0.87, "value": "", "text_citation": None, "fieldType": "date"},
    },
}


def test_read_llm_output():
    result = read_llm_output(LLM_OUTPUT)

    assert len(result.field_confidence_map_list) == 3
    assert {"employee_name": 0.99} in result.field_confidence_map_list
    assert "pay_date" in result.empty_fields
    assert result.field_values["employee_name"] == "John Smith"
    assert result.field_values["pay_date"] == ""


def test_read_llm_output_geometry_excluded_by_default():
    result = read_llm_output(LLM_OUTPUT)
    assert result.field_geometry == {}


def test_read_llm_output_geometry_included():
    result = read_llm_output(LLM_OUTPUT, include_geometry=True)
    assert "employee_name" in result.field_geometry
    assert result.field_geometry["employee_name"]["type"] == "string"
    assert "employer_name" not in result.field_geometry
    assert "pay_date" not in result.field_geometry


def test_read_llm_output_empty():
    result = read_llm_output({"fields": {}})
    assert result.field_confidence_map_list == []
    assert result.empty_fields == []
    assert result.field_values == {}
    assert result.field_geometry == {}


def test_read_llm_output_missing_fields_key():
    result = read_llm_output({})
    assert result == read_llm_output({"fields": {}})
