import pytest
from unittest.mock import patch, MagicMock
from app.services.semantic import _parse_json_response


def test_parse_json_response_plain():
    content = '{"tipo_detectado": "contestacao", "tipo_confirmado": true}'
    result = _parse_json_response(content)
    assert result["tipo_detectado"] == "contestacao"
    assert result["tipo_confirmado"] is True


def test_parse_json_response_with_markdown():
    content = '```json\n{"tipo_detectado": "inicial", "tipo_confirmado": false}\n```'
    result = _parse_json_response(content)
    assert result["tipo_detectado"] == "inicial"
    assert result["tipo_confirmado"] is False


def test_parse_json_response_with_code_block_no_lang():
    content = '```\n{"tipo_detectado": "recurso", "tipo_confirmado": true}\n```'
    result = _parse_json_response(content)
    assert result["tipo_detectado"] == "recurso"


def test_parse_json_response_invalid():
    content = "not valid json at all"
    with pytest.raises(Exception):
        _parse_json_response(content)
