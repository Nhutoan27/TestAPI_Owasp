"""Lop luu tru (service) cho router goi vao, khong chua logic nghiep vu phuc tap."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import ApiSpec, AuthProfile, Endpoint, Parameter, Project
from app.importers.base import NormalizedSpec


async def create_project(db: AsyncSession, name: str, target_base_url: str) -> Project:
    project = Project(name=name, target_base_url=target_base_url)
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


async def get_project(db: AsyncSession, project_id: int) -> Project | None:
    return await db.get(Project, project_id)


async def save_normalized_spec(
    db: AsyncSession,
    project_id: int,
    source_type: str,
    raw_content: dict,
    normalized: NormalizedSpec,
) -> ApiSpec:
    api_spec = ApiSpec(
        project_id=project_id,
        source_type=source_type,
        version=normalized.version,
        raw_content=raw_content,
    )
    for ep in normalized.endpoints:
        endpoint = Endpoint(
            method=ep.method,
            path=ep.path,
            operation_id=ep.operation_id,
            summary=ep.summary,
            tags=ep.tags,
        )
        for p in ep.parameters:
            endpoint.parameters.append(
                Parameter(
                    name=p.name,
                    location=p.location,
                    required=p.required,
                    schema_json=p.schema_json,
                )
            )
        api_spec.endpoints.append(endpoint)

    db.add(api_spec)
    await db.commit()

    result = await db.execute(
        select(ApiSpec)
        .where(ApiSpec.id == api_spec.id)
        .options(selectinload(ApiSpec.endpoints).selectinload(Endpoint.parameters))
    )
    return result.scalar_one()


async def create_auth_profile(
    db: AsyncSession,
    project_id: int,
    name: str,
    role: str,
    login_url: str | None,
    credentials: dict,
    token_path: str,
    static_token: str | None,
) -> AuthProfile:
    profile = AuthProfile(
        project_id=project_id,
        name=name,
        role=role,
        login_url=login_url,
        credentials=credentials,
        token_path=token_path,
        static_token=static_token,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile
