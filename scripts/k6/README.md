# k6 부하 테스트

## 사전 준비

### 1. k6 설치
```bash
brew install k6
```

### 2. 테스트 유저 생성
스크립트에서 사용하는 계정 5개를 사전에 회원가입해두어야 합니다.
```
test1@teamteam.com ~ test5@teamteam.com / 비밀번호: test1234!
```

### 3. 백엔드 실행
```bash
docker compose up backend -d
```

---

## 시나리오 1: 기본 부하 테스트

**목적**: 일반 사용자 플로우(로그인→팀조회→할일조회→공지확인)를 50명이 5분간 지속  
**합격 기준**: p95 500ms 이하, 오류율 1% 미만

```bash
k6 run scripts/k6/load_test.js
```

---

## 시나리오 2: 공지 스파이크 테스트

**목적**: 공지사항이 올라오자마자 10명 → 100명으로 급증, 이후 복귀  
**합격 기준**: 스파이크 중 오류율 5% 미만, p95 2초 이내

```bash
k6 run scripts/k6/spike_test.js
```

---

## 시나리오 3: WebSocket 동시 연결 테스트

**목적**: 채팅방에 50명 동시 접속, 메시지 송수신  
**합격 기준**: 연결 실패 5% 미만, 메시지 수신 100건 이상, p95 1초 이내

```bash
# ROOM_ID는 실제 존재하는 채팅방 ID로 변경
k6 run -e ROOM_ID=1 scripts/k6/websocket_test.js
```

---

## 결과 확인

k6 실행 후 터미널에서 아래 항목 확인:
- `http_req_duration` — 응답시간 분포 (p50/p95/p99)
- `http_req_failed` — 실패율
- `error_rate` — 커스텀 오류율
- `ws_messages_received` — WebSocket 수신 메시지 수

### Grafana 연동 (선택)
```bash
k6 run --out influxdb=http://localhost:8086/k6 scripts/k6/load_test.js
```
