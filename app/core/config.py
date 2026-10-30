from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cau hinh ung dung, lay tu bien moi truong / file .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/testapi_owasp"

    # Allowlist target duoc phep scan, theo "Quy tac an toan" trong CLAUDE.md.
    allowed_target_hosts: str = "localhost,127.0.0.1,dc,vampi,crapi"

    zap_host: str = "localhost"
    zap_port: int = 8080
    zap_api_key: str = "changeme"

    # LLM API tuong thich OpenAI Chat Completions (OpenAI, Azure OpenAI, hoac tuong duong).
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"

    @property
    def allowed_target_hosts_list(self) -> list[str]:
        return [h.strip().lower() for h in self.allowed_target_hosts.split(",") if h.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
