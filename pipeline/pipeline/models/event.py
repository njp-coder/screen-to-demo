import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID

from pipeline.database import Base


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class Event(Base):
    __tablename__ = "events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id = Column(UUID(as_uuid=True), ForeignKey("scenes.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp_s = Column(Float, nullable=False)
    type = Column(String(32), nullable=False)  # click/scroll/type/nav/hover/resize
    position_x = Column(Integer, nullable=True)
    position_y = Column(Integer, nullable=True)
    target_label = Column(String(512), nullable=True)
    value = Column(String(2048), nullable=True)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    scene_id: uuid.UUID
    timestamp_s: float
    type: str
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    target_label: Optional[str] = None
    value: Optional[str] = None
