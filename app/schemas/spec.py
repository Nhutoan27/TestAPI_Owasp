from pydantic import BaseModel


class ApiSpecImport(BaseModel):
    raw_content: str  # noi dung spec dang text (JSON hoac YAML)


class ParameterOut(BaseModel):
    name: str
    location: str
    required: bool


class EndpointOut(BaseModel):
    method: str
    path: str
    operation_id: str
    summary: str
    parameters: list[ParameterOut]


class ApiSpecOut(BaseModel):
    id: int
    project_id: int
    source_type: str
    version: str
    endpoints: list[EndpointOut]

    model_config = {"from_attributes": True}
