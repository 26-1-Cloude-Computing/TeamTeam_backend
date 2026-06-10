"""Authentication routes: signup and login."""

from fastapi import APIRouter, HTTPException, status , Response, Request, Cookie, Header
from app.core.supabase import get_supabase
from app.core.security import( 
                              hash_password, verify_password, create_access_token
                              ,create_refresh_token, decode_refresh_token)
from app.schemas.auth import SignUpRequest, LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/signup", response_model=TokenResponse,
             status_code=status.HTTP_201_CREATED)
async def signup(body: SignUpRequest, response: Response):
    """회원가입 — 이메일, 비밀번호, 이름 등으로 계정 생성 후 토큰 발급."""
    db = get_supabase()

    # Check if email already exists
    existing = db.table("user").select("id").eq("email", body.email).execute()
    if existing.data:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 가입된 이메일입니다.",
        )

    # Create user
    hashed = hash_password(body.password)
    user_data = {
        "email": body.email,
        "password": hashed,
        "name": body.name,
        "department": body.department,
        "student_id": body.student_id,
    }
    result = db.table("user").insert(user_data).execute()

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원가입에 실패했습니다.",
        )

    user = result.data[0]
    token = create_access_token({"user_id": user["id"], "email": user["email"]})
    refresh_token = create_refresh_token({"user_id": user["id"]})

    try:
        db.table("refresh_tokens").insert({"user_id": user["id"], "token": refresh_token}).execute()
    except Exception:
        pass

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 3,
    )

    return TokenResponse(
        access_token=token,
        user_id=user["id"],
        name=user["name"],
        refresh_token=refresh_token,
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, response: Response):
    """로그인 — 이메일과 비밀번호로 인증 후 토큰 발급."""
    db = get_supabase()

    result = db.table("user").select("*").eq("email", body.email).execute()
    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    user = result.data[0]
    if not verify_password(body.password, user["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    access_token = create_access_token({"user_id": user["id"]})
    refresh_token = create_refresh_token({"user_id": user["id"]})

    try:
        db.table("refresh_tokens").insert({"user_id": user["id"], "token": refresh_token}).execute()
    except Exception:
        pass

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 3,
    )

    return TokenResponse(access_token=access_token, user_id=user["id"], name=user["name"], refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str = Cookie(None),
    x_refresh_token: str | None = Header(None),
):
    # 크로스 도메인(S3 http) 환경에서는 쿠키가 전송되지 않으므로
    # X-Refresh-Token 헤더(프론트 localStorage 값)도 함께 허용한다.
    token = refresh_token or x_refresh_token
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh Token이 없습니다.")
    payload = decode_refresh_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 Refresh Token입니다.")
    db = get_supabase()
    try:
        stored = db.table("refresh_tokens").select("id").eq("token", token).execute()
        if not stored.data:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="만료되거나 로그아웃된 토큰입니다.")
    except HTTPException:
        raise
    except Exception:
        pass
    user_id = payload["user_id"]
    user = db.table("user").select("id, name").eq("id", user_id).single().execute()
    new_access_token = create_access_token({"user_id": user_id})
    # 동일 refresh_token을 다시 내려 프론트가 계속 보관하게 한다.
    return TokenResponse(access_token=new_access_token, user_id=user_id, name=user.data["name"], refresh_token=token)


@router.post("/logout")
async def logout(response: Response, refresh_token: str = Cookie(None), x_refresh_token: str | None = Header(None)):
    token = refresh_token or x_refresh_token
    if token:
        db = get_supabase()
        try:
            db.table("refresh_tokens").delete().eq("token", token).execute()
        except Exception:
            pass
    response.delete_cookie("refresh_token")
    return {"message": "로그아웃되었습니다."}