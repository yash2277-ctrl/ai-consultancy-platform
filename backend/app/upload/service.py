"""
Upload service — handles secure file saving and triggers the embedding pipeline.
"""

import os
import uuid
import logging
from fastapi import UploadFile

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models import UploadedFile, FileStatus, Project
from app.rag.vector_store import VectorStore

settings = get_settings()
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"pdf", "docx", "csv", "xlsx"}
MAX_SIZE = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024  # bytes


def _get_extension(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


async def validate_and_save_file(
    file: UploadFile,
    project_id: uuid.UUID,
    db: AsyncSession,
) -> UploadedFile:
    """
    Validate file type/size, save to disk, create DB record.
    """
    ext = _get_extension(file.filename or "")
    if ext not in ALLOWED_TYPES:
        raise ValueError(f"Unsupported file type '.{ext}'. Allowed: {ALLOWED_TYPES}")

    # Read file content
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise ValueError(f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit")

    # Check project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError(f"Project {project_id} not found")

    # Save to disk
    file_id = uuid.uuid4()
    safe_name = f"{file_id}.{ext}"
    project_dir = os.path.join(settings.UPLOAD_DIR, str(project_id))
    os.makedirs(project_dir, exist_ok=True)
    file_path = os.path.join(project_dir, safe_name)

    with open(file_path, "wb") as f:
        f.write(content)

    # Create DB record
    db_file = UploadedFile(
        id=file_id,
        filename=safe_name,
        original_name=file.filename or "unknown",
        file_type=ext,
        file_size=len(content),
        file_path=file_path,
        status=FileStatus.PENDING,
        project_id=project_id,
    )
    db.add(db_file)
    await db.flush()
    await db.refresh(db_file)

    return db_file


async def process_file_embedding(file_id: uuid.UUID, db: AsyncSession) -> None:
    """
    Background task — reads the file, embeds it, stores vectors.
    """
    result = await db.execute(
        select(UploadedFile).where(UploadedFile.id == file_id)
    )
    db_file = result.scalar_one_or_none()
    if not db_file:
        logger.error(f"File {file_id} not found for embedding")
        return

    try:
        db_file.status = FileStatus.PROCESSING
        await db.commit()

        chunk_count = await VectorStore.ingest_file(
            file_path=db_file.file_path,
            file_type=db_file.file_type,
            file_id=str(db_file.id),
            project_id=str(db_file.project_id),
        )

        db_file.chunk_count = chunk_count
        db_file.status = FileStatus.COMPLETED
        await db.commit()
        logger.info(f"File {file_id} embedded: {chunk_count} chunks")

    except Exception as exc:
        logger.exception(f"Embedding failed for file {file_id}: {exc}")
        db_file.status = FileStatus.FAILED
        await db.commit()
