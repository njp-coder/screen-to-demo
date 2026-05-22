from __future__ import annotations
import uuid
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Boolean, Column, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID

from pipeline.database import Base


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class Scene(Base):
    __tablename__ = "scenes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    index = Column(Integer, nullable=False)
    start_time_s = Column(Float, nullable=False)
    end_time_s = Column(Float, nullable=False)
    duration_s = Column(Float, nullable=False)
    transition_type = Column(String(32), nullable=False, default="cut")  # cut/fade/content_change/pause
    key_frame_path = Column(String(1024), nullable=True)
    is_dead_time = Column(Boolean, default=False, nullable=False)
    is_repetitive = Column(Boolean, default=False, nullable=False)
    importance_score = Column(Float, default=0.5, nullable=False)
    ocr_text = Column(Text, nullable=True)
    ui_elements_json = Column(JSON, nullable=True)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class UIElement(BaseModel):
    type: str  # button / input / link / text / image / nav / modal / other
    label: Optional[str] = None
    bounding_box: Optional[list[int]] = None  # [x, y, w, h]
    confidence: float = 1.0


class SceneRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    index: int
    start_time_s: float
    end_time_s: float
    duration_s: float
    transition_type: str
    key_frame_path: Optional[str] = None
    is_dead_time: bool
    is_repetitive: bool
    importance_score: float
    ocr_text: Optional[str] = None
    ui_elements_json: Optional[Any] = None
