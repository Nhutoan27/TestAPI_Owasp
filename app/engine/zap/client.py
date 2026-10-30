from zapv2 import ZAPv2

from app.core.config import Settings, get_settings


def make_zap_client(settings: Settings | None = None) -> ZAPv2:
    """Tao client zapv2, tro ve ZAP daemon chay trong Docker (xem docker-compose.yml)."""
    settings = settings or get_settings()
    proxy = f"http://{settings.zap_host}:{settings.zap_port}"
    return ZAPv2(apikey=settings.zap_api_key, proxies={"http": proxy, "https": proxy})
