from fastapi import FastAPI

from app.api.routes.projects import router as projects_router
from app.api.routes.scans import router as scans_router

app = FastAPI(title="OWASP API Security Testing Tool")

app.include_router(projects_router)
app.include_router(scans_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
