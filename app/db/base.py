from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    # Luu timestamp co timezone (TIMESTAMPTZ): code dung datetime.now(timezone.utc)
    # (xem app/db/models.py::_utcnow), asyncpg se tu choi insert vao cot naive.
    type_annotation_map = {datetime: DateTime(timezone=True)}
