"""Meeting schemas."""

from pydantic import BaseModel
from datetime import datetime


class MeetingCreate(BaseModel):
    date: str
    title: str
    description: str | None = ""
    time: str | None = "14:00"


class MeetingResponse(BaseModel):
    id: int
    team_id: int
    date: str
    time: str | None = None
    title: str
    description: str | None = None
    created_at: datetime | None = None
