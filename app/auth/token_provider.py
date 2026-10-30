"""Lay / lam moi token cho mot auth profile (user A, user B, admin)."""

import httpx

from app.db.models import AuthProfile


def _extract(data: dict, dotted_path: str) -> str:
    value: object = data
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(f"Khong tim thay '{dotted_path}' trong response login")
        value = value[part]
    return str(value)


async def get_token(profile: AuthProfile, client: httpx.AsyncClient) -> str:
    """Tra ve token hien hanh cho profile. Neu co login_url se dang nhap lai (lam moi token)."""
    if profile.login_url:
        response = await client.post(profile.login_url, json=profile.credentials)
        response.raise_for_status()
        return _extract(response.json(), profile.token_path)

    if profile.static_token:
        return profile.static_token

    raise ValueError(f"AuthProfile '{profile.name}' thieu ca login_url va static_token")
