from loguru import logger


def create_filter(
        name: str
):
    def log_filter(record: dict):
        return record["extra"].get("name") == name
    return log_filter


logger.add(
    sink="./logs/status_logs/status_logs.log",
    level="INFO",
    filter=create_filter("status_logs"),
    enqueue=True,
    rotation="100 MB",
    retention="30 days",
    compression="gz"
)

logger.add(
    sink="./logs/file_logs/file_logs.log",
    level="INFO",
    filter=create_filter("file_logs"),
    enqueue=True,
    rotation="100 MB",
    retention="30 days",
    compression="gz"
)

status_logger = logger.bind(name="status_logs")
file_logger = logger.bind(name="file_logs")
