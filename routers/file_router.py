"""
Router for file services
"""
import asyncio
import os
from urllib.parse import unquote

import aioboto3
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from pydantic import UUID4
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from config import config
from controllers.file_controller import upload_file_controller
from database import get_session
from logger import status_logger
from models.files import Files

file_router = APIRouter(
    prefix="/file",
    tags=["Files"]
)
CHUNK_SIZE = 100 * 1024 * 1024  # 100 MB
s3_session = aioboto3.Session()


@file_router.get(
    "/health",
    include_in_schema=False
)
async def health(
        session: AsyncSession = Depends(get_session)
):
    """
    - DB health endpoint
    - **session**: Database session
    - **return**: [1]
    """
    result = await session.execute(
        "select 1"
    )
    return result.scalars().all()


@file_router.post(
    "/upload_file_to_folder"
)
async def upload_file_to_folder(
        folder_id: int,
        file: UploadFile = File(...),
        session: AsyncSession = Depends(get_session)
):
    """
    - File upload endpoint
    - **folder_id**: ID of folder for file
    - **file**: File to upload
    - **session**: Database session (auto)
    - **return**: Error or file info
    """
    file.filename = unquote(file.filename, "utf-8")

    return await upload_file_controller(
        file=file,
        folder_id=folder_id,
        session=session
    )


@file_router.get(
    "/get_file_info"
)
async def get_file_info(
        keys: UUID4,
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for getting file info
    - **keys**: Keys of file
    - **session**: Database session (auto)
    - **return**: Error or file info
    """
    result = await session.execute(
        select(Files)
        .where(Files.keys == keys)
    )

    file: Files = result.scalars().first()

    if file:
        return file
    return JSONResponse(
        status_code=404,
        content={
            "message": f"File with {keys=} is not found",
            "error": None
        }
    )


@file_router.delete(
    "/delete_file"
)
async def delete_file(
        keys: UUID4,
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for file deletion
    - **keys**: Keys of file
    - **session**: Database session (auto)
    - **return**: Error or file keys
    """
    try:
        result = await session.execute(
            select(Files)
            .where(Files.keys == keys)
        )

        file: Files = result.scalars().first()
        if not file:
            return JSONResponse(
                status_code=404,
                content={
                    "message": f"File with {keys=} is not found",
                    "error": None
                }
            )

        await session.delete(file)
        await session.commit()

        return JSONResponse(
            status_code=200,
            content={
                "message": "File was deleted",
                "file_key": f"{keys}"
            }
        )
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Error while file deletion",
                "error": f"{error=}"
            }
        )


@file_router.get(
    "/download_file"
)
async def download_file(
        keys: UUID4,
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for file downloading
    - **keys**: Keys of file
    - **session**: Database session (auto)
    - **return**: Error or file
    """
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
        obj = await s3_resource.Object(config.s3_info.bucket, f"files.md5/{file_in_db.md5}")
        result = await obj.get()
        async with aiofiles.open(f"./temp/{file_in_db.filename}", "wb") as file:
            while content := await result['Body'].read(CHUNK_SIZE):
                await file.write(content)

        return FileResponse(
            f"./temp/{file_in_db.filename}",
            media_type=result['ResponseMetadata']['HTTPHeaders']['content-type'],
            filename=file_in_db.filename
        )


@file_router.get(
    "/get_all_files"
)
async def get_all_files(
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for getting all file rows
    - **session**: Database session (auto)
    - **return**: Error or file
    """
    result = await session.execute(
        select(Files)
    )

    return result.scalars().all()


@file_router.get(
    "/find_file_by_name"
)
async def find_file_by_name(
        filename: str,
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for finding file by filename
    - **filename**: Name of file
    - **session**: Database session (auto)
    - **return**: Error or file
    """
    result = await session.execute(
        select(Files)
        .where(Files.filename.ilike(f"%{filename}%"))
    )

    files_in_db: list[Files] = result.scalars().all()

    return files_in_db


async def download_and_write_file(
        path_to_dir: str,
        s3_resource,
        file_in_db: Files
):
    """
    - Function for downloading and write file in dir
    - **path_to_dir**: Path to download dir
    - **s3_resource**: S3 resource object
    - **file_in_db**: Model of file in db
    - **return**: Message with filename
    """
    obj = await s3_resource.Object(config.s3_info.bucket, f"{file_in_db.md5}")
    result = await obj.get()
    async with aiofiles.open(os.path.join(path_to_dir, file_in_db.filename), "wb") as file:
        while content := await result['Body'].read(CHUNK_SIZE):
            await file.write(content)
    return f"Written file {file_in_db.filename}"


@file_router.get(
    "/download_all_files"
)
@status_logger.catch()
async def download_all_files(
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for all files download
    - **session**: Database session (auto)
    - **return**: Zip archive with all files
    """
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
            tasks.append(
                asyncio.create_task(
                    download_and_write_file(r"E:\temp", s3_resource, file_in_db)
                )
            )
        await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
    return True



