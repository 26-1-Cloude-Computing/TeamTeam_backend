"""AI Schedule schemas."""

from pydantic import BaseModel
from datetime import date, datetime


class AIScheduleRequest(BaseModel):
    """Request to create an AI schedule session."""
    goal: str  # e.g., "mid 발표"
    deadline: date
    tasks: list[str]  # list of task descriptions, e.g., ["API 명세서 마무리하기", "ERD 완료하기"]


class AIScheduleTaskItem(BaseModel):
    """A single recommended task from AI."""
    id: int | None = None
    task_name: str
    start_date: date | None = None
    due_date: date | None = None


class AIScheduleTaskUpdate(BaseModel):
    """Update a single task's dates."""
    task_name: str | None = None
    start_date: date | None = None
    due_date: date | None = None


class AISessionResponse(BaseModel):
    id: int
    team_id: int
    goal: str
    deadline: date
    status: str
    tasks: list[AIScheduleTaskItem] = []
    created_at: datetime | None = None


class AIConfirmRequest(BaseModel):
    """Request to confirm (and optionally modify) AI-recommended tasks."""
    tasks: list[AIScheduleTaskItem]


# ── 2단계 워크플로우(분석·되묻기 → 추천·할당 → 확정) ──

class AIAnalyzeRequest(BaseModel):
    goal: str
    deadline: date
    tasks: list[str]


class AIAnalyzeResponse(BaseModel):
    suggested_tasks: list[str] = []   # 누락 가능성 있는 추가 할 일 제안
    questions: list[str] = []         # 팀장에게 되묻는 확인 질문


class AIPlanRequest(BaseModel):
    goal: str
    deadline: date
    tasks: list[str]                  # 되묻기 후 확정된 최종 할 일 목록


class AIAssignment(BaseModel):
    task_name: str
    due_date: date | None = None
    assignee_id: int | None = None
    assignee_name: str | None = None


class AIPlanResponse(BaseModel):
    assignments: list[AIAssignment] = []


class AIScheduleConfirmRequest(BaseModel):
    assignments: list[AIAssignment]
    create_meetings: bool = False     # 일정(회의)으로도 등록할지
