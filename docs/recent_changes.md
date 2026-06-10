# 최근 변경 이력 (Recent Changes)

---

## [feat] AI 일정 2단계 워크플로우 + 담당자 배정 + 다가오는 일정 + 업무 담당자 재배정 — 배포 완료 (2026-06-11)

- **백엔드**: 로컬 빌드 → ECR push → SSM 배포(운영 인스턴스 `i-05ccd62f09320b9cb`). ALB `/health` 200, 신규 라우트 403(auth) 확인.
- **프론트**: 로컬 빌드 → `aws s3 sync`(S3 배포 완료).

### 1. AI 일정 — 2단계 워크플로우(분석·되묻기 → 추천·할당 → 확정) + 인원별 할당

기존: "할 일 → 마감일만" 추천. 담당자/누락점검 없음. → 재설계.

| 파일 | 변경 내용 |
|------|----------|
| `app/routers/ai_schedule.py` | 신규 3 엔드포인트: `POST /api/teams/{id}/ai-schedule/analyze`(누락 할 일·확인 질문), `…/plan`(마감일+담당자 배정), `…/confirm`(담당자 포함 task 생성 + 선택 시 meeting 등록). 모두 팀장 전용. Gemini 실패 시 서버 폴백(균등분배+라운드로빈). 모델 `gemini-2.5-flash`. 구 `ai-sessions` 흐름은 유지(미사용). |
| `app/schemas/ai_schedule.py` | `AIAnalyzeRequest/Response`, `AIPlanRequest/Response`, `AIAssignment`, `AIScheduleConfirmRequest` 추가 |
| 프론트 `pages/Schedule.tsx` | 3단계 모달(점검·되묻기 → 마감일·담당자 표 → 확정). 확정 시 tasks·dashboard·meetings 캐시 무효화 후 재조회. 입력값은 기각해도 유지. |

### 2. 업무 담당자 재배정 (토글식)

| 파일 | 변경 내용 |
|------|----------|
| `app/schemas/task.py` | `TaskUpdateRequest`에 `assignee_id` 추가 |
| `app/routers/tasks.py` | `update_task` 권한 완화: 본인 한정 → **팀 멤버면 수정 가능**. 재배정 시 새 담당자가 같은 팀 멤버인지 검증 |
| 프론트 `pages/Tasks.tsx` | 담당자 배지 클릭 → 팀원 드롭다운 → PATCH(낙관적). 상태도 동일 드롭다운. 담당자별 필터 추가 |

### 3. 다가오는 일정 (일정 페이지)

- 프론트만. 회의 + 업무 마감(task.due_date) + 프로젝트 마감(team.deadline)을 합쳐 **다가오는 순 Top 5 + D-day** 카드 + 캘린더 종류별 색 점 + 범례 + "전체 보기".

### 4. 체감 대기시간(SWR) 개선 — 프론트 전반

- `src/app/store/dataCache.ts`(SWR + sessionStorage 영속 + `swrLoad`/`prefetch`), `src/app/store/resources.ts`(리소스별 fetcher 단일화), `src/app/components/Skeleton.tsx`(스켈레톤). `DashboardLayout`에서 팀 진입 시 사이드바 탭 프리페치.

---

## [fix] 자동 로그아웃·Gemini·공지고정·평가 DB·다수 데모 UX — 배포 완료 (2026-06-10)

### 1. 자동 로그아웃(~15분) — 크로스도메인 refresh 토큰
- 원인: access 15분 만료 + refresh가 httpOnly 쿠키뿐인데 http S3 ↔ ALB 크로스도메인이라 쿠키 미전송 → refresh 401.
- 해결: `app/routers/auth.py` login·signup이 `refresh_token`을 **body**로도 반환, `/refresh`·`/logout`이 **`X-Refresh-Token` 헤더** 수용. `TokenResponse`에 `refresh_token` 추가. 프론트는 localStorage 저장 후 헤더 전송, refresh 무효 시에만 로그아웃.

### 2. Gemini 실연동
- 원인: 키는 유효하나 `gemini-2.0-flash` free-tier `limit:0`(모델별 0).
- 해결: `chat.py`·`ai_schedule.py` 모델 `gemini-2.0-flash → gemini-2.5-flash`. `teamapp/prod/ai`에 AQ. 형식 키 설치 후 재배포.

### 3. 공지 고정
- `app/routers/notices.py` `PATCH /api/notices/{id}/pin`(팀장). 프론트 고정/해제 버튼.

### 4. 상호평가 DB 연동
- `app/routers/evaluations.py`: submit을 **upsert**로(중복 409 제거), `GET /api/teams/{id}/evaluations/me` 추가. 프론트는 완료 평가를 DB에서 불러와 수정(기존 localStorage·"초기화" 폐기 → "수정").

### 5. 그 외 프론트 데모 UX
- 랜딩 "내가 활동 중인 팀" 카드, 마이페이지 총합(5항목 평균으로 정정), 홈 오늘 일정·업무 현황, 자료 업로드 데모 로컬표시, 업무 상태 드롭다운, 채팅 자동스크롤·로딩표시·AI 프롬프트 툴팁, 공지 로딩 UX.

### 6. 인프라
- GitHub Actions 없이 **로컬 ECR 빌드(amd64, `--provenance=false`) + SSM 배포** 경로 검증. ⚠️ Academy 랩 중지 시 EC2 stop → 재시작 후에도 ALB 503, EC2 start 필요.

---

## [feat] 회의 일정 영속화 + 자료 직접 파일 업로드 + 프론트 대규모 정리 — 배포 완료 (2026-06-08)

- **날짜**: 2026-06-08
- **백엔드**: `26-1-Cloude-Computing/TeamTeam_backend` main `7201f3d` (Actions #25 성공)
- **프론트**: `UsingPP/CollaborativeSoftwareProject` main `5604a7f` (S3 배포 완료)

### 1. 회의 일정 영속화 (신규)
이전에는 "회의 일정 생성"이 없는 `/meetings` API를 호출해 **404 에러**가 났고, 회의는 화면 로컬 상태로만 남아 새로고침 시 사라졌다.

| 파일 | 변경 내용 |
|------|----------|
| `app/routers/meeting.py` (신규) | `GET/POST /api/teams/{team_id}/meetings` — `meeting` 테이블 CRUD, 멤버 검증 |
| `app/schemas/meeting.py` (신규) | `MeetingCreate`, `MeetingResponse` |
| `app/main.py` | `meeting` 라우터 등록 |
| `docs/supabase_schema.sql` | `meeting` 테이블(14번) + `idx_meeting_team` 추가 |
| 프론트 `Schedule.tsx` | 회의 목록을 서버에서 조회/저장, AI 확정 일정도 회의로 영구 저장 |

> ✅ Supabase에 `meeting` 테이블 생성 완료(2026-06-08, RLS off).

### 2. 자료실 직접 파일 업로드 (신규)
기존엔 URL(링크)만 등록 가능했다. PC 파일 직접 업로드 추가.

| 파일 | 변경 내용 |
|------|----------|
| `app/routers/references.py` | `POST /api/teams/{team_id}/references/upload` — Supabase Storage `references` 버킷에 업로드(최대 20MB) 후 공개 URL을 `reference_room`에 저장 |
| 프론트 `FileStorage.tsx` | 등록 모달에 "파일 업로드 / 링크로 등록" 탭 추가 |

> ✅ Supabase Storage `references` public 버킷 생성 완료(2026-06-08).

### 3. 프론트 정리·버그 수정·성능 (프론트 전용, 배포 완료)
- **더미데이터 전면 제거**: `dumpTeams`/`MY_TEAMS`/`DUMP_TASKS`/`DUMP_MEMBERS`/하드코딩 이름(박미소·오소원 등) 삭제, API 실패 시 가짜 데이터 대신 빈 상태+알림 처리. `Tasks`/`Schedule`을 공유 `api` 인스턴스(토큰 자동·401 refresh)로 전환.
- **대시보드 인증 가드**: 비로그인 `/team/:id` 접근 시 `/`로 리다이렉트, 로딩/빈팀/팀없음 상태 분리.
- **테마 일관 적용**: 선택 테마를 localStorage에 저장(새로고침 유지), 모든 콘텐츠 페이지 하드코딩 색상을 테마 토큰으로 전환.
- **팀원 '알 수 없음' 수정**: `member.user.name` 경로로 정정(Dashboard/Chat).
- **사이드바 이름**: 하드코딩 '박미소' → `/api/users/me` 실제 이름.
- **AI 프롬프트(채팅)**: 방 미선택 가드 + 진행 스피너 + 백엔드 에러 메시지 노출.
- **공지 작성 권한**: `isLeader = true` 하드코딩 제거 → 팀 `leader_id`로 도출.
- **성능**: react-router lazy 라우트 코드 스플리팅(초기 JS 404KB→308KB).

> ⚠️ 운영 메모: 이 과정에서 service_role 키가 노출됐으므로 데모/제출 후 **키 회전** 권장(회전 시 Secrets Manager `SUPABASE_SERVICE_KEY`도 갱신 → 컨테이너 재시작).

> ✅ 참고: 아래 2026-06-05 "로그인 CORS/422" 이슈는 이미 해결됨(원인은 Secrets Manager의 무효 `SUPABASE_SERVICE_KEY`였고 키 교체+컨테이너 재시작으로 해결). 과거 기록은 이력 보존용.

---

## [bug] 로그인 CORS + 422 에러 — 미해결 (2026-06-05)

- **날짜**: 2026-06-05
- **현상**: S3 프론트 → ALB 백엔드 로그인 시 브라우저 CORS 에러 + 422 에러 동시 발생

### 1. CORS 에러

**원인**: EC2 컨테이너가 구버전으로 실행 중. 이전 `deploy.yml`이 `.env`에 `CORS_ORIGINS=*`를 기록했는데,
`CORS_ORIGINS=*` + `allow_credentials=True` 조합은 CORS 스펙상 브라우저가 차단함.
현재 `deploy.yml`은 SSM 방식으로 변경되어 `.env`를 쓰지 않으므로, 재배포 시 Secrets Manager의
올바른 CORS_ORIGINS 값이 적용됨.

**해결 방법**: `main` 브랜치에 커밋 push → GitHub Actions 자동 재배포.
또는 EC2 SSH 접속 → `docker compose pull && docker compose up -d`

### 2. 422 에러

**원인**: 로그인 입력 필드 placeholder가 "아이디"인데, 백엔드 `LoginRequest`는 `email: EmailStr`로
이메일 형식만 허용. 이메일이 아닌 값 입력 시 FastAPI가 422 반환.

**해결 방법**: 프론트 `MainPage.tsx` `LoginModal`의 input placeholder를 "이메일"로 변경.

> 이 문서는 TeamTeam Backend의 최근 머지(merge)된 주요 변경사항을 정리한 문서입니다.

---

## [fix] 로그인 500 에러 수정 + Secrets Manager 연동 + status 값 정합 — `ab77c0b`, `23cd902`

- **날짜**: 2026-06-02
- **작성자**: PYO

### 개요
로그인 시 발생하던 500 Internal Server Error를 수정하고, 시크릿 관리를 Secrets Manager로
이전했으며, 프론트/백엔드 간 status 문자열 불일치를 백엔드 기준으로 통일했습니다.

### 1. 로그인 500 에러 — `refresh_tokens` 테이블 부재

**원인**: Supabase에 `public.refresh_tokens` 테이블이 없어, 로그인 시 토큰 insert가
`PGRST205` (table not found) 에러를 던지고 500으로 이어졌습니다. 서버가 500을 반환하면
CORS 헤더가 빠져 프론트에는 CORS 에러로 보였습니다.

| 파일 | 변경 내용 |
|------|----------|
| `app/routers/auth.py` | login/refresh/logout의 `refresh_tokens` 접근을 `try/except`로 보호 — 테이블이 없어도 로그인 자체는 성공 |
| `docs/supabase_schema.sql` | `refresh_tokens` 테이블(13번) + `idx_refresh_tokens_token` 인덱스 추가 |

> ⚠️ **운영 조치 필요**: Supabase SQL Editor에서 `docs/supabase_schema.sql`의
> `refresh_tokens` 테이블을 실제로 생성해야 refresh/logout이 완전히 동작합니다.

### 2. Secrets Manager 연동 + service_role key 지원

| 파일 | 변경 내용 |
|------|----------|
| `app/core/config.py` | `teamapp/prod/jwt`, `teamapp/prod/ai`, `teamapp/prod/db` 3개 시크릿을 boto3로 로드 (`.env` 폴백) |
| `app/core/supabase.py` | `SUPABASE_SERVICE_KEY`가 있으면 anon key 대신 우선 사용 (RLS 우회, 서버용) |
| `requirements.txt` | `boto3==1.38.0` 추가 (config.py가 import하므로 누락 시 컨테이너 기동 실패) |
| `.dockerignore` | 신규 추가 — `.env`, `.venv`, `__pycache__` 등 빌드 컨텍스트에서 제외 |

### 3. 프론트/백엔드 status 값 정합 (프론트엔드 레포)

백엔드 기준값으로 프론트엔드를 통일했습니다.
- **Task status**: `To do` / `In progress` / `Done` (기존 프론트 `pending`/`in-progress`/`completed` 제거)
- **Team status**: `진행중` / `종료` (기존 프론트 `completed` 제거)
- **Schedule.tsx**: 없는 엔드포인트 `/api/teams/{id}/members` 호출 제거 → `GET /api/teams/{id}` 응답의 `members` 사용

### 4. 배포 워크플로 이중화 준비 — `23cd902`

`.github/workflows/deploy.yml`이 `EC2_HOST`와 `EC2_HOST_2` 두 인스턴스에 모두 배포하도록 확장.
실제 동작에는 `EC2_HOST_2` Secret 등록 + 두 EC2의 Elastic IP 연결이 필요(인프라 담당 후속 작업).

---

## [feat] Gemini API 모델 버전 수정 — `31004f5`

- **날짜**: 2026-05-21
- **작성자**: PYO

### 개요
AI 기능에서 사용하는 Gemini 모델명이 실제 존재하지 않는 버전(`gemini-2.5-flash`)으로 잘못 설정되어 있어 API 호출 시 에러가 발생하던 문제를 수정했습니다.

### 변경 내용

| 파일 | 변경 사항 |
|------|----------|
| `app/routers/ai_schedule.py` | `gemini-2.5-flash` → `gemini-2.0-flash` |
| `app/routers/chat.py` | `gemini-2.5-flash` → `gemini-2.0-flash` |
| `README.md` | 기술스택 명세 동기화 |

### 영향 범위
- `POST /api/teams/{team_id}/ai-sessions` — AI 일정 자동 추천
- `POST /api/chat-rooms/{room_id}/ai-prompt` — 채팅 내용 AI 요약 및 프롬프트 생성

---

## [feat] Prometheus / Grafana 모니터링 스택 + 비즈니스 메트릭 — `2e3338c` (merge commit)

- **날짜**: 2026-05-21
- **작성자**: xihxxn

### 개요
Prometheus + Grafana 기반 모니터링 스택을 추가하고, 비즈니스 핵심 엔드포인트에 커스텀 메트릭 계측 및 구조화 로깅을 적용합니다.  
이 커밋은 아래 두 커밋(`24dfa3c`, `7e479e8`)을 통합한 merge commit입니다.

---

### 1단계 — 인프라 구성 (`24dfa3c`)

Docker Compose에 Prometheus 및 Grafana 서비스를 추가하고 모니터링 설정 파일을 구성했습니다.

#### 새로운 파일

| 파일 | 설명 |
|------|------|
| `monitoring/prometheus.yml` | Prometheus 스크래핑 설정 (FastAPI `/metrics` 엔드포인트 대상) |
| `monitoring/alert.rules.yml` | 알림 규칙 정의 (레이턴시, 에러율, 이탈 등) |
| `monitoring/grafana/provisioning/dashboards/teamteam.json` | TeamTeam 전용 Grafana 대시보드 |
| `monitoring/grafana/provisioning/dashboards/dashboard.yml` | Grafana 대시보드 자동 프로비저닝 설정 |
| `monitoring/grafana/provisioning/datasources/prometheus.yml` | Grafana → Prometheus 데이터소스 연결 설정 |

#### 수정된 파일
- **`docker-compose.yml`** — `prometheus` (포트 9090), `grafana` (포트 3000) 서비스 추가

---

### 2단계 — 애플리케이션 코드 계측 (`7e479e8`)

각 라우터에 Prometheus 커스텀 메트릭을 삽입하고 구조화 로깅을 강화했습니다.

#### 새로운 파일

| 파일 | 설명 |
|------|------|
| `app/core/metrics.py` | 비즈니스 핵심 엔드포인트별 Prometheus 커스텀 메트릭 정의 |

#### 수정된 파일

| 파일 | 변경 사항 |
|------|----------|
| `app/core/logging.py` | HTTP 4xx/5xx 발생 시 `http_requests_errors_total` 카운터 증가, `user_id` 로그 컨텍스트 추가 |
| `app/dependencies.py` | 인증 의존성에서 `user_id` 로깅 컨텍스트 주입 |
| `app/routers/ai_schedule.py` | AI 일정 추천 E2E 레이턴시, 실패/수용/기각/태스크 수정 카운터 계측 |
| `app/routers/chat.py` | AI 채팅 요약 E2E 레이턴시, 외부 API 레이턴시, 클라이언트 이탈 카운터 계측 |
| `app/routers/evaluations.py` | 동료 평가 제출 성공/실패 카운터 계측 |
| `app/routers/tasks.py` | 개인 투두 조회(`mine_only=true`) 레이턴시 및 DAU 프록시 카운터 계측 |

#### 수집 메트릭 목록

| 메트릭 이름 | 타입 | 설명 |
|-------------|------|------|
| `ai_chat_summary_latency_seconds` | Histogram | AI 채팅 요약 E2E 레이턴시 |
| `ai_chat_external_api_latency_seconds` | Histogram | 외부 Gemini API 순수 호출 레이턴시 |
| `ai_chat_client_disconnect_total` | Counter | 스트리밍 중 클라이언트 이탈 수 |
| `ai_schedule_latency_seconds` | Histogram | AI 일정 추천 E2E 레이턴시 |
| `ai_schedule_failure_total` | Counter | AI 일정 추천 외부 API 실패 수 (에러 타입별) |
| `ai_schedule_accept_total` | Counter | AI 추천 일정 수용 횟수 |
| `ai_schedule_reject_total` | Counter | AI 추천 일정 기각 횟수 |
| `ai_schedule_task_modify_total` | Counter | 추천 태스크 수동 수정 횟수 |
| `task_list_mine_latency_seconds` | Histogram | 개인 투두 조회 레이턴시 (DAU 프록시 지표) |
| `evaluation_submit_total` | Counter | 동료 평가 제출 성공/실패 (결과별) |
| `http_requests_errors_total` | Counter | 전체 HTTP 에러 수 (엔드포인트/상태코드별) |

#### 알림 규칙 (`monitoring/alert.rules.yml`)

| 알림명 | 조건 | 심각도 |
|--------|------|--------|
| `AIChatSummarySlowP95` | AI 채팅 요약 p95 레이턴시 5초 초과 | warning |
| `AIScheduleSlowP95` | AI 일정 추천 p95 레이턴시 5초 초과 | warning |
| `AIScheduleAPIFailureSurge` | AI 일정 추천 실패 급증 | critical |
| `EvaluationSubmitFailure` | 동료 평가 제출 실패 1건 이상 | critical |
| `TaskListMineSlowP99` | 개인 투두 조회 p99 레이턴시 1초 초과 | critical |
| `HighServerErrorRate` | 5xx 에러율 급증 | critical |
| `AIChatDisconnectSurge` | AI 채팅 클라이언트 이탈 급증 | warning |

---

## [feat] GitHub Actions CI/CD 및 docs 초기 구성 — `5130f86`

- **날짜**: 2026-05-20
- **작성자**: PYO

### 개요
GitHub Actions를 활용한 EC2 자동 배포 파이프라인과 `docs/Project Walkthrough` 문서를 최초 구성했습니다.

### 변경 내용

| 파일 | 설명 |
|------|------|
| `.github/workflows/deploy.yml` | `main`/`master` 브랜치 push 시 EC2 자동 배포 워크플로우 |
| `docs/Project Walkthrough` | 프로젝트 전반 구조 설명 문서 초안 |

### 배포 파이프라인 흐름

```
push to main
    │
    ▼
① GitHub Secrets에서 환경변수 읽어 .env 파일 생성
    │  (SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, CORS_ORIGINS)
    ▼
② scp-action으로 소스 전체를 EC2 서버로 복사
    │
    ▼
③ ssh-action으로 EC2 접속 → docker compose up --build -d 실행
```

### GitHub Secrets 연동 목록

| Secret 이름 | 용도 |
|-------------|------|
| `EC2_HOST` | EC2 퍼블릭 IP 주소 |
| `EC2_USERNAME` | EC2 SSH 접속 사용자명 |
| `EC2_SSH_KEY` | EC2 SSH 개인키 |
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase anon key |
| `GEMINI_API_KEY` | Google Gemini API 키 |
