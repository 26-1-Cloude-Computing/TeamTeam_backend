"""Meeting (회의 일정) routes — team-scoped, persisted in the `meeting` table."""

from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user
from app.core.supabase import get_supabase
from app.schemas.meeting import MeetingCreate, MeetingResponse

router = APIRouter(tags=["Meetings"])


def _verify_member(db, team_id: int, user_id: int):
    r = db.table("team_member").select("id").eq("team_id", team_id).eq("user_id", user_id).execute()
    if not r.data:
        raise HTTPException(status_code=403, detail="해당 팀의 멤버가 아닙니다.")


@router.get("/api/teams/{team_id}/meetings", response_model=list[MeetingResponse])
async def list_meetings(team_id: int, current_user: dict = Depends(get_current_user)):
    db = get_supabase()
    _verify_member(db, team_id, current_user["id"])
    rows = (
        db.table("meeting")
        .select("*")
        .eq("team_id", team_id)
        .order("date")
        .execute()
    )
    return [MeetingResponse(**r) for r in rows.data or []]


@router.post("/api/teams/{team_id}/meetings", response_model=MeetingResponse, status_code=201)
async def create_meeting(team_id: int, body: MeetingCreate, current_user: dict = Depends(get_current_user)):
    db = get_supabase()
    _verify_member(db, team_id, current_user["id"])
    data = {
        "team_id": team_id,
        "date": body.date,
        "time": body.time or "14:00",
        "title": body.title,
        "description": body.description or "",
    }
    result = db.table("meeting").insert(data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="회의 일정 생성에 실패했습니다.")
    return MeetingResponse(**result.data[0])


@router.delete("/api/meetings/{meeting_id}", response_model=dict)
async def delete_meeting(meeting_id: int, current_user: dict = Depends(get_current_user)):
    """회의 일정 삭제 — 같은 팀 멤버면 삭제 가능."""
    db = get_supabase()

    meeting = db.table("meeting").select("team_id").eq("id", meeting_id).single().execute()
    if not meeting.data:
        raise HTTPException(status_code=404, detail="회의 일정을 찾을 수 없습니다.")

    _verify_member(db, meeting.data["team_id"], current_user["id"])

    db.table("meeting").delete().eq("id", meeting_id).execute()

    return {"message": "회의 일정이 삭제되었습니다."}
