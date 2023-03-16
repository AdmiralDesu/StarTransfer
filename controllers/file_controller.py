"""
Модуль с контроллерами для разных сервисов
"""
from datetime import datetime

from fastapi import UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from logger import file_logger
from schemas.files import FileUpload
from services.file_services import (
    get_md5_and_file_size,
    upload_file_to_s3,
    create_new_files_md5,
    create_new_file
)


@file_logger.catch()
async def upload_file_controller(
        session: AsyncSession,
        file: UploadFile,
        folder_id: int
) -> JSONResponse:
    """
    - Controller for file upload
    - **session**: Database session (auto)
    - **file**: File to upload
    - **folder_id**: ID of folder for file
    - **return**: Error of file info in JSONResponse
    """
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
            detail=f"File '{new_file.filename}' successfully uploaded"
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
                "message": "Error while file upload",
                "error": f"{error=}"
            }
        )
