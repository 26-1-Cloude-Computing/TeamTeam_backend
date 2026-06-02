# 세션 시작 가이드 — TeamTeam

> 채팅을 지우고 새 세션을 시작하거나, 팀원이 인프라를 바꿨을 때 현재 상태를 빠르게 파악하기 위한 문서입니다.
> 작성 기준: 2026-06-02

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
- **t3 (primary)**: 배포 대상 인스턴스
- **t2 (secondary)**: 이중화용

### Step 2 — GitHub Secret 업데이트
```
GitHub vyjsjs/TeamTeam_backend → Settings → Secrets and variables → Actions
→ EC2_HOST → 연필 아이콘 → 새 IP 입력
```
`EC2_HOST_2`가 등록되어 있다면 t2 IP도 업데이트.

### Step 3 — EC2에 Docker 컨테이너 올리기
```bash
ssh -i TeamTeam.pem ec2-user@<새 EC2 IP>
cd ~/TeamTeam_backend
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
- [ ] 인스턴스 타입 변경 여부 (기준: t3.small × 1, t2.micro × 1)
- [ ] IAM 역할 변경 여부 (Secrets Manager 읽기 권한 필수)
- [ ] 보안 그룹 변경 여부 (ALB → 8000 포트 허용 필수)

### AWS ALB
- [ ] 리스너: HTTP:80 → Target Group 포워딩 유지 여부
- [ ] Target Group 헬스체크 경로: `/health`
- [ ] Target Group 등록 인스턴스 수 (현재: 2개 등록 목표, 상황에 따라 1개)

### Secrets Manager (`us-east-1`)
아래 3개 시크릿 모두 존재해야 앱이 뜸:

| 시크릿 이름 | 필수 키 |
|------------|---------|
| `teamapp/prod/jwt` | `JWT_SECRET`, `REFRESH_SECRET` |
| `teamapp/prod/ai` | `GEMINI_API_KEY` |
| `teamapp/prod/db` | `SUPABASE_URL`, `SUPABASE_KEY`, `CORS_ORIGINS` |

확인 명령어 (Session Manager 또는 로컬 AWS CLI):
```bash
aws secretsmanager get-secret-value --secret-id teamapp/prod/db \
  --region us-east-1 --query SecretString --output text
```
`SUPABASE_SERVICE_KEY`가 추가됐는지도 확인 (없으면 anon key로 폴백, RLS 이슈 가능).

### GitHub Secrets (`vyjsjs/TeamTeam_backend`)
| Secret | 기준값 |
|--------|--------|
| `EC2_HOST` | ⚠️ 세션 시작마다 바뀜 — 현재 세션 IP로 업데이트 |
| `EC2_HOST_2` | ⚠️ 등록 여부 확인 (이중화 완료 시 존재) |
| `EC2_SSH_KEY` | 변경 불필요 |
| `EC2_USERNAME` | `ec2-user` 고정 |
| `SUPABASE_URL` / `SUPABASE_KEY` / `GEMINI_API_KEY` | 변경 불필요 |

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
| `refresh_tokens` | ⚠️ **JWT 토큰 저장용 — 없으면 로그인 동작은 하지만 refresh/logout 불완전** |

### S3 프론트엔드
- [ ] 버킷 정적 호스팅 활성화 여부
- [ ] 버킷 퍼블릭 액세스 차단 해제 + 버킷 정책(PublicRead) 유지 여부
- [ ] 최신 빌드 배포 여부 — GitHub 최신 커밋과 S3 파일이 일치하는지 확인:
  ```bash
  # S3에 올라간 index.html 수정 시각 확인
  aws s3 ls s3://teamteam-frontend-bucket/index.html
  ```
- [ ] CloudFront 배포 연결 여부 (현재 미완 — S3 직접 접근 중)

---

## 3. 코드 현재 상태 (2026-06-02 기준)

### 백엔드 (`vyjsjs/TeamTeam_backend`) — 최신 커밋: `9c035c3`
```
9c035c3  docs: 로그인 500 수정·Secrets Manager·status 정합 반영
23cd902  ci: deploy to both EC2 instances
ab77c0b  fix: login (로그인 500, try/except, boto3, .dockerignore)
338b04c  Update config.py (Secrets Manager 연동)
```

**배포된 코드 = GitHub main = EC2에 올라간 코드** (GitHub Actions 자동 배포, 단 EC2_HOST가 최신이어야 함)

### 프론트엔드 (`UsingPP/CollaborativeSoftwareProject`) — 최신 커밋: `5d7f690`
```
5d7f690  fix: 로그인 모달 await 누락, 회원가입 자동 로그인
b6225d9  docs: gap analysis v4
1457320  fix: login (status 값 정합, Schedule 멤버 엔드포인트 수정)
```

> **⚠️ 프론트엔드는 CI/CD 없음 — GitHub push만으로는 S3에 반영되지 않습니다.**
> 코드 변경 후 아래 수동 배포 절차를 따라야 합니다.

### 프론트엔드 코드 변경 후 배포 절차

```bash
# 1. 로컬에서 코드 수정 후 GitHub push
cd CollaborativeSoftwareProject
git add -A
git commit -m "fix: 변경 내용 설명"
git push origin main

# 2. 환경변수 설정 (.env.production 또는 빌드 시 직접)
#    VITE_SERVER_URL = ALB 주소
echo "VITE_SERVER_URL=http://team-alb-1271871703.us-east-1.elb.amazonaws.com" > .env.production

# 3. 빌드
npm run build
# → dist/ 폴더 생성됨

# 4. S3에 업로드
aws s3 sync dist/ s3://teamteam-frontend-bucket --delete

# 5. 배포 확인
open http://teamteam-frontend-bucket.s3-website-us-east-1.amazonaws.com
# 또는 curl로 200 확인
curl -s -o /dev/null -w "%{http_code}" \
  http://teamteam-frontend-bucket.s3-website-us-east-1.amazonaws.com
```

> `aws s3 sync` 실행 시 AWS 자격증명이 필요합니다.  
> AWS Academy 세션에서 발급된 임시 자격증명을 `~/.aws/credentials`에 설정하거나  
> `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` 환경변수로 설정하세요.

### VITE_SERVER_URL 환경변수

프론트가 백엔드 API를 어디로 보낼지 결정하는 핵심 변수입니다.

| 환경 | 값 |
|------|-----|
| 로컬 개발 | `http://localhost:8000` |
| 운영 (현재) | `http://team-alb-1271871703.us-east-1.elb.amazonaws.com` |
| 운영 (CloudFront 연결 후) | CloudFront URL로 변경 필요 |

`.env.production` 파일에 설정하면 `npm run build` 시 자동으로 번들에 포함됩니다.

---

## 4. 현재 미완료 작업 (인프라 담당 후속)

| 항목 | 담당 | 상태 |
|------|------|------|
| Supabase `refresh_tokens` 테이블 생성 | 백엔드 | ⚠️ 생성 필요 (없으면 refresh/logout 불완전) |
| EC2_HOST_2 GitHub Secret 등록 + t2 Elastic IP 연결 | 인프라A | ❌ 미완 |
| **프론트엔드 CI/CD 구성** | 프론트E / 인프라D | ❌ 미완 — main push 시 자동으로 빌드 → S3 업로드되도록 GitHub Actions 워크플로 추가 필요 (`UsingPP/CollaborativeSoftwareProject`에 `.github/workflows/deploy.yml` 없음) |
| S3 프론트엔드 최신 빌드 배포 | 프론트E | ❌ 미완 (현재 수동 배포 필요 — 위 배포 절차 참고) |
| CloudFront 연결 (HTTPS) | 프론트E | ❌ 미완 |
| CORS 실제 URL 적용 (`deploy.yml`의 `CORS_ORIGINS=*` 제거) | SecOps B | ❌ 미완 |
| ALB WAF 연결 | SecOps B | ❌ 미완 |
| CloudWatch Alarms + SNS | SRE C | ❌ 미완 |
| AWS Budgets 알림 설정 | FinOps F | ❌ 미완 |

---

## 5. 알려진 이슈

| 이슈 | 영향 | 해결 시점 |
|------|------|----------|
| Refresh Token 쿠키 SameSite=Lax | S3(프론트) ↔ ALB(백엔드) 크로스 도메인에서 refresh 호출 시 쿠키 미전송 → 15분 후 강제 로그아웃 | CloudFront HTTPS 구성 후 `samesite="none", secure=True`로 변경 |
| `deploy.yml`이 `.env`에 `CORS_ORIGINS=*` 기록 | Secrets Manager의 실제 CORS URL이 덮어써짐 | `deploy.yml`에서 해당 줄 제거 |

---

## 6. EC2 접속 후 자주 쓰는 명령어

```bash
# 컨테이너 상태 확인
docker ps

# 로그 확인 (최근 100줄)
docker logs my-backend --tail 100 -f

# 컨테이너 재시작
docker compose down && docker compose up -d

# 최신 코드 pull 후 재빌드
git pull
docker compose up --build -d

# 디스크 정리 (빌드 실패 시)
docker system prune -af --volumes
```

---

## 7. 로그인 동작 검증 (빠른 curl 테스트)

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
