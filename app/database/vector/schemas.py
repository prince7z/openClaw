"""Pydantic schemas for Qdrant Semantic and Episodic Memories."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field
from typing import List


class SemanticMemory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # user_profile | preference | project | knowledge | relationship
    category: str  # identity | preferences | family | education | career | projects | skills | location | devices | habits | goals | knowledge | relationship | contacts | custom
    text: str
    importance: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0
    source_chat: str
    tags: List[str] = Field(default_factory=list)


class EpisodicMemory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # debug | discussion | decision | meeting | achievement | failure | experiment
    summary: str
    importance: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    last_accessed: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    access_count: int = 0
    source_chat: str
    tags: List[str] = Field(default_factory=list)
