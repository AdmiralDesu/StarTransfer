"""
Файл с запуском API
"""
from uvicorn import run
from logger import status_logger
from config import config


if __name__ == "__main__":
    status_logger.info("Стартую API")
    try:
        run(
            app="main:app",
            host=config.api_info.host,
            port=config.api_info.port,
            workers=1
        )
    except Exception as run_error:
        status_logger.error("Во время запуска API произошла ошибка")
        status_logger.error(f"{run_error=}")
        raise run_error
