"""Reference room routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.dependencies import get_current_user
from app.core.supabase import get_supabase
from app.schemas.reference import ReferenceCreateRequest, ReferenceResponse

router = APIRouter(tags=["References"])

# Supabase Storage public 버킷 이름 (사전 생성 필요)
REFERENCE_BUCKET = "references"
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20MB


def _verify_member(db, team_id: int, user_id: int):
    r = db.table("team_member").select("id").eq("team_id", team_id).eq("user_id", user_id).execute()
    if not r.data:
        raise HTTPException(status_code=403, detail="해당 팀의 멤버가 아닙니다.")


@router.get("/api/teams/{team_id}/references", response_model=list[ReferenceResponse])
async def list_references(team_id: int, current_user: dict = Depends(get_current_user)):
    db = get_supabase()
    _verify_member(db, team_id, current_user["id"])
    refs = db.table("reference_room").select("*, uploader:uploader_id(name)").eq("team_id", team_id).order("created_at", desc=True).execute()
    result = []
    for r in refs.data or []:
        uname = r.get("uploader", {}).get("name") if r.get("uploader") else None
        result.append(ReferenceResponse(id=r["id"], team_id=r["team_id"], uploader_id=r["uploader_id"], uploader_name=uname, file_name=r["file_name"], file_url=r["file_url"], created_at=r.get("created_at")))
    return result


@router.post("/api/teams/{team_id}/references", response_model=ReferenceResponse, status_code=201)
async def upload_reference(team_id: int, body: ReferenceCreateRequest, current_user: dict = Depends(get_current_user)):
    db = get_supabase()
    _verify_member(db, team_id, current_user["id"])
    ref_data = {"team_id": team_id, "uploader_id": current_user["id"], "file_name": body.file_name, "file_url": body.file_url}
    result = db.table("reference_room").insert(ref_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="자료 업로드에 실패했습니다.")
    r = result.data[0]
    return ReferenceResponse(id=r["id"], team_id=r["team_id"], uploader_id=r["uploader_id"], uploader_name=current_user["name"], file_name=r["file_name"], file_url=r["file_url"], created_at=r.get("created_at"))


@router.post("/api/teams/{team_id}/references/upload", response_model=ReferenceResponse, status_code=201)
async def upload_reference_file(
    team_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
):
    """파일 직접 업로드 — Supabase Storage에 저장 후 공개 URL을 자료로 등록한다."""
    db = get_supabase()
    _verify_member(db, team_id, current_user["id"])

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="빈 파일은 업로드할 수 없습니다.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="20MB 이하의 파일만 업로드할 수 있습니다.")

    original_name = file.filename or "file"
    storage_path = f"team_{team_id}/{uuid.uuid4().hex}_{original_name}"

    try:
        db.storage.from_(REFERENCE_BUCKET).upload(
            storage_path,
            contents,
            {"content-type": file.content_type or "application/octet-stream"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파일 저장에 실패했습니다: {e}")

    public_url = db.storage.from_(REFERENCE_BUCKET).get_public_url(storage_path)

    ref_data = {
        "team_id": team_id,
        "uploader_id": current_user["id"],
        "file_name": original_name,
        "file_url": public_url,
    }
    result = db.table("reference_room").insert(ref_data).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="자료 등록에 실패했습니다.")
    r = result.data[0]
    return ReferenceResponse(
        id=r["id"], team_id=r["team_id"], uploader_id=r["uploader_id"],
        uploader_name=current_user["name"], file_name=r["file_name"],
        file_url=r["file_url"], created_at=r.get("created_at"),
    )


@router.delete("/api/references/{ref_id}", response_model=dict)
async def delete_reference(ref_id: int, current_user: dict = Depends(get_current_user)):
    db = get_supabase()
    ref = db.table("reference_room").select("uploader_id").eq("id", ref_id).single().execute()
    if not ref.data:
        raise HTTPException(status_code=404, detail="자료를 찾을 수 없습니다.")
    if ref.data["uploader_id"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="본인이 업로드한 자료만 삭제할 수 있습니다.")
    db.table("reference_room").delete().eq("id", ref_id).execute()
    return {"message": "자료가 삭제되었습니다."}
