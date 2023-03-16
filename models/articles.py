"""
Model for article table
"""
import datetime

from sqlmodel import SQLModel, Field, UniqueConstraint, MetaData, Column, BigInteger


class Article(SQLModel, table=True):
    """
    Class for app.articles table
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
    title: str = Field(nullable=False)
    folder_id: int = Field(
        nullable=False,
        sa_column=Column(
            BigInteger(),
            nullable=False
        )
    )
    inserted = Field(default=datetime.datetime.today())
    inserted_by: str = Field(nullable=False)

    metadata = MetaData(schema="app")

    __tablename__ = "articles"

    __table_args__ = (
        UniqueConstraint("folder_id", name="articles_unique_folder_id"),
    )
