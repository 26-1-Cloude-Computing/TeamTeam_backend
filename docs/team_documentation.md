# TeamTeam 클라우드 컴퓨팅 프로젝트 — 팀원 공유 문서

> 최종 업데이트: 2026-06-05

> **새 세션 시작 또는 인프라 변경 확인이 필요하면 → [`docs/session_start.md`](session_start.md)**

---

## 목차

1. [최종 아키텍처](#1-최종-아키텍처)
2. [아키텍처 변경 이유](#2-아키텍처-변경-이유)
3. [현재 구현된 것](#3-현재-구현된-것)
4. [남은 작업 및 알려진 버그](#4-남은-작업-및-알려진-버그)
5. [데모 발표 계획](#5-데모-발표-계획)
6. [역할 분배](#6-역할-분배)

---

## 1. 최종 아키텍처

```
┌─────────────────────────────────────────────────────────────────┐
│                          INTERNET                               │
└───────────────┬─────────────────────────┬───────────────────────┘
                │                         │ API 요청
      ┌─────────▼──────────┐    ┌─────────▼──────────┐
      │   S3 버킷          │    │   ALB + WAF        │
      │  (프론트엔드)      │    │  HTTP:80, XSS/SQLi │
      │  React SPA 정적    │    │  차단              │
      └────────────────────┘    └────┬──────────┬────┘
                                     │          │
                        ┌────────────▼──┐  ┌────▼────────────┐
                        │ EC2 (AZ-a)    │  │ EC2 (AZ-c)      │
                        │ t3.small      │  │ t2.small        │
                        │ ─────────     │  │ ─────────       │
                        │ FastAPI       │  │ FastAPI         │  Auto Scaling Group
                        │ Prometheus    │  │ Prometheus      │  min:1 / max:2
                        │ Grafana       │  │                 │
                        └──────┬────────┘  └────────┬────────┘
                               │                    │
              ┌────────────────┼────────────────────┤
              │                │                    │
              ▼                ▼                    ▼
          Supabase    Gemini Flash API    Secrets Manager
          (외부 DB)   (외부 AI API)       (API Key 보관)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  DevOps:   GitHub Actions → ECR → SSM → EC2 Rolling Deploy
  SRE:      Prometheus → Grafana → CloudWatch Alarms → SNS → 이메일
  SecOps:   WAF(teamapp-waf) + CloudTrail + IAM + Secrets Manager
  FinOps:   AWS Budgets + Cost Allocation Tags + Cost Explorer
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 2. 아키텍처 변경 이유

중간발표 계획에서 실제 구현으로 변경된 사항과 그 이유입니다.

| 구분 | 중간발표 계획 | 최종 아키텍처 | 변경 이유 |
|------|-------------|--------------|-----------|
| 데이터베이스 | AWS RDS (PostgreSQL) | **Supabase** (외부 관리형 DB) | 개발 초기에 이미 Supabase로 구현 완료. AWS Academy에서 RDS 마이그레이션 시 데이터 손실 위험 및 비용 증가. Supabase가 관리형 PostgreSQL로 동일 기능 제공 |
| AI 연동 | AWS Lambda + Bedrock | **Gemini Flash API** (직접 호출) | Gemini 2.0 Flash가 이미 FastAPI에 연동 완료. Bedrock 대비 응답 품질이 우수하고 AWS Academy에서 Bedrock 사용 제한이 있음 |
| 모니터링 | CloudWatch 중심 | **Prometheus + Grafana** (주) + CloudWatch (보조) | Prometheus + Grafana가 이미 Docker Compose에 구성 완료. 커스텀 메트릭 9개 구현됨. CloudWatch는 로그 중앙화 보조용으로 유지 |
| 컨테이너 오케스트레이션 | ECS Fargate | **EC2 + Docker Compose + ASG** | AWS Academy에서 ECS 사용 제한. Docker Compose로 이미 운영 중이며, ASG로 이중화 충분히 달성 가능 |
| 프론트엔드 | EC2에서 서빙 | **S3 정적 호스팅** | 정적 파일은 S3가 99.999% SLA로 더 안정적. 비용도 EC2 대비 ~95% 절감 (FinOps). CloudFront 미사용 — S3 웹사이트 엔드포인트로 직접 서빙 |
| CI/CD 배포 방식 | SSH/SCP 직접 복사 | **ECR + SSM Run Command** | ECR에 이미지 푸시 후 SSM으로 EC2에서 pull. 이미지 버전 관리 가능, SSH 키 불필요 |

### 핵심 원칙
> "이미 잘 동작하는 것은 유지하고, AWS 서비스는 그 위에 더한다."

---

## 3. 현재 구현된 것

### 백엔드 (FastAPI) ✅ 완료

| 기능 | 엔드포인트 | 상태 |
|------|-----------|------|
| 인증 (JWT) | POST /api/auth/signup, /login, /refresh, /logout | ✅ |
| 팀 관리 | GET/POST /api/teams, PATCH /api/teams/{id}/status | ✅ |
| 업무 관리 | GET/POST /api/teams/{id}/tasks, PATCH /api/tasks/{id} | ✅ |
| AI 일정 추천 | POST /api/teams/{id}/ai-sessions | ✅ Gemini Flash |
| 실시간 채팅 | WebSocket /ws/chat/{room_id} | ✅ |
| 공지사항 | GET/POST /api/teams/{id}/notices | ✅ |
| 자료실 | GET/POST /api/teams/{id}/references, DELETE /api/references/{id} | ✅ |
| 팀원 평가 | POST /api/evaluations | ✅ |
| 헬스체크 | GET /health | ✅ |

### SRE (모니터링) ✅ 대부분 완료

| 항목 | 상태 | 비고 |
|------|------|------|
| Prometheus 메트릭 수집 | ✅ | 11개 커스텀 메트릭 |
| Grafana 대시보드 | ✅ | provisioning JSON 존재 |
| 알림 룰 7개 | ✅ | alert.rules.yml |
| Grafana Datasource 자동 연결 | ✅ | prometheus.yml provisioning |
| 구조화 JSON 로깅 | ✅ | request_id, latency_ms, user_id |
| X-Request-ID 헤더 | ✅ | 분산 추적용 |

### 인프라 현황

| 항목 | 상태 |
|------|------|
| EC2 × 2 (t3.small + t2.small, AZ-a + AZ-c) | ✅ |
| Docker Compose (FastAPI + Prometheus + Grafana) | ✅ |
| ALB (HTTP:80) → EC2:8000 | ✅ |
| WAF (teamapp-waf) → team-alb 연결 | ✅ |
| Auto Scaling Group (min:1, max:2) | ✅ |
| ECR 레포 (teamteam-backend) | ✅ |
| GitHub Actions CI/CD (main push → ECR → SSM → EC2) | ✅ |
| Secrets Manager (`teamapp/prod/{jwt,ai,db}`) | ✅ |
| Supabase PostgreSQL (refresh_tokens 포함 12개 테이블) | ✅ |
| S3 프론트엔드 배포 | ✅ |

---

## 4. 남은 작업 및 알려진 버그

### 🔴 Critical — 지금 당장 고쳐야 동작함

| 항목 | 원인 | 해결 방법 |
|------|------|-----------|
| **로그인 CORS 에러** | EC2 컨테이너가 구버전 실행 중 (CORS_ORIGINS=* + allow_credentials=True 조합은 브라우저가 차단) | `main` 브랜치에 아무 커밋 push → GitHub Actions 재배포, 또는 EC2 SSH 접속 후 `docker compose up -d` |
| **로그인 422 에러** | 로그인 입력 필드 레이블이 "아이디"인데 백엔드는 `EmailStr` 검증 — 이메일 형식이 아니면 422 반환 | 프론트 `LoginModal` 입력 placeholder를 "이메일" 로 변경 |

### 🟡 High — 기능 영향 있음

| 항목 | 파일 | 내용 |
|------|------|------|
| 대시보드 인증 가드 없음 | `DashboardLayout.tsx` | 로그인 없이 `/team/1` 직접 접근 가능. `useSelector(isLoggedIn)` 체크 후 `/`로 redirect 필요 |
| 빈 팀 목록 → 더미 데이터 표시 | `DashboardLayout.tsx:58-73` | `teams.length === 0`이면 에러를 throw해서 하드코딩 더미 팀을 보여줌 — 신규 유저에게 잘못된 팀이 표시됨 |

### 🟢 Medium — 배포 전 정리 권장

| 항목 | 파일 | 내용 |
|------|------|------|
| 비밀번호 콘솔 출력 | `MainPage.tsx:54` | `console.log({ email, password })` — 로그인 시 비밀번호가 브라우저 콘솔에 평문으로 찍힘 |
| 디버그 console.log 잔류 | `DashboardLayout.tsx:57, 69` | `console.log(teams)`, `console.log(1)` 제거 필요 |
| CloudWatch Alarms → SNS | SRE 담당 | 알림 룰은 정의됐으나 알림 전달 체계 미연결 |

---

## 5. 데모 발표 계획

### 시간 배분 (총 15분)

```
[0:00 - 2:00]  차별점 분석          (2분)  팀원D
[2:00 - 5:00]  아키텍처 + 4 Ops     (3분)  팀원D
[5:00 - 13:00] 데모 시연            (8분)  팀원D
[13:00 - 15:00] 버퍼 / 마무리       (2분)  여유 시간
```

### 시연 흐름

```
Step 1  [0:00 - 1:00]  로그인 → 팀 대시보드 진입 (S3 URL 접속)
Step 2  [1:00 - 2:30]  AI 일정 추천 (Gemini Flash) ← 핵심 차별점
Step 3  [2:30 - 3:30]  실시간 채팅 (WebSocket)
Step 4  [3:30 - 4:30]  업무 관리 (상태 변경 → Grafana 실시간 반영)
Step 5  [4:30 - 5:30]  공지사항 + 자료실
Step 6  [5:30 - 7:00]  Grafana 대시보드 (SRE 메트릭 라이브)
Step 7  [7:00 - 8:00]  CI/CD 파이프라인 (GitHub Actions 배포 로그)
```

### 예상 질문 & 답변

| 예상 질문 | 답변 포인트 |
|----------|-----------|
| DB가 AWS 외부인데 괜찮나요? | Supabase는 관리형 PostgreSQL로 99.99% SLA 제공. AWS RDS와 동일 엔진, 외부 연결로도 안정적 운영 가능 |
| Lambda/ECS 안 쓴 이유는? | AWS Academy 서비스 제한 + 이미 Docker Compose 운영 중. EC2 + ASG로 동일한 이중화 달성 |
| SLO는 어떻게 정의했나요? | 가용성 99.9%, p99 응답시간 500ms 이하, 에러율 1% 미만 |
| Secrets Manager 어떻게 쓰나요? | EC2 IAM Instance Profile → Secrets Manager 읽기 권한 → 앱 시작 시 자동 주입 |
| CloudFront 안 쓴 이유는? | 학교 프로젝트 범위에서 S3 직접 호스팅으로 충분. 비용 절감 및 설정 단순화 |

---

## 6. 역할 분배

| 팀원 | 담당 | 주요 작업 |
|------|------|----------|
| A | 인프라 리더 | VPC, EC2×2, ASG, ALB, IAM |
| B | SecOps | Secrets Manager, WAF, CloudTrail, CORS |
| C | SRE / 로깅 | Grafana 대시보드, CloudWatch Alarms, SNS |
| D | 총괄 PM | ECR, GitHub Actions, 발표, 데모 리허설 |
| E | 프론트 배포 | S3 버킷, npm build, 정적 호스팅 배포 |
| F | FinOps | AWS Budgets, Cost Allocation Tags, Cost Explorer |
| G | 테스트 | 부하 테스트, 데모 시나리오 검증 |
