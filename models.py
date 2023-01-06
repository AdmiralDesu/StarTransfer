import datetime

from sqlmodel import SQLModel, Field, UniqueConstraint, MetaData


class BaseFiles(SQLModel):
    title: str = Field()
    md5: str = Field()
    created_at = Field(default=datetime.datetime.today())


class Files(BaseFiles, table=True):
    id: int = Field(primary_key=True, index=True, nullable=False)
    metadata = MetaData(schema="app")

    __tablename__ = "files"

    __table_args__ = (
        UniqueConstraint("md5", name="unique_md5"),
    )

