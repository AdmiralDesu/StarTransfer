"""
Файл с обработкой конфига
"""
from yaml import YAMLError, load, SafeLoader
from pydantic import BaseModel
from logger import status_logger


class DBInfo(BaseModel):
    """
    Класс с описанием подключения к БД
    """
    db_name: str
    db_host: str
    db_port: int
    db_user: str
    db_password: str


class S3Info(BaseModel):
    """
    Класс с описанием подключения к S3
    """
    access_key: str
    secret_key: str


class APIInfo(BaseModel):
    """
    Класс с параметрами API
    """
    host: str
    port: int


class Config(BaseModel):
    """
    Класс с параметрами конфига
    """
    api_info: APIInfo
    s3_info: S3Info
    db_info: DBInfo


with open("./config.yaml", "r", encoding="utf-8") as stream:
    try:
        _config = load(stream=stream, Loader=SafeLoader)
        config = Config(**_config)
    except YAMLError as config_parse_error:
        status_logger.error("Во время обработки конфига возникла ошибка")
        status_logger.error(f"{config_parse_error=}")
        raise config_parse_error
    except FileNotFoundError as config_not_found_error:
        status_logger.error("Файл с конфигом не найден!")
        raise config_not_found_error
