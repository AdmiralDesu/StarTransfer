"""
File with app initialization
"""

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from routers import (
    article_router,
    file_router
)

app = FastAPI(
    debug=False,
    title="StarTransferAPI",
    description="API для работы с S3 хранилищем",
    version="0.1"
)

app.include_router(file_router)
app.include_router(article_router)


@app.get("/ping", include_in_schema=False)
async def ping():
    return {
        "ping": "pong"
    }


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse("/docs")

