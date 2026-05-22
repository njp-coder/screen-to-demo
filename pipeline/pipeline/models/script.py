from __future__ import annotations
import uuid
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from pipeline.database import Base


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class Script(Base):
    __tablename__ = "scripts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    app_name = Column(String(256), nullable=True)
    app_description = Column(Text, nullable=False, default="")
    user_journey_summary = Column(Text, nullable=False, default="")
    chapters_json = Column(JSON, nullable=False, default=list)
    full_narration_text = Column(Text, nullable=False, default="")
    estimated_read_duration_s = Column(Float, default=0.0, nullable=False)
    subtitle_segments_json = Column(JSON, nullable=False, default=list)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class Chapter(BaseModel):
    index: int
    title: str
    start_scene_index: int
    end_scene_index: int
    narration_text: str
    feature_highlights: list[str] = []


class SubtitleSegment(BaseModel):
    start_s: float
    end_s: float
    text: str


class ScriptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    app_name: Optional[str] = None
    app_description: str
    user_journey_summary: str
    chapters_json: Any
    full_narration_text: str
    estimated_read_duration_s: float
    subtitle_segments_json: Any


class ScriptUpdate(BaseModel):
    app_name: Optional[str] = None
    app_description: Optional[str] = None
    user_journey_summary: Optional[str] = None
    chapters_json: Optional[Any] = None
    full_narration_text: Optional[str] = None
    estimated_read_duration_s: Optional[float] = None
    subtitle_segments_json: Optional[Any] = None
