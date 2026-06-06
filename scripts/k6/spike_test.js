/**
 * 시나리오 2: 공지 스파이크 테스트
 * 공지사항이 올라오자마자 전원이 한꺼번에 접속하는 상황
 * 평상시 10명 → 급증 100명 → 복귀 10명
 *
 * 실행:
 *   k6 run scripts/k6/spike_test.js
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { Rate, Trend } from "k6/metrics";

const BASE_URL = __ENV.BASE_URL || "http://localhost:8000";

const errorRate = new Rate("error_rate");
const noticeLatency = new Trend("notice_latency");

export const options = {
  stages: [
    { duration: "1m",  target: 10  }, // 평상시
    { duration: "10s", target: 100 }, // 공지 올라오자마자 급증 (10초 만에 100명)
    { duration: "1m",  target: 100 }, // 스파이크 유지
    { duration: "10s", target: 10  }, // 빠르게 복귀
    { duration: "1m",  target: 10  }, // 복구 확인
  ],
  thresholds: {
    // 스파이크 중 오류율 5% 미만
    error_rate: ["rate<0.05"],
    // 스파이크 이후 복귀 확인 (전체 p95 기준)
    http_req_duration: ["p(95)<2000"],
    // notice 조회 레이턴시
    notice_latency: ["p(95)<1000"],
  },
};

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
  check(res, { "login success": (r) => r.status === 200 });
  return res.status === 200 ? res.json() : null;
}

export default function () {
  const user = USERS[Math.floor(Math.random() * USERS.length)];

  // 1. 로그인
  const loginData = login(user);
  if (!loginData) {
    errorRate.add(1);
    sleep(1);
    return;
  }
  errorRate.add(0);

  const headers = {
    Authorization: `Bearer ${loginData.access_token}`,
    "Content-Type": "application/json",
  };

  // 2. 내 팀 확인
  const teamsRes = http.get(`${BASE_URL}/api/teams`, { headers });
  if (!check(teamsRes, { "teams 200": (r) => r.status === 200 }) || !teamsRes.json().length) {
    errorRate.add(1);
    sleep(1);
    return;
  }

  const teamId = teamsRes.json()[0].id;

  // 3. 공지사항 조회 (스파이크의 핵심 — 공지 올라오자마자 모두가 확인)
  const start = Date.now();
  const noticesRes = http.get(`${BASE_URL}/api/teams/${teamId}/notices`, { headers });
  noticeLatency.add(Date.now() - start);

  const noticesOk = check(noticesRes, {
    "notices 200": (r) => r.status === 200,
    "응답 1초 이내": (r) => r.timings.duration < 1000,
  });
  errorRate.add(!noticesOk ? 1 : 0);

  // 4. 공지 상세 조회 (목록에 항목 있을 때)
  if (noticesOk && noticesRes.json().length > 0) {
    const noticeId = noticesRes.json()[0].id;
    const detailRes = http.get(`${BASE_URL}/api/notices/${noticeId}`, { headers });
    const detailOk = check(detailRes, { "notice detail 200": (r) => r.status === 200 });
    errorRate.add(!detailOk ? 1 : 0);
  }

  // 5. 할일 조회 (공지 확인 후 자기 할일 체크)
  const tasksRes = http.get(
    `${BASE_URL}/api/teams/${teamId}/tasks?mine_only=true`,
    { headers }
  );
  const tasksOk = check(tasksRes, { "tasks 200": (r) => r.status === 200 });
  errorRate.add(!tasksOk ? 1 : 0);

  sleep(0.5);
}
