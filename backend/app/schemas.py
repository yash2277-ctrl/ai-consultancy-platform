"""
Pydantic v2 schemas for request/response validation.
"""

from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from enum import Enum


# ── Auth ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    company: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    company: Optional[str]
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ── Project ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    industry: Optional[str] = None


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    industry: Optional[str]
    owner_id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectDetail(ProjectResponse):
    file_count: int = 0
    report_count: int = 0


# ── File Upload ──────────────────────────────────────────────────────────────

class FileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    original_name: str
    file_type: str
    file_size: int
    status: str
    chunk_count: int
    project_id: UUID
    uploaded_at: datetime


# ── Consulting ───────────────────────────────────────────────────────────────

class ConsultRequest(BaseModel):
    project_id: UUID
    goal_statement: str = Field(
        min_length=10,
        max_length=2000,
        description="Describe the business objective or question for the AI consultants."
    )


class ReportStatusEnum(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    goal_statement: str
    status: str
    financial_analysis: Optional[Any] = None
    market_strategy: Optional[Any] = None
    executive_summary: Optional[Any] = None
    consolidated_report: Optional[Any] = None
    tokens_used: int
    processing_time_seconds: float
    created_at: datetime
    completed_at: Optional[datetime] = None


class ReportSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    goal_statement: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


# ── Agent Structured Output ──────────────────────────────────────────────────

class FinancialInsight(BaseModel):
    revenue_analysis: Optional[str] = None
    cost_optimization: Optional[list[str]] = None
    risk_factors: Optional[list[str]] = None
    financial_health_score: Optional[float] = None
    recommendations: list[str] = []
    key_metrics: Optional[dict[str, Any]] = None


class MarketInsight(BaseModel):
    market_overview: Optional[str] = None
    competitive_landscape: Optional[list[str]] = None
    growth_opportunities: Optional[list[str]] = None
    threats: Optional[list[str]] = None
    target_segments: Optional[list[str]] = None
    recommendations: list[str] = []


class ExecutiveSummary(BaseModel):
    situation_assessment: str = ""
    key_findings: list[str] = []
    strategic_recommendations: list[str] = []
    priority_actions: list[dict[str, Any]] = []
    risk_matrix: Optional[list[dict[str, Any]]] = None
    timeline: Optional[list[dict[str, str]]] = None
    confidence_score: float = Field(default=0.75, ge=0.0, le=1.0)
