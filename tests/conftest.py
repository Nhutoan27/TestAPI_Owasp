"""Fixture db_session: chay test tren Postgres thuc (bang migration da ap dung),
nhung moi test nam trong 1 transaction duoc rollback khi ket thuc - du code duoc
test co goi db.commit() ben trong (crud/evaluator deu commit ngay khi ghi).

Dung lai "join a Session into an external transaction" cua SQLAlchemy: session
chay tren 1 connection da mo transaction + savepoint; moi khi code goi commit(),
savepoint duoc dong thi mo lai savepoint moi ngay sau do.
"""

import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import get_settings

# Tao engine rieng cho tung test (khong dung chung engine global cua app.db.session):
# asyncpg pool gan voi 1 event loop cu the, trong khi pytest-asyncio tao event loop
# moi cho moi test function, nen dung chung engine giua cac test se vo hieu tren Windows.


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine(get_settings().database_url)
    connection = await engine.connect()
    await connection.begin()
    await connection.begin_nested()

    session_factory = async_sessionmaker(bind=connection, expire_on_commit=False)
    session = session_factory()

    @event.listens_for(session.sync_session, "after_transaction_end")
    def _restart_savepoint(sync_session, transaction) -> None:
        if connection.closed:
            return
        if not connection.sync_connection.in_nested_transaction():
            connection.sync_connection.begin_nested()

    try:
        yield session
    finally:
        await session.close()
        await connection.rollback()
        await connection.close()
        await engine.dispose()
