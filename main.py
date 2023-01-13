import os.path
import shutil

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from routers import file_router

app = FastAPI(
    debug=False,
    title="StarTransferAPI",
    description="API для работы с S3 хранилищем",
    version="0.1"
)

app.include_router(file_router)

app.scheduler = AsyncIOScheduler()
app.scheduler.start()


@app.get("/", include_in_schema=False)
async def redirect_to_docs():
    return RedirectResponse("/docs")


@app.scheduler.scheduled_job(trigger=CronTrigger(minute=10))
async def clear_temp():
    folder = "./temp"
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        time_of_creation = None




