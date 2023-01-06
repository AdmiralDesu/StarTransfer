import hashlib
from datetime import datetime

import aioboto3
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import config
from database import get_session
from models import Files

file_router = APIRouter()
CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB
s3_session = aioboto3.Session()


@file_router.get("/get_all_files")
async def get_all_files(
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
    )

    return result.scalars().all()


@file_router.delete("/delete_file")
async def delete_file(
        file_id: int,
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
        .where(Files.id == file_id)
    )

    file: Files = result.scalars().first()
    if not file:
        raise HTTPException(status_code=404, detail="Файл с таким id не найден!")
    else:
        async with s3_session.resource(
                "s3",
                endpoint_url=config.s3_info.host,
                aws_access_key_id=config.s3_info.access_key,
                aws_secret_access_key=config.s3_info.secret_key
        ) as s3_resource:
            s3_obj = await s3_resource.Object("test1", file.md5)
            await s3_obj.delete()

        await session.delete(file)
        await session.commit()

    return JSONResponse(
        status_code=200,
        content={
            "message": "Файл удален",
            "file_id": file_id
        }
    )


@file_router.get("/get_file_info")
async def get_file_info(
        file_id: int,
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
        .where(Files.id == file_id)
    )

    file: Files = result.scalars().first()

    if file:
        return file
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Файл с {file_id=} не найден!"
        )


async def get_hash(filename):
    md5_hash = hashlib.md5()
    async with aiofiles.open(filename, "rb") as f:
        while content := await f.read(CHUNK_SIZE):
            md5_hash.update(content)
    return md5_hash


@file_router.post("/test_upload")
async def upload_file_test(
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_session)
):
    start_time = datetime.now()

    md5_hash = hashlib.md5()
    while content := await file.read(CHUNK_SIZE):
        md5_hash.update(content)
    md5_hash = md5_hash.hexdigest()
    file.file.seek(0)

    upload_time = datetime.now() - start_time
    start_hash = datetime.now()
    hash_time = datetime.now() - start_hash
    all_time = datetime.now() - start_time

    async with s3_session.client(
        "s3",
        endpoint_url=config.s3_info.host,
        aws_access_key_id=config.s3_info.access_key,
        aws_secret_access_key=config.s3_info.secret_key
    ) as s3_client:
        await s3_client.upload_fileobj(file.file, "test1", md5_hash)

    new_file = Files(
        title=file.filename,
        md5=md5_hash
    )
    session.add(new_file)
    await session.commit()
    await session.refresh(new_file)

    return {
        "upload_time": f"{upload_time.seconds}.{upload_time.microseconds}",
        "hash_time": f"{hash_time.seconds}.{hash_time.microseconds}",
        "all_time": f"{all_time.seconds}.{all_time.microseconds}",
        "hash": md5_hash,
        "file_id": new_file.id
    }
