"""
Module for file services
"""
# coding: utf8
import hashlib
from datetime import datetime
from typing import Tuple, Optional
from uuid import uuid4

import aioboto3
from fastapi import UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import config
from logger import file_logger
from models.files import Files, FilesMD5

s3_session = aioboto3.Session()

CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB


@file_logger.catch()
async def get_md5_and_file_size(
        file: UploadFile
) -> Tuple[str, int, Optional[JSONResponse]]:
    """
    Function for md5 calculation
    :param file: File object
    :return:
    """
    try:
        md5_hash = hashlib.md5()
        file_size = 0
        while content := await file.read(CHUNK_SIZE):
            file_size += len(content)
            md5_hash.update(content)
        md5_hash = str(md5_hash.hexdigest())
        file.file.seek(0)
        return md5_hash, file_size, None
    except Exception as error:
        return "", 0, JSONResponse(
            status_code=500,
            content={
                "message": "Error while md5 calculation",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def check_md5_in_db(
        md5_hash: str,
        session: AsyncSession
) -> Tuple[bool, Optional[JSONResponse]]:
    """
    Function for checking md5 sum in db
    :param md5_hash: md5 of file
    :param session: session to database
    :return:
    """
    try:
        result = await session.execute(
            select(FilesMD5)
            .where(FilesMD5.id == md5_hash)
        )

        file_in_db: Files = result.scalars().first()
        if file_in_db:
            return True, None
        return False, None
    except Exception as error:
        return False, JSONResponse(
            status_code=500,
            content={
                "message": "Error while checking for existing md5",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def upload_file_to_s3(
        file: UploadFile,
        md5_hash: str
) -> Optional[JSONResponse]:
    """
    Function for uploading file to s3
    :param file: File object
    :param md5_hash: md5 hash of file
    :return:
    """
    try:
        async with s3_session.client(
                "s3",
                endpoint_url=config.s3_info.host,
                aws_access_key_id=config.s3_info.access_key,
                aws_secret_access_key=config.s3_info.secret_key
        ) as s3_client:
            await s3_client.upload_fileobj(
                file.file,
                config.s3_info.bucket,
                f"files.md5/{md5_hash}"
            )
        return None
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Error while uploading to s3",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def create_new_files_md5(
        md5_hash: str,
        file_size: int,
        mime_type: str,
        session: AsyncSession,
) -> Optional[JSONResponse]:
    """
    Function for creating new md5 row in db
    :param md5_hash: md5 hash of file.
    :param file_size: file size
    :param mime_type: type of file
    :param session: session to db
    :return:
    """
    try:
        files_md5 = FilesMD5(
            id=md5_hash,
            mime_type=mime_type,
            file_size=file_size,
            inserted=datetime.today(),
            inserted_by="StarWorker"
        )
        session.add(files_md5)
        await session.commit()
        return None
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Error while creating new md5 row in db",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def create_new_file(
        filename: str,
        folder_id: int,
        md5_hash: str,
        session: AsyncSession
) -> Tuple[Optional[Files], Optional[JSONResponse]]:
    """
    Function for creating new file row in db
    :param filename: name of file
    :param folder_id: id of folder for file
    :param md5_hash: md5 hash of file
    :param session: session to db
    :return:
    """
    try:
        new_file = Files(
            filename=filename,
            folder_id=folder_id,
            keys=uuid4(),
            inserted_by="StarWorker",
            inserted=datetime.today(),
            md5=md5_hash
        )
        session.add(new_file)
        await session.commit()
        await session.refresh(new_file)
        return new_file, None
    except Exception as error:
        return None, JSONResponse(
            status_code=500,
            content={
                "message": "Error while creating new file row in db",
                "error": f"{error=}"
            }
        )
