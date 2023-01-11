import hashlib
from datetime import datetime

import aioboto3
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import config
from database import get_session
from models import Files

file_router = APIRouter()
CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB
s3_session = aioboto3.Session()


@file_router.post("/upload_file")
async def upload_file(
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_session)
):
    start_time = datetime.now()

    md5_hash = hashlib.md5()
    while content := await file.read(CHUNK_SIZE):
        md5_hash.update(content)
    md5_hash = md5_hash.hexdigest()

    result = await session.execute(
        select(Files)
        .where(Files.md5 == md5_hash)
    )

    file_in_db: Files = result.scalars().first()

    file.file.seek(0)

    if file_in_db:
        raise HTTPException(status_code=400, detail="Такой файл уже существует!")

    async with s3_session.client(
            "s3",
            endpoint_url=config.s3_info.host,
            aws_access_key_id=config.s3_info.access_key,
            aws_secret_access_key=config.s3_info.secret_key
    ) as s3_client:
        await s3_client.upload_fileobj(file.file, "test1", md5_hash)

    new_file = Files(
        title=file.filename,
        md5=md5_hash,
        content_type=file.content_type
    )
    session.add(new_file)
    await session.commit()
    await session.refresh(new_file)

    all_time = datetime.now() - start_time

    return JSONResponse(
        status_code=200,
        content={
            "all_time": f"{all_time.seconds}.{all_time.microseconds}",
            "hash": md5_hash,
            "file_id": new_file.id,
            "keys": f"{new_file.keys}"
        }
    )


@file_router.get("/get_file_info")
async def get_file_info(
        keys: UUID4,
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
        .where(Files.keys == keys)
    )

    file: Files = result.scalars().first()

    if file:
        return file
    else:
        raise HTTPException(
            status_code=404,
            detail=f"Файл с {keys=} не найден!"
        )


@file_router.delete("/delete_file")
async def delete_file(
        keys: UUID4,
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
        .where(Files.keys == keys)
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
            "file_key": f"{keys}"
        }
    )


@file_router.get("/download_file")
async def download_file(
        keys: UUID4,
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
        .where(Files.keys == keys)
    )

    file_in_db: Files = result.scalars().first()

    if not file_in_db:
        raise HTTPException(status_code=404, detail=f"Файла с {keys} не существует!")

    async with s3_session.resource(
            "s3",
            endpoint_url=config.s3_info.host,
            aws_access_key_id=config.s3_info.access_key,
            aws_secret_access_key=config.s3_info.secret_key
    ) as s3_resource:
        obj = await s3_resource.Object(f"test1", f"{file_in_db.md5}")
        result = await obj.get()
        async with aiofiles.open(f"./temp/{file_in_db.title}", "wb") as file:
            while content := await result['Body'].read(CHUNK_SIZE):
                await file.write(content)

        return FileResponse(
            f"./temp/{file_in_db.title}",
            media_type=result['ResponseMetadata']['HTTPHeaders']['content-type'],
            filename=file_in_db.title
        )


@file_router.get("/get_all_files")
async def get_all_files(
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
    )

    return result.scalars().all()

