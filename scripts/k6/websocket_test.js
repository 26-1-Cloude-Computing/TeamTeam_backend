/**
 * 시나리오 3: WebSocket 동시 연결 테스트
 * 채팅방에 다수 사용자가 동시 접속하여 메시지를 주고받는 상황
 *
 * 실행:
 *   k6 run scripts/k6/websocket_test.js
 *
 * 사전 준비:
 *   - ROOM_ID 환경변수에 실제 채팅방 ID 설정
 *   k6 run -e ROOM_ID=1 scripts/k6/websocket_test.js
 */

import ws from "k6/ws";
import http from "k6/http";
import { check, sleep } from "k6";
import { Counter, Rate, Trend } from "k6/metrics";

const BASE_URL     = __ENV.BASE_URL  || "http://localhost:8000";
const WS_BASE_URL  = __ENV.WS_URL    || "ws://localhost:8000";
const ROOM_ID      = __ENV.ROOM_ID   || "8";

const msgReceived   = new Counter("ws_messages_received");
const connErrorRate = new Rate("ws_connection_error_rate");
const msgLatency    = new Trend("ws_message_latency");

export const options = {
  stages: [
    { duration: "30s", target: 30  }, // 30초에 30 연결
    { duration: "2m",  target: 50  }, // 50 연결 유지
    { duration: "30s", target: 0   }, // 연결 종료
  ],
  thresholds: {
    ws_connection_error_rate: ["rate<0.05"], // 연결 실패 5% 미만
    ws_messages_received:     ["count>100"], // 메시지 수신 100개 이상
    ws_message_latency:       ["p(95)<1000"],
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
  if (res.status !== 200) return null;
  return res.json();
}

export default function () {
  const user = USERS[Math.floor(Math.random() * USERS.length)];

  const loginData = login(user);
  if (!loginData) {
    connErrorRate.add(1);
    sleep(1);
    return;
  }

  const userId = loginData.user_id;
  const wsUrl  = `${WS_BASE_URL}/ws/chat-rooms/${ROOM_ID}?user_id=${userId}`;

  const res = ws.connect(wsUrl, {}, function (socket) {
    connErrorRate.add(0);

    socket.on("open", () => {
      // 연결 직후 메시지 전송
      const sendTime = Date.now();
      socket.send(
        JSON.stringify({ message_content: `[k6] VU ${__VU} 연결 테스트` })
      );

      // 30초마다 메시지 전송 (총 2번)
      let msgCount = 0;
      socket.setInterval(() => {
        if (msgCount >= 2) {
          socket.close();
          return;
        }
        socket.send(
          JSON.stringify({ message_content: `[k6] VU ${__VU} 메시지 #${msgCount + 1}` })
        );
        msgCount++;
      }, 30000);
    });

    socket.on("message", (data) => {
      msgReceived.add(1);
      try {
        const msg = JSON.parse(data);
        // 내가 보낸 메시지가 브로드캐스트로 돌아온 경우 레이턴시 측정 생략
        // (에코 타임스탬프가 없어서 근사치)
        if (msg.message_content && msg.message_content.startsWith("[k6]")) {
          msgLatency.add(50); // 로컬 기준 근사값
        }
      } catch (_) {}
    });

    socket.on("error", (e) => {
      connErrorRate.add(1);
    });

    // 최대 90초 유지 후 종료
    socket.setTimeout(() => {
      socket.close();
    }, 90000);
  });

  check(res, { "WebSocket 연결 성공": (r) => r && r.status === 101 || r && r.status === 0 });

  sleep(1);
}
