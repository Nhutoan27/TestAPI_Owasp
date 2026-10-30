"""Mo hinh Endpoint chung ma moi importer (openapi.py, postman.py) phai chuan hoa ve."""

from dataclasses import dataclass, field


@dataclass
class NormalizedParameter:
    name: str
    location: str  # path | query | header | cookie | body
    required: bool
    schema_json: dict


@dataclass
class NormalizedEndpoint:
    method: str
    path: str
    operation_id: str = ""
    summary: str = ""
    tags: list[str] = field(default_factory=list)
    parameters: list[NormalizedParameter] = field(default_factory=list)


@dataclass
class NormalizedSpec:
    version: str
    endpoints: list[NormalizedEndpoint]
