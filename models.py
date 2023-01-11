import datetime
from uuid import uuid4

from sqlmodel import SQLModel, Field, UniqueConstraint, MetaData
from pydantic import UUID4


class BaseFiles(SQLModel):
    title: str = Field(nullable=False)
    md5: str = Field(nullable=False)
    keys: UUID4 = Field(nullable=False, default_factory=uuid4)
    content_type: str = Field(nullable=False)
    created_at = Field(default=datetime.datetime.today())


class Files(BaseFiles, table=True):
    id: int = Field(primary_key=True, index=True, nullable=False)
    metadata = MetaData(schema="app")

    __tablename__ = "files"

    __table_args__ = (
        UniqueConstraint("md5", name="unique_md5"),
    )

