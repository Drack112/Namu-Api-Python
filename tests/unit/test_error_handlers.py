from app.core.exceptions.handlers import _error_body, _translate_error


def test_translate_missing_field():
    result = _translate_error({"type": "missing", "loc": ["body", "name"], "ctx": {}})
    assert result["field"] == "name"
    assert "obrigatório" in result["message"]


def test_translate_string_too_short():
    result = _translate_error(
        {
            "type": "string_too_short",
            "loc": ["body", "name"],
            "ctx": {"min_length": 1},
        }
    )
    assert "mínimo 1" in result["message"]


def test_translate_greater_than_equal():
    result = _translate_error(
        {"type": "greater_than_equal", "loc": ["body", "age"], "ctx": {"ge": 1}}
    )
    assert result["field"] == "age"
    assert "maior ou igual a 1" in result["message"]


def test_translate_less_than_equal():
    result = _translate_error(
        {"type": "less_than_equal", "loc": ["body", "age"], "ctx": {"le": 120}}
    )
    assert "menor ou igual a 120" in result["message"]


def test_translate_literal_error():
    result = _translate_error(
        {
            "type": "literal_error",
            "loc": ["body", "experience_level"],
            "ctx": {"expected": "'iniciante', 'intermediário', 'avançado'"},
        }
    )
    assert result["field"] == "experience_level"
    assert "valores:" in result["message"]


def test_translate_unknown_type_uses_fallback():
    result = _translate_error(
        {"type": "some_new_type", "loc": ["body", "field"], "msg": "custom error", "ctx": {}}
    )
    assert "custom error" in result["message"]


def test_translate_drops_body_prefix_from_location():
    result = _translate_error({"type": "missing", "loc": ["body", "goals"], "ctx": {}})
    assert result["field"] == "goals"
    assert "body" not in result["field"]


def test_translate_nested_field_path():
    result = _translate_error(
        {"type": "string_type", "loc": ["body", "address", "street"], "ctx": {}}
    )
    assert result["field"] == "address.street"


def test_translate_top_level_field_returns_none():
    result = _translate_error({"type": "json_invalid", "loc": ["body"], "ctx": {}})
    assert result["field"] is None


def test_error_body_without_details():
    body = _error_body(404, "Não encontrado", "/users/1")
    assert body == {"status_code": 404, "path": "/users/1", "message": "Não encontrado"}
    assert "details" not in body


def test_error_body_with_details():
    details = [{"field": "name", "message": "obrigatório"}]
    body = _error_body(422, "Validação", "/users/", details)
    assert body["details"] == details


def test_error_body_with_empty_list_details():
    body = _error_body(422, "msg", "/path", [])
    assert body["details"] == []
