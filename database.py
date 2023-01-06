"""
Файл с определением базы данных и генерацией
сессий для подключения к ней
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from config import config
from sqlalchemy.pool import AsyncAdaptedQueuePool


DATABASE_URL = f"postgresql+asyncpg://{config.db_info.user}" \
               f":{config.db_info.password}" \
               f"@{config.db_info.host}:{config.db_info.port}" \
               f"/{config.db_info.database}"


engine = create_async_engine(
    DATABASE_URL,
    poolclass=AsyncAdaptedQueuePool,
    pool_size=10,
    max_overflow=10,
    future=True,
    echo=True,
)


async def get_session() -> AsyncSession:
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

