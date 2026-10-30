"""Import spec OpenAPI/Swagger (JSON hoac YAML) va chuan hoa ve NormalizedSpec."""

import json

import yaml

from app.importers.base import NormalizedEndpoint, NormalizedParameter, NormalizedSpec

_VALID_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}


def parse_raw(raw_text: str) -> dict:
    """Parse noi dung spec dang text thanh dict. Thu JSON truoc, roi YAML."""
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        return yaml.safe_load(raw_text)


def normalize(spec: dict) -> NormalizedSpec:
    version = spec.get("openapi") or spec.get("swagger") or ""
    endpoints: list[NormalizedEndpoint] = []

    for path, path_item in (spec.get("paths") or {}).items():
        if not isinstance(path_item, dict):
            continue

        shared_params = path_item.get("parameters") or []

        for method, operation in path_item.items():
            if method.lower() not in _VALID_METHODS or not isinstance(operation, dict):
                continue

            raw_params = shared_params + (operation.get("parameters") or [])
            parameters = [
                NormalizedParameter(
                    name=p.get("name", ""),
                    location=p.get("in", "query"),
                    required=bool(p.get("required", False)),
                    schema_json=p.get("schema") or {},
                )
                for p in raw_params
                if isinstance(p, dict)
            ]

            request_body = operation.get("requestBody")
            if isinstance(request_body, dict):
                body_schema = (
                    request_body.get("content", {}).get("application/json", {}).get("schema", {})
                )
                parameters.append(
                    NormalizedParameter(
                        name="body",
                        location="body",
                        required=bool(request_body.get("required", False)),
                        schema_json=body_schema,
                    )
                )

            endpoints.append(
                NormalizedEndpoint(
                    method=method.upper(),
                    path=path,
                    operation_id=operation.get("operationId", ""),
                    summary=operation.get("summary", ""),
                    tags=operation.get("tags") or [],
                    parameters=parameters,
                )
            )

    return NormalizedSpec(version=str(version), endpoints=endpoints)
