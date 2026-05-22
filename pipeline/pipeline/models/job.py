import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from pipeline.database import Base


# ---------------------------------------------------------------------------
# ORM Model
# ---------------------------------------------------------------------------

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    status = Column(String(64), nullable=False, default="pending")
    progress_pct = Column(Integer, default=0, nullable=False)
    input_file_path = Column(String(1024), nullable=False)
    input_duration_s = Column(Float, nullable=True)
    input_width = Column(Integer, nullable=True)
    input_height = Column(Integer, nullable=True)
    options_json = Column(JSON, nullable=True)
    error_message = Column(String(2048), nullable=True)
    output_id = Column(UUID(as_uuid=True), nullable=True)


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class JobStatus(str, Enum):
    pending = "pending"
    ingesting = "ingesting"
    detecting_scenes = "detecting_scenes"
    running_ocr = "running_ocr"
    understanding_narrative = "understanding_narrative"
    generating_script = "generating_script"
    editing = "editing"
    rendering = "rendering"
    generating_docs = "generating_docs"
    complete = "complete"
    failed = "failed"


class JobOptions(BaseModel):
    target_duration_s: int = 120
    output_style: str = "product_demo"  # product_demo | tutorial | walkthrough
    include_subtitles: bool = True
    include_docs: bool = True
    use_elevenlabs: bool = False


class JobCreate(BaseModel):
    upload_id: str
    file_path: str
    options: JobOptions = JobOptions()


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    status: str
    progress_pct: int
    input_file_path: str
    input_duration_s: Optional[float] = None
    input_width: Optional[int] = None
    input_height: Optional[int] = None
    options_json: Optional[Any] = None
    error_message: Optional[str] = None
    output_id: Optional[uuid.UUID] = None
