"""
ProcessManager — Orchestrates the full consulting pipeline:
  1. Retrieve relevant context from Vector Store
  2. Run FinancialAnalyst + MarketStrategist in parallel
  3. Pass both results to ExecutivePartner
  4. Persist the structured report to the database
"""

import asyncio
import logging
import time
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import ConsultingReport, ReportStatus, Project
from app.rag.vector_store import VectorStore
from app.agents.agents import (
    run_financial_analyst,
    run_market_strategist,
    run_executive_partner,
)

logger = logging.getLogger(__name__)


class ProcessManager:
    """Coordinates the multi-agent consulting workflow."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_consultation(self, report_id: UUID) -> None:
        """
        Full pipeline — called as a background task.
        Updates the report row in-place as it progresses.
        """
        start = time.time()

        # ── Load report ──────────────────────────────────────────────────
        result = await self.db.execute(
            select(ConsultingReport).where(ConsultingReport.id == report_id)
        )
        report = result.scalar_one_or_none()
        if not report:
            logger.error(f"Report {report_id} not found")
            return

        try:
            report.status = ReportStatus.IN_PROGRESS
            await self.db.commit()

            project_id = str(report.project_id)
            goal = report.goal_statement

            # ── 1. Retrieve RAG context ──────────────────────────────────
            logger.info(f"Retrieving context for project {project_id}")
            try:
                search_results = await VectorStore.search(
                    query=goal,
                    project_id=project_id,
                    n_results=12,
                )
            except Exception as exc:
                logger.warning(f"RAG retrieval failed: {exc}")
                search_results = []

            context = "\n\n---\n\n".join(
                r["content"] for r in search_results
            ) if search_results else "No uploaded documents found for this project. Provide analysis based on the goal statement using your expert knowledge and industry benchmarks."

            # ── 2. Run Financial + Market agents in parallel ─────────────
            logger.info("Running Financial & Market agents in parallel")
            financial_task = asyncio.create_task(
                run_financial_analyst(context, goal)
            )
            market_task = asyncio.create_task(
                run_market_strategist(context, goal)
            )

            # Use return_exceptions to prevent one failure from killing both
            results = await asyncio.gather(
                financial_task, market_task, return_exceptions=True
            )

            financial_result = results[0] if not isinstance(results[0], Exception) else {
                "raw_analysis": f"Financial analysis failed: {results[0]}",
                "recommendations": ["Re-run analysis with more complete data"],
            }
            market_result = results[1] if not isinstance(results[1], Exception) else {
                "raw_analysis": f"Market analysis failed: {results[1]}",
                "recommendations": ["Re-run analysis with more complete data"],
            }

            report.financial_analysis = financial_result
            report.market_strategy = market_result
            await self.db.commit()

            # ── 3. Run Executive Partner (synthesis) ─────────────────────
            logger.info("Running ExecutivePartner synthesis agent")
            try:
                executive_result = await run_executive_partner(
                    context=context,
                    goal_statement=goal,
                    financial_analysis=financial_result,
                    market_analysis=market_result,
                )
            except Exception as exc:
                logger.exception(f"Executive agent failed: {exc}")
                executive_result = {
                    "situation_assessment": "Executive synthesis encountered an error. The financial and market analyses above are still valid.",
                    "key_findings": ["Review the financial and market sections for individual insights."],
                    "strategic_recommendations": ["Re-run the consultation for a synthesised executive view."],
                    "confidence_score": 0.3,
                }

            # ── 4. Build consolidated report ─────────────────────────────
            consolidated = {
                "goal_statement": goal,
                "data_sources_used": len(search_results),
                "financial_analysis": financial_result,
                "market_strategy": market_result,
                "executive_summary": executive_result,
                "generated_at": datetime.utcnow().isoformat(),
            }

            report.executive_summary = executive_result
            report.consolidated_report = consolidated
            report.status = ReportStatus.COMPLETED
            report.processing_time_seconds = round(time.time() - start, 2)
            report.completed_at = datetime.utcnow()
            await self.db.commit()

            logger.info(
                f"Report {report_id} completed in {report.processing_time_seconds}s"
            )

        except Exception as exc:
            logger.exception(f"Report {report_id} failed: {exc}")
            try:
                report.status = ReportStatus.FAILED
                report.consolidated_report = {"error": str(exc)}
                report.processing_time_seconds = round(time.time() - start, 2)
                await self.db.commit()
            except Exception as db_exc:
                logger.exception(f"Could not update failed status for report {report_id}: {db_exc}")
