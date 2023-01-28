import datetime
from uuid import uuid4

from sqlmodel import SQLModel, Field, UniqueConstraint, MetaData, Column, BigInteger
from pydantic import UUID4


class BaseFiles(SQLModel):
    title: str = Field(nullable=False)
    md5: str = Field(nullable=False)
    keys: UUID4 = Field(nullable=False, default_factory=uuid4)
    content_type: str = Field(nullable=False)
    created_at = Field(default=datetime.datetime.today())
    comment: str = Field(nullable=True, default="")
    file_size: int = Field(nullable=False, sa_column=Column(BigInteger()))


class Files(BaseFiles, table=True):
    id: int = Field(primary_key=True, index=True, nullable=False, sa_column=Column(BigInteger(), primary_key=True))
    metadata = MetaData(schema="app")

    __tablename__ = "files"

    __table_args__ = (
        UniqueConstraint("md5", name="unique_md5"),
    )

