"""
Файл с запуском API
"""
from uvicorn import run
from logger import status_logger
from config import config
import shutil
from py7zr import unpack_7zarchive, pack_7zarchive

shutil.register_unpack_format('7zip', ['.7z', ".7zip"], unpack_7zarchive)
shutil.register_archive_format('7zip', pack_7zarchive, description='7zip archive')

if __name__ == "__main__":
    status_logger.info("Стартую API")
    try:
        run(
            app="main:app",
            host=config.api_info.host,
            port=config.api_info.port
        )
    except Exception as run_error:
        status_logger.error("Во время запуска API произошла ошибка")
        status_logger.error(f"{run_error=}")
        raise run_error
