import datetime
from uuid import uuid4

from sqlmodel import SQLModel, Field, UniqueConstraint, MetaData, Column, BigInteger
from pydantic import UUID4


class FilesBase(SQLModel):
    filename: str = Field(nullable=False)
    folder_id: int = Field(
        nullable=False,
        sa_column=Column(
            BigInteger(),
            nullable=False
        )
    )
    keys: UUID4 = Field(nullable=False, default_factory=uuid4)
    inserted = Field(default=datetime.datetime.today())
    inserted_by: str = Field(nullable=False)
    md5: str = Field(nullable=False)


class Files(FilesBase, table=True):
    id: int = Field(
        primary_key=True,
        index=True,
        nullable=False,
        sa_column=Column(
            BigInteger(),
            primary_key=True,
            index=True,
            nullable=False
        )
    )
    metadata = MetaData(schema="app")

    __tablename__ = "files"

    __table_args__ = (
        UniqueConstraint("keys", name="unique_keys"),
    )


class FilesMD5Base(SQLModel):
    mime_type: str = Field(nullable=False)
    file_size: int = Field(
        nullable=False,
        sa_column=Column(
            BigInteger(),
            nullable=False
        )
    )
    inserted = Field(default=datetime.datetime.today())
    inserted_by: str = Field(nullable=False)


class FilesMD5(FilesMD5Base, table=True):
    id: str = Field(
        primary_key=True,
        index=True,
        nullable=False
    )
    metadata = MetaData(schema="app")

    __tablename__ = "files_md5"


class FilesTreeBase(SQLModel):
    parent_id: int = Field(
        nullable=False,
        sa_column=Column(
            BigInteger(),
            nullable=False
        )
    )
    name: str = Field(nullable=False)
    keys: UUID4 = Field(nullable=False, default_factory=uuid4)
    inserted = Field(default=datetime.datetime.today())
    inserted_by: str = Field(nullable=False)
    order_n: int = Field(nullable=True)


class FilesTree(FilesTreeBase, table=True):
    id: int = Field(
        primary_key=True,
        index=True,
        nullable=False,
        sa_column=Column(
            BigInteger(),
            primary_key=True,
            index=True,
            nullable=False
        )
    )
    metadata = MetaData(schema="app")

    __tablename__ = "files_tree"

    __table_args__ = (
        UniqueConstraint("keys", name="folder_unique_keys"),
    )

