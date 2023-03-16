from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_session
from models.articles import Article
from models.files import Files, FilesTree

article_router = APIRouter(
    prefix="/article",
    tags=['Article']
)


@article_router.delete(
    "/folder_delete"
)
async def delete_all_files(
        folder_id: int,
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for folder deletion
    - **session**: Database session
    - **return**: None
    """
    result = await session.execute(
        select(Files)
        .where(Files.folder_id == folder_id)
    )

    files_in_db: list[Files] = result.scalars().all()

    for file_in_db in files_in_db:
        await session.delete(file_in_db)
        await session.commit()

    result = await session.execute(
        select(FilesTree)
        .where(FilesTree.id == folder_id)
    )

    folder = result.scalars().first()
    await session.delete(folder)
    await session.commit()


@article_router.get(
    "/create_article"
)
async def create_article(
        title: str,
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for article creation
    - **title**: Title of article
    - **session**: Database session (auto)
    - **return**: Article id and folder id or error
    """
    try:
        new_folder = FilesTree(
            name="root",
            inserted=datetime.today(),
            inserted_by="star_worker"
        )

        session.add(new_folder)
        await session.commit()
        await session.refresh(new_folder)
        new_folder.parent_id = new_folder.id
        await session.commit()

        new_article = Article(
            title=title,
            folder_id=new_folder.id,
            inserted=datetime.today(),
            inserted_by="star_worker"
        )

        session.add(new_article)
        await session.commit()
        await session.refresh(new_article)
        return {
            "message": "new article was created",
            "id": new_article.id,
            "folder_id": new_article.folder_id
        }
    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "There was a error while creating article",
                "error": f"{error=}"
            }
        )


@article_router.get("/create_new_folder")
async def create_new_folder(
        name: str,
        article_id: int,
        session: AsyncSession = Depends(get_session)
):
    """
    - Endpoint for new folder creation
    - **name**: Name of folder
    - **article_id**: ID of article with new folder
    - **session**: Database session (auto)
    - **return**: Folder id or error
    """
    try:
        results = await session.execute(
            select(Article)
            .where(Article.id == article_id)
        )
        article: Article = results.scalars().first()
        if not article:
            return JSONResponse(
                status_code=404,
                content={
                    "message": f"Article with {article_id=} is not exists"
                }
            )

        new_folder = FilesTree(
            parent_id=article.folder_id,
            name=name,
            inserted=datetime.today(),
            inserted_by="star_worker"
        )
        session.add(new_folder)
        await session.commit()
        return JSONResponse(
            status_code=200,
            content={
                "message": "New folder was created",
                "folder_id": new_folder.id
            }
        )

    except Exception as error:
        return JSONResponse(
            status_code=500,
            content={
                "message": "There was a error while creating new folder",
                "error": f"{error=}"
            }
        )

