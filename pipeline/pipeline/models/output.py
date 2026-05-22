import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from pipeline.database import Base


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class Output(Base):
    __tablename__ = "outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    video_path = Column(String(1024), nullable=False)
    video_duration_s = Column(Float, nullable=False)
    video_width = Column(Integer, nullable=False)
    video_height = Column(Integer, nullable=False)
    video_size_bytes = Column(BigInteger, nullable=False)
    doc_path = Column(String(1024), nullable=True)
    screenshot_paths_json = Column(JSON, nullable=False, default=list)
    thumbnail_path = Column(String(1024), nullable=True)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class OutputRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    created_at: datetime
    video_path: str
    video_duration_s: float
    video_width: int
    video_height: int
    video_size_bytes: int
    doc_path: Optional[str] = None
    screenshot_paths_json: Any
    thumbnail_path: Optional[str] = None
