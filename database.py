"""
Файл с определением базы данных и генерацией
сессий для подключения к ней
"""
from typing import AsyncGenerator, Union

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import AsyncAdaptedQueuePool

from config import config


DATABASE_URL = f"postgresql+asyncpg://{config.db_info.db_user}" \
               f":{config.db_info.db_password}" \
               f"@{config.db_info.db_host}:{config.db_info.db_port}" \
               f"/{config.db_info.db_name}"

engine = create_async_engine(
    DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=70,
    max_overflow=10,
    future=True,
    echo=True,
    pool_pre_ping=True
)


async def get_session() -> Union[AsyncSession, AsyncGenerator]:
    """
    Получение сессии к базе.
    :return: Асинхронная сессия к базе данных
    """
    async_session = sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False
    )

    async with async_session() as session:
        yield session

