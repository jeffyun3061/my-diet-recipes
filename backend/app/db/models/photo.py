# app/db/models/photo.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class PhotoDoc(BaseModel):
    anon_id: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    data: bytes
    created_at: datetime = Field(default_factory=datetime.utcnow)