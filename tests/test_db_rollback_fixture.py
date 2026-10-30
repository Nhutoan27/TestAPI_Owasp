"""Kiem tra ha tang test: db_session phai rollback het du code test co commit().

2 test duoi day phu thuoc thu tu chay (pytest giu nguyen thu tu khai bao trong
file) de xac nhan du lieu tao o test 1 khong con sau khi fixture cleanup.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db import crud
from app.db.models import Project

_PROJECT_NAME = "rollback-fixture-check-project"


@pytest.mark.asyncio
async def test_1_create_project_commits_inside_fixture_transaction(db_session) -> None:
    project = await crud.create_project(db_session, _PROJECT_NAME, "http://localhost:1234")
    assert project.id is not None


@pytest.mark.asyncio
async def test_2_previous_test_data_was_rolled_back_from_real_db() -> None:
    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(select(Project).where(Project.name == _PROJECT_NAME))
            assert result.first() is None
    finally:
        await engine.dispose()
