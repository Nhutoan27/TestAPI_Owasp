from pydantic import BaseModel


class AuthProfileCreate(BaseModel):
    name: str
    role: str  # user_a | user_b | admin
    login_url: str | None = None
    credentials: dict = {}
    token_path: str = "access_token"
    static_token: str | None = None


class AuthProfileOut(BaseModel):
    """Khong tra ve credentials/static_token: tranh echo lai secret qua API."""

    id: int
    project_id: int
    name: str
    role: str

    model_config = {"from_attributes": True}
