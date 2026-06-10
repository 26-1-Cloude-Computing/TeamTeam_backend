"""Notice schemas."""

from pydantic import BaseModel
from datetime import datetime


class NoticeCreateRequest(BaseModel):
    title: str
    content: str | None = None


class NoticePinRequest(BaseModel):
    is_pinned: bool


class NoticeResponse(BaseModel):
    id: int
    team_id: int
    author_id: int
    author_name: str | None = None
    title: str
    content: str | None = None
    is_leader_notice: bool
    created_at: datetime | None = None
