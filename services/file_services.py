import hashlib
from datetime import datetime
from typing import Optional, Union, Tuple
from uuid import uuid4

import aioboto3
from fastapi import UploadFile, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import config
from models import Files, FilesMD5
from schemas import FileUpload
from logger import file_logger
from pydantic import UUID4

s3_session = aioboto3.Session()

CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB


@file_logger.catch()
async def get_md5_and_file_size(
        file: UploadFile
):
    try:
        md5_hash = hashlib.md5()
        file_size = 0
        while content := await file.read(CHUNK_SIZE):
            file_size += len(content)
            md5_hash.update(content)
        md5_hash = str(md5_hash.hexdigest())
        file.file.seek(0)
        return md5_hash, file_size, ""
    except Exception as error:
        return "", 0, JSONResponse(
            status_code=500,
            content={
                "message": "Возникла ошибка при обработке файла",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def check_md5_in_db(
        md5_hash: str,
        session: AsyncSession
) -> Tuple[bool, Union[JSONResponse, None]]:
    try:
        result = await session.execute(
            select(FilesMD5)
            .where(FilesMD5.id == md5_hash)
        )

        file_in_db: Files = result.scalars().first()
        print(file_in_db)
        if file_in_db:
            print("md5 есть")
            return True, None
        return False, None
    except Exception as error:
        return False, JSONResponse(
            status_code=500,
            content={
                "message": "Ошибка проверки файла в базе",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def upload_file_to_s3(
        file: UploadFile,
        md5_hash: str
):
    try:
        async with s3_session.client(
                "s3",
                endpoint_url=config.s3_info.host,
                aws_access_key_id=config.s3_info.access_key,
                aws_secret_access_key=config.s3_info.secret_key
        ) as s3_client:

            await s3_client.upload_fileobj(file.file, config.s3_info.bucket, md5_hash)
        return None
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Не удалась загрузка на s3",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def create_new_files_md5(
        md5_hash: str,
        file_size: str,
        mime_type: str,
        session: AsyncSession
):
    try:
        exist, error = await check_md5_in_db(
            md5_hash=md5_hash,
            session=session
        )
        if error:
            return error
        if exist:
            return None
        files_md5 = FilesMD5(
            id=md5_hash,
            mime_type=mime_type,
            file_size=file_size,
            inserted_by="StarWorker"
        )
        session.add(files_md5)
        await session.commit()
        return None
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Во время сохранения md5 произошла ошибка",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def create_new_file(
        filename: str,
        folder_id: int,
        md5_hash: str,
        session: AsyncSession
):
    try:
        new_file = Files(
            filename=filename,
            folder_id=folder_id,
            keys=uuid4(),
            inserted_by="StarWorker",
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
                "message": "Во время сохранения файла в базе произошла ошибка",
                "error": f"{error=}"
            }
        )


@file_logger.catch()
async def upload_file_service(
        session: AsyncSession,
        file: UploadFile,
        folder_id: int
):
    try:
        start_time = datetime.now()
        md5_hash, file_size, error = await get_md5_and_file_size(
            file=file
        )
        if error:
            return error

        error = await upload_file_to_s3(
            file=file,
            md5_hash=md5_hash
        )
        if error:
            return error

        error = await create_new_files_md5(
            md5_hash=md5_hash,
            file_size=file_size,
            mime_type=file.content_type,
            session=session
        )
        if error:
            return error

        new_file, error = await create_new_file(
            filename=file.filename,
            folder_id=folder_id,
            md5_hash=md5_hash,
            session=session
        )
        if error:
            return error

        uploaded_file = FileUpload(
            keys=str(new_file.keys),
            md5=new_file.md5,
            id=new_file.id,
            detail=f"Файл {new_file.filename} успешно загружен"
        )
        all_time = datetime.now() - start_time
        return JSONResponse(
            status_code=200,
            content={
                "all_time": f"{all_time.seconds}.{all_time.microseconds}",
                "info": uploaded_file.dict()
            }
        )
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Во время работы по сохранению файла произошла ошибка",
                "error": f"{error=}"
            }
        )
