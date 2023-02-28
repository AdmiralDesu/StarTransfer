import asyncio
import hashlib
import mimetypes
import os
from datetime import datetime
from typing import Optional

import aioboto3
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import config
from database import get_session
from logger import status_logger
from models import Files
from schemas.files import FileUpload
from services import upload_file_service

file_router = APIRouter()
CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB
s3_session = aioboto3.Session()


@file_router.get("/health")
async def health(
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        "select 1"
    )
    return result.scalars().all()


@file_router.post("/upload_file")
async def upload_file(
        folder_id: int,
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_session)
):
    return await upload_file_service(
        file=file,
        folder_id=folder_id,
        session=session
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
            s3_obj = await s3_resource.Object(config.s3_info.bucket, file.md5)
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


@file_router.delete("/delete_all_files")
async def delete_all_files(
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
    )

    files_in_db: list[Files] = result.scalars().all()

    async with s3_session.resource(
            "s3",
            endpoint_url=config.s3_info.host,
            aws_access_key_id=config.s3_info.access_key,
            aws_secret_access_key=config.s3_info.secret_key
    ) as s3_resource:
        bucket = await s3_resource.Bucket(config.s3_info.bucket)
        async for s3_object in bucket.objects.all():
            print(s3_object)
            s3_obj = await s3_resource.Object(config.s3_info.bucket, s3_object.key)

            await s3_obj.delete()
    for file_in_db in files_in_db:
        await session.delete(file_in_db)
        await session.commit()


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
        obj = await s3_resource.Object(config.s3_info.bucket, f"{file_in_db.md5}")
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


@file_router.get("/find_file_by_name")
async def find_file_by_name(
        filename: str,
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
        .where(Files.title.ilike(f"%{filename}%"))
    )

    files_in_db: list[Files] = result.scalars().all()

    return files_in_db


async def download_and_write_file(
        path_to_dir: str,
        s3_resource,
        file_in_db: Files
):
    obj = await s3_resource.Object(config.s3_info.bucket, f"{file_in_db.md5}")
    result = await obj.get()
    async with aiofiles.open(os.path.join(path_to_dir, file_in_db.title), "wb") as file:
        while content := await result['Body'].read(CHUNK_SIZE):
            await file.write(content)
    return f"Записал файл {file_in_db.title}"


@file_router.get("/download_all_files")
@status_logger.catch()
async def download_all_files(
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
    )
    files_in_db: list[Files] = result.scalars().all()
    tasks = []
    async with s3_session.resource(
            "s3",
            endpoint_url=config.s3_info.host,
            aws_access_key_id=config.s3_info.access_key,
            aws_secret_access_key=config.s3_info.secret_key
    ) as s3_resource:
        for file_in_db in files_in_db:
            tasks.append(download_and_write_file(r"E:\temp", s3_resource, file_in_db))
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return True


async def upload_filename(
    fullpath: str,
    session: AsyncSession
):
    start_time = datetime.now()
    md5_hash = hashlib.md5()
    file_size = 0
    filename = os.path.basename(fullpath)
    uploaded_file = FileUpload()
    async with s3_session.client(
            "s3",
            endpoint_url=config.s3_info.host,
            aws_access_key_id=config.s3_info.access_key,
            aws_secret_access_key=config.s3_info.secret_key
    ) as s3_client:

        async with aiofiles.open(fullpath, "rb") as file:
            while content := await file.read(CHUNK_SIZE):
                file_size += len(content)
                md5_hash.update(content)

        md5_hash = str(md5_hash.hexdigest())

        print(f"У Файла {filename} {md5_hash=}")

        result = await session.execute(
            select(Files)
            .where(Files.md5 == md5_hash)
        )

        file_in_db: Files = result.scalars().first()

        if file_in_db:
            print(f"Файл {filename} уже существует!")
            uploaded_file.detail = f"Файл {filename} уже существует!"
            return uploaded_file

        async with aiofiles.open(fullpath, "rb") as file:
            await s3_client.upload_fileobj(file, config.s3_info.bucket, md5_hash)

        mime_type = mimetypes.guess_type(url=filename)[0]

        print(f"У файла {filename} {mime_type=}")

        new_file = Files(
            title=filename,
            md5=md5_hash,
            content_type=mime_type,
            comment="",
            file_size=file_size
        )
        session.add(new_file)
        await session.commit()
        await session.refresh(new_file)
        uploaded_file.keys = str(new_file.keys),
        uploaded_file.md5 = new_file.md5,
        uploaded_file.id = new_file.id,
        uploaded_file.detail = f"Файл {new_file.title} успешно загружен"

    all_time = datetime.now() - start_time
    print(f"Файл {new_file.title} записался за {all_time}")
    await session.close()
    return uploaded_file


@file_router.get("/upload_dir")
async def upload_dir(
        path_to_dir: str
):
    if not os.path.exists(path_to_dir):
        raise HTTPException(status_code=400, detail="Директории не существует!")

    tasks = []

    for root, dirs, files in os.walk(path_to_dir):
        for file in files:
            fullpath = os.path.join(root, file)
            tasks.append(
                upload_filename(
                    fullpath=fullpath,
                    session=await anext(get_session())
                )
            )
    results = asyncio.gather(*tasks)

    print(results)

    return {
        "message": "uploaded"
    }

