/**
 * 시나리오 1: 기본 부하 테스트
 * 일반 사용자 플로우 — 로그인 → 팀 조회 → 할일 조회 → 공지 확인
 *
 * 실행:
 *   k6 run scripts/k6/load_test.js
 *   k6 run -e BASE_URL=http://localhost:8000 scripts/k6/load_test.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

// 커스텀 메트릭
const errorRate = new Rate("error_rate");
const taskLatency = new Trend("task_list_latency");

export const options = {
  stages: [
    { duration: "30s", target: 50 }, // 30초 동안 50명으로 ramp-up
    { duration: "5m", target: 50 },  // 5분 유지
    { duration: "30s", target: 0 },  // 30초 동안 ramp-down
  ],
  thresholds: {
    http_req_duration: ["p(95)<500"], // p95 500ms 이하
    error_rate: ["rate<0.01"],        // 오류율 1% 미만
    http_req_failed: ["rate<0.01"],
  },
};

// 테스트 유저 풀 (사전에 가입된 계정 필요)
const USERS = [
  { email: "k6test1@teamteam.com", password: "k6test1234!" },
  { email: "k6test2@teamteam.com", password: "k6test1234!" },
  { email: "k6test3@teamteam.com", password: "k6test1234!" },
  { email: "k6test4@teamteam.com", password: "k6test1234!" },
  { email: "k6test5@teamteam.com", password: "k6test1234!" },
];

function login(user) {
  const res = http.post(
    `${BASE_URL}/api/auth/login`,
    JSON.stringify({ email: user.email, password: user.password }),
    { headers: { "Content-Type": "application/json" } }
  );
  check(res, { "login 200": (r) => r.status === 200 });
  return res.status === 200 ? res.json("access_token") : null;
}

export default function () {
  const user = USERS[Math.floor(Math.random() * USERS.length)];

  // 1. 로그인
  const token = login(user);
  if (!token) {
    errorRate.add(1);
    return;
  }
  errorRate.add(0);

  const headers = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  };

  // 2. 내 팀 목록 조회
  const teamsRes = http.get(`${BASE_URL}/api/teams`, { headers });
  const teamsOk = check(teamsRes, { "teams 200": (r) => r.status === 200 });
  errorRate.add(!teamsOk ? 1 : 0);

  sleep(0.5);

  if (!teamsOk || !teamsRes.json().length) {
    sleep(1);
    return;
  }

  const teamId = teamsRes.json()[0].id;

  // 3. 내 할일 조회
  const start = Date.now();
  const tasksRes = http.get(
    `${BASE_URL}/api/teams/${teamId}/tasks?mine_only=true`,
    { headers }
  );
  taskLatency.add(Date.now() - start);
  const tasksOk = check(tasksRes, { "tasks 200": (r) => r.status === 200 });
  errorRate.add(!tasksOk ? 1 : 0);

  sleep(0.5);

  // 4. 공지사항 조회
  const noticesRes = http.get(
    `${BASE_URL}/api/teams/${teamId}/notices`,
    { headers }
  );
  const noticesOk = check(noticesRes, { "notices 200": (r) => r.status === 200 });
  errorRate.add(!noticesOk ? 1 : 0);

  sleep(1);
}
