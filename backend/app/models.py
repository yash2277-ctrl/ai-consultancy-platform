"""
SQLAlchemy ORM models â€” Users, Files, Projects, ConsultingReports.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Text, DateTime, Integer, ForeignKey, Float, JSON, Boolean, Enum as SAEnum, Uuid
)
from sqlalchemy.orm import relationship
from app.database import Base
import enum


# â”€â”€ Enums â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class FileStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ReportStatus(str, enum.Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


# â”€â”€ User â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class User(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    role = Column(String(50), default="user")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # relationships
    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")


# â”€â”€ Project â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class Project(Base):
    __tablename__ = "projects"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    industry = Column(String(100), nullable=True)
    owner_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User", back_populates="projects")
    files = relationship("UploadedFile", back_populates="project", cascade="all, delete-orphan")
    reports = relationship("ConsultingReport", back_populates="project", cascade="all, delete-orphan")


# â”€â”€ Uploaded File â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)          # pdf, docx, csv
    file_size = Column(Integer, nullable=False)              # bytes
    file_path = Column(String(500), nullable=False)
    status = Column(SAEnum(FileStatus), default=FileStatus.PENDING)
    chunk_count = Column(Integer, default=0)
    project_id = Column(Uuid, ForeignKey("projects.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="files")


# â”€â”€ Consulting Report â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

class ConsultingReport(Base):
    __tablename__ = "consulting_reports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    project_id = Column(Uuid, ForeignKey("projects.id"), nullable=False)
    goal_statement = Column(Text, nullable=False)
    status = Column(SAEnum(ReportStatus), default=ReportStatus.QUEUED)

    # Structured JSON results from each agent
    financial_analysis = Column(JSON, nullable=True)
    market_strategy = Column(JSON, nullable=True)
    executive_summary = Column(JSON, nullable=True)
    consolidated_report = Column(JSON, nullable=True)

    tokens_used = Column(Integer, default=0)
    processing_time_seconds = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="reports")
