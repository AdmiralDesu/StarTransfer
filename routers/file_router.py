import asyncio
import hashlib
import os
from datetime import datetime
from shutil import make_archive
from typing import Optional
from uuid import uuid4

import aioboto3
import aiofiles
import tqdm
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import config
from database import get_session
from logger import status_logger
from models import Files
from schemas.file_schemas import FileUpload

file_router = APIRouter()
CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB
s3_session = aioboto3.Session()


@file_router.post("/upload_file")
async def upload_file(
        files: list[UploadFile] = File(...),
        comment: Optional[str] = "",
        session: AsyncSession = Depends(get_session)
):
    start_time = datetime.now()
    uploaded_files: list[FileUpload] = []
    async with s3_session.client(
            "s3",
            endpoint_url=config.s3_info.host,
            aws_access_key_id=config.s3_info.access_key,
            aws_secret_access_key=config.s3_info.secret_key
    ) as s3_client:
        for file in files:
            md5_hash = hashlib.md5()
            file_size = 0
            while content := await file.read(CHUNK_SIZE):
                file_size += len(content)
                md5_hash.update(content)
            md5_hash = md5_hash.hexdigest()

            result = await session.execute(
                select(Files)
                .where(Files.md5 == md5_hash)
            )

            file_in_db: Files = result.scalars().first()

            file.file.seek(0)

            if file_in_db:
                uploaded_files.append(FileUpload(
                    detail=f"Файл {file.filename} уже существует!"
                ))
                continue

            await s3_client.upload_fileobj(file.file, "test1", md5_hash)

            new_file = Files(
                title=file.filename,
                md5=md5_hash,
                content_type=file.content_type,
                comment=comment
            )
            session.add(new_file)
            await session.commit()
            await session.refresh(new_file)
            uploaded_files.append(
                FileUpload(
                    keys=str(new_file.keys),
                    md5=new_file.md5,
                    id=new_file.id,
                    detail=f"Файл {new_file.title} успешно загружен"
                )
            )
    all_time = datetime.now() - start_time

    return JSONResponse(
        status_code=200,
        content={
            "all_time": f"{all_time.seconds}.{all_time.microseconds}",
            "uploaded_files": [item.dict() for item in uploaded_files]
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
        bucket = await s3_resource.Bucket("test1")
        async for s3_object in bucket.objects.all():
            print(s3_object)
            s3_obj = await s3_resource.Object("test1", s3_object.key)

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
    obj = await s3_resource.Object(f"test1", f"{file_in_db.md5}")
    result = await obj.get()
    async with aiofiles.open(os.path.join(path_to_dir, file_in_db.title), "wb") as file:
        while content := await result['Body'].read(CHUNK_SIZE):
            await file.write(content)
    return f"Записал файл {file_in_db.title}"


async def tq(flen: int):
    for _ in tqdm.tqdm(range(flen)):
        await asyncio.sleep(0.1)


@file_router.get("/download_all_files")
@status_logger.catch()
async def download_all_files(
        session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Files)
    )
    path_to_dir = f"./temp/{uuid4()}"
    os.mkdir(path_to_dir)
    files_in_db: list[Files] = result.scalars().all()
    tasks = []
    async with s3_session.resource(
            "s3",
            endpoint_url=config.s3_info.host,
            aws_access_key_id=config.s3_info.access_key,
            aws_secret_access_key=config.s3_info.secret_key
    ) as s3_resource:
        for file_in_db in files_in_db:
            # obj = await s3_resource.Object(f"test1", f"{file_in_db.md5}")
            # result = await obj.get()
            # async with aiofiles.open(os.path.join(path_to_dir, file_in_db.title), "wb") as file:
            #     while content := await result['Body'].read(CHUNK_SIZE):
            #         await file.write(content)
            tasks.append(download_and_write_file(path_to_dir, s3_resource, file_in_db))
        #results = await asyncio.gather(*tasks, return_exceptions=True)
        pbar = tqdm.tqdm(total=len(tasks), position=0, ncols=90)
        for task in asyncio.as_completed(tasks):
            value = await task
            pbar.set_description(desc=f" {value}", refresh=True)
            tqdm.tqdm.write(value)
            pbar.update()
        #print(results)
    print("Перехожу к созданию архива")
    make_archive(os.path.join("./temp", "result"), '7zip', path_to_dir)
    print("Архив создан")

    return FileResponse(
        path=os.path.join("./temp", "result.7z"),
        filename="result.7zip"
    )


