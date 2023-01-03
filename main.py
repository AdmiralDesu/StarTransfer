from fastapi import FastAPI, Depends
from fastapi.responses import RedirectResponse

app = FastAPI(
    debug=False,
    title="StarTransferAPI",
    description="API для работы с S3 хранилищем",
    version="0.1"
)


@app.get("/")
async def redirect_to_docs():
    return RedirectResponse("/docs")

