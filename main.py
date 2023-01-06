from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse
from database import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import Files
from routers import file_router

app = FastAPI(
    debug=False,
    title="StarTransferAPI",
    description="API для работы с S3 хранилищем",
    version="0.1"
)

app.include_router(file_router)


@app.get("/")
async def redirect_to_docs():
    return RedirectResponse("/docs")




