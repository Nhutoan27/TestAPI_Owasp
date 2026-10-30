"""Goi LLM qua OpenAI-compatible Chat Completions API, bat buoc output theo JSON schema."""

import json

import httpx

from app.ai.schema import SEVERITY_JSON_SCHEMA
from app.core.config import Settings

SYSTEM_PROMPT = (
    "Ban la chuyen gia bao mat API. Ban CHI duoc dieu chinh severity co so da cho "
    "(Low/Medium/High/Critical), khong duoc tu dat severity ngoai thang do. "
    "Phai kem ly do ro rang, ngan gon cho de xuat cua ban."
)


def _build_user_prompt(finding_context: dict) -> str:
    return (
        f"OWASP ID: {finding_context['owasp_id']}\n"
        f"Tieu de: {finding_context['title']}\n"
        f"Mo ta: {finding_context['description']}\n"
        f"Severity co so (da duoc rule xac dinh truoc): {finding_context['base_severity']}\n"
        f"Bang chung (da mask thong tin nhay cam): "
        f"{json.dumps(finding_context['evidence'], ensure_ascii=False)}\n\n"
        "Dua tren bang chung, de xuat severity cuoi cung (co the giu nguyen severity co so "
        "neu hop ly) va giai thich ngan gon ly do."
    )


async def call_llm_for_severity(
    finding_context: dict, client: httpx.AsyncClient, settings: Settings
) -> dict:
    response = await client.post(
        f"{settings.openai_base_url}/chat/completions",
        headers={"Authorization": f"Bearer {settings.openai_api_key}"},
        json={
            "model": settings.openai_model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(finding_context)},
            ],
            "response_format": {"type": "json_schema", "json_schema": SEVERITY_JSON_SCHEMA},
        },
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return json.loads(content)
