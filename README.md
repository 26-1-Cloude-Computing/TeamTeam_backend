# TeamTeam Backend

> 26-1 클라우드 컴퓨팅 수업 프로젝트 백엔드 레포입니다.

## 기술스택

- **Framework**: Python 3.12 / FastAPI
- **Database**: Supabase (PostgreSQL)
- **Authentication**: JWT (HS256) + bcrypt 비밀번호 해싱 — Access Token + Refresh Token(httpOnly Cookie)
- **AI**: Gemini API (gemini-2.0-flash) — 일정 추천 & 채팅 요약
- **Monitoring**: Prometheus + 구조화 JSON 로깅
- **Secrets**: AWS Secrets Manager (앱 시작 시 boto3로 로드, EC2 IAM 역할 사용)
- **Deployment**: Docker + Docker Compose → AWS EC2

## 프로젝트 구조

```
app/
├── main.py              # FastAPI 앱, 미들웨어, CORS 설정
├── dependencies.py      # 인증 dependency (get_current_user)
├── core/
│   ├── config.py        # 환경변수 설정 (Secrets Manager 우선, .env 폴백)
│   ├── supabase.py      # Supabase 클라이언트 싱글턴 (service_role key 우선)
│   ├── security.py      # bcrypt 해싱 + JWT(access/refresh) 발급·검증
│   └── logging.py       # 구조화 JSON 로깅 미들웨어
├── routers/
│   ├── auth.py          # 회원가입/로그인/토큰 재발급/로그아웃
│   ├── users.py         # GET/PATCH /api/users/me
│   ├── teams.py         # 팀 생성/참여/목록/대시보드/상태변경
│   ├── notices.py       # 공지사항 CRUD
│   ├── tasks.py         # 업무 관리
│   ├── ai_schedule.py   # AI 일정 추천 세션
│   ├── references.py    # 자료실 (링크 등록 + 파일 업로드/Storage)
│   ├── chat.py          # 채팅방 & 메시지 & AI 프롬프트
│   ├── evaluations.py   # 상호평가
│   └── meeting.py       # 회의 일정 (meeting 테이블)
└── schemas/             # Pydantic 요청/응답 모델
```

## 로컬 실행

```bash
# 가상환경 생성 & 활성화
python3 -m venv .venv
source .venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행 (개발 모드)
uvicorn app.main:app --reload --port 8000
```

## Docker 실행

```bash
docker compose up --build
```

## 환경변수 / 시크릿

`config.py`는 **앱 시작 시 AWS Secrets Manager(`us-east-1`)에서 아래 3개 시크릿을 boto3로 읽어
모든 설정을 구성**합니다. 따라서 로컬 실행에도 Secrets Manager 접근 권한(AWS 자격증명)이 필요하며,
접근이 불가하면 앱이 기동되지 않습니다. 별도의 `.env` 폴백 로직은 없습니다.

| Secrets Manager 시크릿 | 포함 키 |
|------------------------|---------|
| `teamapp/prod/jwt` | `JWT_SECRET`, `REFRESH_SECRET` |
| `teamapp/prod/ai`  | `GEMINI_API_KEY` |
| `teamapp/prod/db`  | `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `CORS_ORIGINS` |

> 동일한 이름의 **환경변수가 설정되어 있으면 Secrets Manager 값보다 우선 적용**됩니다
> (pydantic-settings 기본 동작). `docker-compose.yml`이 `env_file: .env`로 컨테이너에
> 주입하는 값들이 여기에 해당하므로, `.env`와 Secrets Manager 값이 다르면 `.env`가 이깁니다.

| 변수명 | 설명 | 필수 |
|--------|------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL | ✅ |
| `SUPABASE_KEY` | Supabase anon key | ✅ |
| `SUPABASE_SERVICE_KEY` | Supabase service_role(secret) key — 있으면 RLS 우회용으로 우선 사용 | ❌ |
| `GEMINI_API_KEY` | Gemini API 키 (AI 기능용) | ❌ |
| `JWT_SECRET` | Access Token 서명 키 | ✅ |
| `REFRESH_SECRET` | Refresh Token 서명 키 | ✅ |
| `CORS_ORIGINS` | 허용 오리진 (쉼표 구분, 없으면 `*`) | ❌ |

> **참고**: JWT 인증은 Supabase의 `refresh_tokens` 테이블을 사용합니다. 현재 `auth.py`는
> 이 테이블이 없어도 로그인은 되도록 `try/except`로 방어하고 있으나, **토큰 재발급(`/refresh`)과
> 로그아웃(`/logout`)이 정상 동작하려면 테이블 생성이 필요**합니다 (`docs/supabase_schema.sql` 참고).

## API 엔드포인트

### 인증 (Auth)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/auth/signup` | 회원가입 (bcrypt 해싱) |
| POST | `/api/auth/login` | 로그인 → Access Token 반환 + Refresh Token Cookie 발급 |
| POST | `/api/auth/refresh` | Refresh Token Cookie로 Access Token 재발급 |
| POST | `/api/auth/logout` | 로그아웃 + Refresh Token Cookie 삭제 |

### 사용자 (Users)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/users/me` | 마이페이지 (평가 통계 포함) |
| PATCH | `/api/users/me` | 내 정보 수정 |

### 팀 (Teams)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/teams` | 팀 생성 |
| POST | `/api/teams/join` | 초대 코드로 팀 참여 |
| GET | `/api/teams` | 내 팀 목록 |
| GET | `/api/teams/{teamId}` | 팀 대시보드 |
| PATCH | `/api/teams/{teamId}/status` | 상태 변경 (팀장) |

### 공지사항 (Notices)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/teams/{teamId}/notices` | 공지 목록 |
| POST | `/api/teams/{teamId}/notices` | 공지 작성 |
| GET | `/api/notices/{noticeId}` | 공지 상세 |

### 업무 (Tasks)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/teams/{teamId}/tasks` | 업무 목록 (?mine_only=true) |
| POST | `/api/teams/{teamId}/tasks` | 업무 추가 |
| PATCH | `/api/tasks/{taskId}` | 업무 수정 |

### AI 스케줄링
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/teams/{teamId}/ai-sessions` | AI 추천 요청 (팀장) |
| GET | `/api/ai-sessions/{sessionId}` | 추천 일정 확인 |
| POST | `/api/ai-sessions/{sessionId}/confirm` | 일정 확정 |

### 자료실 (References)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/teams/{teamId}/references` | 자료 목록 |
| POST | `/api/teams/{teamId}/references` | 자료 등록 (file_url 링크) |
| POST | `/api/teams/{teamId}/references/upload` | 파일 직접 업로드 → Supabase Storage(`references` 버킷, ≤20MB) |
| DELETE | `/api/references/{refId}` | 자료 삭제 |

### 회의 일정 (Meetings)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/api/teams/{teamId}/meetings` | 회의 일정 목록 |
| POST | `/api/teams/{teamId}/meetings` | 회의 일정 생성 (meeting 테이블 영속) |

### 채팅 (Chat)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/teams/{teamId}/chat-rooms` | 채팅방 생성 |
| GET | `/api/teams/{teamId}/chat-rooms` | 채팅방 목록 |
| GET | `/api/chat-rooms/{roomId}/messages` | 메시지 조회 |
| POST | `/api/chat-rooms/{roomId}/messages` | 메시지 전송 |
| POST | `/api/chat-rooms/{roomId}/ai-prompt` | AI 요약 생성 |

### 상호평가 (Evaluations)
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| POST | `/api/teams/{teamId}/evaluations` | 평가 제출 |
| GET | `/api/teams/{teamId}/members/eval-status` | 평가 현황 |

### 기타
| 메서드 | 엔드포인트 | 설명 |
|--------|-----------|------|
| GET | `/` | 헬스 체크 |
| GET | `/health` | 헬스 체크 |
| GET | `/metrics` | Prometheus 메트릭 |
| GET | `/docs` | Swagger UI |
| GET | `/redoc` | ReDoc |
