from app.importers import openapi as openapi_importer

JSON_SPEC = """
{
  "openapi": "3.0.0",
  "paths": {
    "/users/{id}": {
      "get": {
        "operationId": "getUser",
        "summary": "Get a user",
        "tags": ["users"],
        "parameters": [
          {"name": "id", "in": "path", "required": true, "schema": {"type": "integer"}}
        ]
      },
      "post": {
        "operationId": "updateUser",
        "requestBody": {
          "required": true,
          "content": {"application/json": {"schema": {"type": "object"}}}
        }
      }
    }
  }
}
"""

YAML_SPEC = """
openapi: "3.0.0"
paths:
  /ping:
    get:
      operationId: ping
      summary: health check
"""


def test_parse_and_normalize_json_spec() -> None:
    raw = openapi_importer.parse_raw(JSON_SPEC)
    normalized = openapi_importer.normalize(raw)

    assert normalized.version == "3.0.0"
    assert len(normalized.endpoints) == 2

    get_user = next(e for e in normalized.endpoints if e.operation_id == "getUser")
    assert get_user.method == "GET"
    assert get_user.path == "/users/{id}"
    assert len(get_user.parameters) == 1
    assert get_user.parameters[0] == openapi_importer.NormalizedParameter(
        name="id", location="path", required=True, schema_json={"type": "integer"}
    )

    update_user = next(e for e in normalized.endpoints if e.operation_id == "updateUser")
    assert update_user.method == "POST"
    assert any(p.location == "body" for p in update_user.parameters)


def test_parse_and_normalize_yaml_spec() -> None:
    raw = openapi_importer.parse_raw(YAML_SPEC)
    normalized = openapi_importer.normalize(raw)

    assert len(normalized.endpoints) == 1
    assert normalized.endpoints[0].method == "GET"
    assert normalized.endpoints[0].path == "/ping"


def test_normalize_spec_with_no_paths_returns_empty() -> None:
    normalized = openapi_importer.normalize({"openapi": "3.0.0"})
    assert normalized.endpoints == []
