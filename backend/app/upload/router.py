"""
Upload API routes — file upload + project CRUD.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db, AsyncSessionLocal
from app.auth.dependencies import get_current_user
from app.models import User, Project, UploadedFile
from app.schemas import ProjectCreate, ProjectResponse, ProjectDetail, FileResponse
from app.upload.service import validate_and_save_file, process_file_embedding

router = APIRouter(tags=["Projects & Uploads"])


# ── Project endpoints ────────────────────────────────────────────────────────

@router.post("/projects", response_model=ProjectResponse, status_code=201)
async def create_project(
    payload: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = Project(
        name=payload.name,
        description=payload.description,
        industry=payload.industry,
        owner_id=user.id,
    )
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return ProjectResponse.model_validate(project)


@router.get("/projects", response_model=List[ProjectDetail])
async def list_projects(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.owner_id == user.id).order_by(Project.created_at.desc())
    )
    projects = result.scalars().all()

    details = []
    for p in projects:
        file_count = (await db.execute(
            select(func.count()).select_from(UploadedFile).where(UploadedFile.project_id == p.id)
        )).scalar() or 0

        from app.models import ConsultingReport
        report_count = (await db.execute(
            select(func.count()).select_from(ConsultingReport).where(ConsultingReport.project_id == p.id)
        )).scalar() or 0

        details.append(ProjectDetail(
            **ProjectResponse.model_validate(p).model_dump(),
            file_count=file_count,
            report_count=report_count,
        ))

    return details


@router.get("/projects/{project_id}", response_model=ProjectDetail)
async def get_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_count = (await db.execute(
        select(func.count()).select_from(UploadedFile).where(UploadedFile.project_id == project.id)
    )).scalar() or 0

    from app.models import ConsultingReport
    report_count = (await db.execute(
        select(func.count()).select_from(ConsultingReport).where(ConsultingReport.project_id == project.id)
    )).scalar() or 0

    return ProjectDetail(
        **ProjectResponse.model_validate(project).model_dump(),
        file_count=file_count,
        report_count=report_count,
    )


@router.delete("/projects/{project_id}", status_code=204)
async def delete_project(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Clean up vector store data
    try:
        from app.rag.vector_store import VectorStore
        VectorStore.delete_project_data(str(project_id))
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(f"Vector cleanup failed for project {project_id}: {exc}")

    await db.delete(project)


# ── File Upload ──────────────────────────────────────────────────────────────

@router.post("/upload", response_model=FileResponse, status_code=201)
async def upload_file(
    background_tasks: BackgroundTasks,
    project_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify user owns the project
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        db_file = await validate_and_save_file(file, project_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Trigger embedding in background with a fresh DB session
    async def _embed_task(fid: uuid.UUID):
        async with AsyncSessionLocal() as session:
            await process_file_embedding(fid, session)
            await session.commit()

    background_tasks.add_task(_embed_task, db_file.id)

    return FileResponse.model_validate(db_file)


@router.get("/projects/{project_id}/files", response_model=List[FileResponse])
async def list_files(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify ownership
    proj = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    if not proj.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(UploadedFile).where(UploadedFile.project_id == project_id)
        .order_by(UploadedFile.uploaded_at.desc())
    )
    files = result.scalars().all()
    return [FileResponse.model_validate(f) for f in files]
