"""
Consult service — creates report records and launches the AI pipeline.
"""

import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import ConsultingReport, ReportStatus, Project

logger = logging.getLogger(__name__)


async def create_report(
    db: AsyncSession,
    project_id: uuid.UUID,
    goal_statement: str,
) -> ConsultingReport:
    """Create a new consulting report record."""
    # Verify project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise ValueError(f"Project {project_id} not found")

    report = ConsultingReport(
        project_id=project_id,
        goal_statement=goal_statement,
        status=ReportStatus.QUEUED,
    )
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


async def get_report(db: AsyncSession, report_id: uuid.UUID) -> ConsultingReport | None:
    result = await db.execute(
        select(ConsultingReport).where(ConsultingReport.id == report_id)
    )
    return result.scalar_one_or_none()


async def list_reports(db: AsyncSession, project_id: uuid.UUID):
    result = await db.execute(
        select(ConsultingReport)
        .where(ConsultingReport.project_id == project_id)
        .order_by(ConsultingReport.created_at.desc())
    )
    return result.scalars().all()
