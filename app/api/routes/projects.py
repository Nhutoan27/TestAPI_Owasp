from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import mask_target_allowlist_check
from app.db import crud
from app.db.session import get_db
from app.importers import openapi as openapi_importer
from app.schemas.auth_profile import AuthProfileCreate, AuthProfileOut
from app.schemas.project import ProjectCreate, ProjectOut
from app.schemas.spec import ApiSpecImport, ApiSpecOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> ProjectOut:
    host = urlparse(payload.target_base_url).hostname or ""
    if not mask_target_allowlist_check(host, settings.allowed_target_hosts_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Target '{host}' khong nam trong allowlist cho phep scan.",
        )
    project = await crud.create_project(db, payload.name, payload.target_base_url)
    return ProjectOut.model_validate(project)


@router.post("/{project_id}/specs/openapi", response_model=ApiSpecOut, status_code=status.HTTP_201_CREATED)
async def import_openapi_spec(
    project_id: int,
    payload: ApiSpecImport,
    db: AsyncSession = Depends(get_db),
) -> ApiSpecOut:
    project = await crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    raw_dict = openapi_importer.parse_raw(payload.raw_content)
    normalized = openapi_importer.normalize(raw_dict)
    api_spec = await crud.save_normalized_spec(db, project_id, "openapi", raw_dict, normalized)
    return ApiSpecOut.model_validate(api_spec)


@router.post(
    "/{project_id}/auth-profiles", response_model=AuthProfileOut, status_code=status.HTTP_201_CREATED
)
async def create_auth_profile(
    project_id: int,
    payload: AuthProfileCreate,
    db: AsyncSession = Depends(get_db),
) -> AuthProfileOut:
    project = await crud.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not payload.login_url and not payload.static_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can cung cap login_url hoac static_token.",
        )

    profile = await crud.create_auth_profile(
        db,
        project_id=project_id,
        name=payload.name,
        role=payload.role,
        login_url=payload.login_url,
        credentials=payload.credentials,
        token_path=payload.token_path,
        static_token=payload.static_token,
    )
    return AuthProfileOut.model_validate(profile)
