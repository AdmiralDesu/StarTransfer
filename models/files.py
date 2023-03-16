"""
Model for file tables
"""
import datetime
from uuid import uuid4

from sqlmodel import SQLModel, Field, UniqueConstraint, MetaData, Column, BigInteger
from pydantic import UUID4


class Files(SQLModel, table=True):
    """
    Class for app.files table
    """
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

    metadata = MetaData(schema="app")

    __tablename__ = "files"

    __table_args__ = (
        UniqueConstraint("keys", name="files_unique_keys"),
    )


class FilesMD5(SQLModel, table=True):
    """
    Class for app.files_md5 table
    """
    id: str = Field(
        primary_key=True,
        index=True,
        nullable=False
    )
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

    metadata = MetaData(schema="app")

    __tablename__ = "files_md5"


class FilesTree(SQLModel, table=True):
    """
    Class for app.files_tree table
    """
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
    parent_id: int = Field(
        nullable=True,
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

    metadata = MetaData(schema="app")

    __tablename__ = "files_tree"

    __table_args__ = (
        UniqueConstraint("keys", name="files_tree_unique_keys"),
    )
