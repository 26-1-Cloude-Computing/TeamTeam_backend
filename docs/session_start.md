# 세션 시작 가이드 — TeamTeam

> 채팅을 지우고 새 세션을 시작하거나, 팀원이 인프라를 바꿨을 때 현재 상태를 빠르게 파악하기 위한 문서입니다.
> 작성 기준: 2026-06-05

---

## 0. 고정 리소스 (변하지 않는 값)

| 리소스 | 값 |
|--------|-----|
| **ALB DNS** | `http://team-alb-1271871703.us-east-1.elb.amazonaws.com` |
| **S3 프론트엔드** | `http://teamteam-frontend-bucket.s3-website-us-east-1.amazonaws.com` |
| **Supabase URL** | `https://wbjxofnpdyarpygzwckg.supabase.co` |
| **백엔드 GitHub** | `https://github.com/vyjsjs/TeamTeam_backend` |
| **프론트 GitHub** | `https://github.com/UsingPP/CollaborativeSoftwareProject` |
| **AWS 리전** | `us-east-1` |
| **SSH 키 파일** | 프로젝트 루트 `TeamTeam.pem` |
| **EC2 SSH 사용자** | `ec2-user` |

---

## 1. AWS Academy 세션 시작 시 매번 할 것

AWS Academy 세션을 새로 시작하면 EC2 퍼블릭 IP가 바뀝니다.

### Step 1 — 새 EC2 IP 확인
```
AWS 콘솔 → EC2 → Instances → 인스턴스 선택 → Public IPv4 address 복사
```

인스턴스가 2개 있습니다 (t3, t2 — 이중화):
- **t3.small (primary)**: 배포 대상 인스턴스 (Grafana 포함)
- **t2.small (secondary)**: 이중화용

### Step 2 — GitHub Secret 업데이트
```
GitHub vyjsjs/TeamTeam_backend → Settings → Secrets and variables → Actions
→ EC2_HOST → 연필 아이콘 → 새 IP 입력
```
`EC2_HOST_2`가 등록되어 있다면 t2.small IP도 업데이트.

### Step 3 — 백엔드 컨테이너 확인

배포는 GitHub Actions(SSM)가 자동으로 처리합니다.
직접 확인이 필요한 경우:
```bash
ssh -i TeamTeam.pem ec2-user@<새 EC2 IP>
cd ~/TeamTeam_backend
docker ps
# 컨테이너가 없으면:
docker compose up -d
```

### Step 4 — 백엔드 헬스체크
```bash
curl http://team-alb-1271871703.us-east-1.elb.amazonaws.com/health
# 정상: {"status":"healthy"}
# 502면 컨테이너가 안 떠 있는 것
```

---

## 2. 인프라 변경사항 확인 체크리스트

> 팀원이 인프라를 수정했을 수 있으므로, 세션 시작 시 아래 항목을 콘솔에서 확인합니다.

### AWS EC2
- [ ] 인스턴스 상태: Running 여부
- [ ] 인스턴스 타입 변경 여부 (기준: t3.small × 1, t2.small × 1)
- [ ] IAM 역할 변경 여부 (Secrets Manager 읽기 권한 필수)
- [ ] 보안 그룹 변경 여부 (ALB → 8000 포트 허용 필수)
- [ ] EC2에 `Role=backend` 태그 있는지 확인 (SSM 배포 타겟 조건)

### AWS ALB
- [ ] 리스너: HTTP:80 → Target Group 포워딩 유지 여부
- [ ] Target Group 헬스체크 경로: `/health`
- [ ] Target Group 등록 인스턴스 수 (현재: 2개 목표)

### Secrets Manager (`us-east-1`)
아래 3개 시크릿 모두 존재해야 앱이 뜸:

| 시크릿 이름 | 필수 키 |
|------------|---------|
| `teamapp/prod/jwt` | `JWT_SECRET`, `REFRESH_SECRET` |
| `teamapp/prod/ai` | `GEMINI_API_KEY` |
| `teamapp/prod/db` | `SUPABASE_URL`, `SUPABASE_KEY`, `SUPABASE_SERVICE_KEY`, `CORS_ORIGINS` |

`CORS_ORIGINS` 값 확인 (쉼표로 두 URL이 있어야 함, 띄어쓰기 없이):
```bash
aws secretsmanager get-secret-value --secret-id teamapp/prod/db \
  --region us-east-1 --query SecretString --output text
# CORS_ORIGINS 값이 아래와 정확히 일치해야 함:
# http://teamteam-frontend-bucket.s3-website-us-east-1.amazonaws.com,http://team-alb-1271871703.us-east-1.elb.amazonaws.com
```

### GitHub Secrets (`vyjsjs/TeamTeam_backend`)
| Secret | 기준값 |
|--------|--------|
| `EC2_HOST` | ⚠️ 세션 시작마다 바뀜 — 현재 세션 IP로 업데이트 |
| `EC2_HOST_2` | ⚠️ 등록 여부 확인 (이중화 완료 시 존재) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` | ⚠️ 세션 시작마다 갱신 필요 |
| `EC2_SSH_KEY` / `EC2_USERNAME` | 변경 불필요 |

### Supabase 테이블 확인
Supabase 대시보드 → Table Editor 에서 아래 테이블이 모두 있어야 합니다:

| 테이블 | 비고 |
|--------|------|
| `user` | 회원 정보 |
| `team` | 팀 정보 |
| `team_member` | 팀-멤버 매핑 |
| `task` | 업무 |
| `notice` | 공지사항 |
| `chat_room` / `chat_room_member` / `chat_message` | 채팅 |
| `ai_schedule_session` / `ai_schedule_task` | AI 일정 |
| `reference_room` | 자료실 |
| `evaluation` | 상호평가 |
| `refresh_tokens` | ✅ 생성 완료 — JWT 토큰 저장용 |

### S3 프론트엔드
- [ ] 버킷 정적 호스팅 활성화 여부
- [ ] 버킷 퍼블릭 액세스 차단 해제 + 버킷 정책(PublicRead) 유지 여부
- [ ] 최신 빌드 배포 여부:
  ```bash
  aws s3 ls s3://teamteam-frontend-bucket/index.html
  ```

---

## 3. 코드 현재 상태 (2026-06-05 기준)

### 백엔드 (`vyjsjs/TeamTeam_backend`)
- Secrets Manager에서 설정 로드 (`.env` 불필요)
- docker-compose.yml에 `env_file` 없음 — Secrets Manager가 유일한 설정 소스
- SSM Run Command로 EC2에 배포 (SSH/SCP 방식 아님)

### 프론트엔드 (`UsingPP/CollaborativeSoftwareProject`)
- S3 정적 호스팅 배포됨
- `.env`에 `VITE_SERVER_URL`, `VITE_API_BASE_URL` 모두 ALB URL로 설정됨
- CI/CD 없음 — 수동 빌드 + S3 업로드 필요

### 프론트엔드 코드 변경 후 배포 절차

```bash
cd CollaborativeSoftwareProject

# 1. 코드 수정 후 빌드
npm run build
# → dist/ 폴더 생성됨

# 2. S3에 업로드 (AWS 자격증명 필요)
aws s3 sync dist/ s3://teamteam-frontend-bucket --delete

# 3. 배포 확인
curl -s -o /dev/null -w "%{http_code}" \
  http://teamteam-frontend-bucket.s3-website-us-east-1.amazonaws.com
# 200이 나와야 정상
```

> `aws s3 sync` 실행 시 AWS Academy 세션의 임시 자격증명이 필요합니다.
> `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` 환경변수로 설정하세요.

---

## 4. 현재 알려진 버그

| 버그 | 증상 | 원인 | 해결 방법 |
|------|------|------|-----------|
| **로그인 CORS 에러** | 브라우저 콘솔 "No 'Access-Control-Allow-Origin'" | EC2가 구버전 컨테이너 실행 중. `CORS_ORIGINS=*` + `allow_credentials=True` 조합은 브라우저가 차단 | `main` push → GitHub Actions 재배포. 또는 EC2 SSH → `docker compose up -d` |
| **로그인 422 에러** | 서버 422 Unprocessable Entity | 로그인 입력 placeholder "아이디" → 이메일 형식 아닌 값 입력 시 FastAPI EmailStr 검증 실패 | 프론트 `LoginModal` placeholder "이메일"로 변경 |
| **비밀번호 콘솔 노출** | 개발자 도구에 비밀번호 평문 출력 | `MainPage.tsx:54` `console.log({ email, password })` | 해당 줄 삭제 |
| **대시보드 인증 가드 없음** | 비로그인 상태로 `/team/1` 직접 접근 가능 | `DashboardLayout.tsx`에 인증 체크 없음 | `isLoggedIn` 확인 후 `/`로 `navigate` 추가 |
| **빈 팀 → 더미 데이터** | 신규 유저에게 가짜 팀 표시 | `DashboardLayout.tsx:58-73` teams 빈 배열이면 에러 throw 후 더미 fallback | `teams.length === 0` throw 제거, 빈 팀 상태 UI로 처리 |

---

## 5. EC2 접속 후 자주 쓰는 명령어

```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인 (최근 100줄)
docker logs my-backend --tail 100 -f

# 컨테이너 재시작
docker compose down && docker compose up -d

# 최신 이미지 pull 후 재시작 (ECR에서)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin 851725653265.dkr.ecr.us-east-1.amazonaws.com
docker compose pull && docker compose up -d

# 디스크 정리 (빌드 실패 시)
docker system prune -af --volumes
```

---

## 6. 로그인 동작 검증 (빠른 curl 테스트)

```bash
# 회원가입
curl -s -X POST http://team-alb-1271871703.us-east-1.elb.amazonaws.com/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test1234","name":"테스트"}' | python3 -m json.tool

# 로그인
curl -s -X POST http://team-alb-1271871703.us-east-1.elb.amazonaws.com/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test1234"}' | python3 -m json.tool

# 헬스체크
curl http://team-alb-1271871703.us-east-1.elb.amazonaws.com/health
```
