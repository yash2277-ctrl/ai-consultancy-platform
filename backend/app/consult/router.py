"""
Consult API routes — trigger AI consultation, check status, retrieve reports.
"""

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db, AsyncSessionLocal
from app.auth.dependencies import get_current_user
from app.models import User, Project
from app.schemas import ConsultRequest, ReportResponse, ReportSummary
from app.consult.service import create_report, get_report, list_reports
from app.agents.process_manager import ProcessManager

router = APIRouter(tags=["Consulting"])


@router.post("/consult", response_model=ReportResponse, status_code=202)
async def start_consultation(
    payload: ConsultRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Accept a project_id + goal_statement, create a report record,
    and launch the multi-agent pipeline as a background task.
    """
    # Verify user owns the project
    result = await db.execute(
        select(Project).where(Project.id == payload.project_id, Project.owner_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    try:
        report = await create_report(db, payload.project_id, payload.goal_statement)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Launch background task with fresh session
    async def _run_pipeline(report_id: uuid.UUID):
        async with AsyncSessionLocal() as session:
            pm = ProcessManager(session)
            await pm.run_consultation(report_id)

    background_tasks.add_task(_run_pipeline, report.id)

    return ReportResponse.model_validate(report)


@router.get("/reports/{report_id}", response_model=ReportResponse)
async def get_report_detail(
    report_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Get full report details including AI analyses."""
    report = await get_report(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Verify ownership
    result = await db.execute(
        select(Project).where(Project.id == report.project_id, Project.owner_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse.model_validate(report)


@router.get("/projects/{project_id}/reports", response_model=List[ReportSummary])
async def list_project_reports(
    project_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """List all reports for a project."""
    result = await db.execute(
        select(Project).where(Project.id == project_id, Project.owner_id == user.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Project not found")

    reports = await list_reports(db, project_id)
    return [ReportSummary.model_validate(r) for r in reports]
