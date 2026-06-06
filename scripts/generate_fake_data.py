#!/usr/bin/env python3
"""
TeamTeam 7일치 가짜 Prometheus 데이터 생성기

Day1 — 킥오프, 정상 운영
Day2 — 업무 가속, 부하 증가 예고
Day3 — 중간 점검, 1차 마감 압박
Day4 — 위기 본격화 🚨 (레이턴시 폭증, 에러 급증, 새벽 스퍼트)
Day5 — 대응 완료, 안정화
Day6 — 완전 정상, 마감 준비
Day7 — 최종 마감, 평가 제출 폭증 → 전원 완료 ✅

사용법:
  python generate_fake_data.py
  → teamteam_metrics.openmetrics 생성

이후 Prometheus에 주입:
  docker run --rm -v "$(pwd):/data" prom/prometheus:v2.52.0 \
    promtool tsdb create-blocks-from openmetrics \
    /data/teamteam_metrics.openmetrics /data/tsdb_blocks_new

  docker restart teamteam_backend-prometheus-1
"""

import math
import random
import time
import os

random.seed(42)

STEP = 15
OUTPUT_FILE = "teamteam_metrics.openmetrics"
DAYS = 7

NOW   = int(time.time())
DAY   = 86400
START = NOW - DAYS * DAY

JOB = 'job="teamteam-backend",instance="backend:8000"'

def jitter(base, pct=0.08):
    return base * (1 + random.uniform(-pct, pct))

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def ts_range(start, end, step=STEP):
    t = start
    while t <= end:
        yield t
        t += step

def work_intensity(hour_frac):
    return max(0.0, math.sin(math.pi * clamp((hour_frac - 0.375) / 0.375, 0, 1)))

def gaussian(x, center, width):
    return math.exp(-((x - center) ** 2) / (2 * width ** 2))

def get_params(ts):
    offset    = ts - START
    day       = offset / DAY
    day_int   = int(day) + 1
    hour_frac = (offset % DAY) / DAY
    work      = work_intensity(hour_frac)

    # Day 1: 킥오프, 정상
    if day_int == 1:
        return {
            "n_chat":  max(0, int(jitter(5  + work * 15))),
            "n_sched": max(0, int(jitter(3  + work * 10))),
            "n_task":  max(0, int(jitter(10 + work * 35))),
            "chat_p50": jitter(1.2), "chat_p95": jitter(1.8), "chat_p99": jitter(2.2),
            "sched_p50": jitter(1.5), "sched_p95": jitter(2.0), "sched_p99": jitter(2.5),
            "task_p50": jitter(0.07), "task_p95": jitter(0.11), "task_p99": jitter(0.16),
            "ws_base": int(jitter(1 + work * 3)),
            "error_prob": 0.0, "disconnect_prob": 0.0, "sched_fail_prob": 0.0,
            "accept_rate": 0.85, "reject_rate": 0.10,
            "eval_success": 0, "eval_fail_prob": 0.0,
        }

    # Day 2: 부하 증가 예고
    elif day_int == 2:
        return {
            "n_chat":  max(0, int(jitter(8  + work * 22))),
            "n_sched": max(0, int(jitter(5  + work * 14))),
            "n_task":  max(0, int(jitter(20 + work * 55))),
            "chat_p50": jitter(1.4), "chat_p95": jitter(2.2), "chat_p99": jitter(2.8),
            "sched_p50": jitter(1.8), "sched_p95": jitter(2.8), "sched_p99": jitter(3.3),
            "task_p50": jitter(0.08), "task_p95": jitter(0.14), "task_p99": jitter(0.20),
            "ws_base": int(jitter(2 + work * 4)),
            "error_prob": 0.0, "disconnect_prob": 0.0, "sched_fail_prob": 0.0,
            "accept_rate": 0.85, "reject_rate": 0.10,
            "eval_success": 0, "eval_fail_prob": 0.0,
        }

    # Day 3: 중간 점검, 1차 평가 제출
    elif day_int == 3:
        spike_morning = gaussian(hour_frac, 0.067, 0.01) * 2.5
        eval_burst    = gaussian(hour_frac, 0.333, 0.015)
        eval_n        = int(eval_burst * 3)
        return {
            "n_chat":  max(0, int(jitter(10 + work * 28 + spike_morning * 10))),
            "n_sched": max(0, int(jitter(6  + work * 16 + spike_morning * 8))),
            "n_task":  max(0, int(jitter(25 + work * 65))),
            "chat_p50": jitter(clamp(1.5 + spike_morning * 0.3, 1.2, 3.0)),
            "chat_p95": jitter(clamp(2.5 + spike_morning * 0.8, 1.8, 4.5)),
            "chat_p99": jitter(clamp(3.0 + spike_morning * 1.0, 2.2, 5.5)),
            "sched_p50": jitter(clamp(2.0 + spike_morning * 0.5, 1.5, 4.0)),
            "sched_p95": jitter(clamp(3.2 + spike_morning * 1.0, 2.5, 4.8)),
            "sched_p99": jitter(clamp(3.8 + spike_morning * 1.2, 3.0, 5.5)),
            "task_p50": jitter(0.09), "task_p95": jitter(0.16), "task_p99": jitter(0.24),
            "ws_base": int(jitter(3 + work * 5 + spike_morning * 2)),
            "error_prob": 0.0, "disconnect_prob": 0.0, "sched_fail_prob": 0.0,
            "accept_rate": 0.84, "reject_rate": 0.11,
            "eval_success": eval_n, "eval_fail_prob": 0.0,
        }

    # Day 4: 위기 본격화 🚨
    elif day_int == 4:
        d = hour_frac
        spike_access  = gaussian(d, 0.067, 0.012) * 3.0
        spike_latency = gaussian(d, 0.133, 0.008) * 9.0
        spike_error   = gaussian(d, 0.200, 0.008) * 7.0
        spike_eval    = gaussian(d, 0.267, 0.008) * 5.0
        spike_night   = gaussian(d, 0.867, 0.015) * 11.0
        spike_total   = spike_access + spike_latency + spike_error + spike_night

        chat_p95  = clamp(2.0 + spike_latency * 0.9 + spike_night * 1.1, 1.5, 15)
        sched_p95 = clamp(2.0 + spike_latency * 1.1 + spike_night * 1.3, 1.5, 15)

        return {
            "n_chat":  max(0, int(jitter(15 + work * 35 + spike_total * 18))),
            "n_sched": max(0, int(jitter(8  + work * 18 + spike_total * 10))),
            "n_task":  max(0, int(jitter(30 + work * 70 + spike_total * 22))),
            "chat_p50": jitter(clamp(1.8 + spike_latency * 0.6 + spike_night * 0.9, 1.0, 12)),
            "chat_p95": jitter(chat_p95),
            "chat_p99": jitter(clamp(chat_p95 * 1.35, 2.0, 20)),
            "sched_p50": jitter(clamp(2.0 + spike_latency * 0.7 + spike_night * 1.1, 1.0, 12)),
            "sched_p95": jitter(sched_p95),
            "sched_p99": jitter(clamp(sched_p95 * 1.4, 2.5, 20)),
            "task_p50": jitter(clamp(0.09 + spike_total * 0.015, 0.05, 0.5)),
            "task_p95": jitter(clamp(0.16 + spike_total * 0.04,  0.10, 1.2)),
            "task_p99": jitter(clamp(0.24 + spike_total * 0.07,  0.15, 2.0)),
            "ws_base": clamp(int(jitter(5 + spike_total * 3 + spike_night * 6)), 0, 25),
            "error_prob":      clamp(spike_error * 0.07 + spike_night * 0.05, 0.0, 0.35),
            "disconnect_prob": clamp(spike_latency * 0.07 + spike_night * 0.05, 0.0, 0.45),
            "sched_fail_prob": clamp(spike_latency * 0.05 + spike_night * 0.07, 0.0, 0.35),
            "accept_rate": clamp(0.85 - spike_total * 0.04, 0.30, 0.85),
            "reject_rate": clamp(0.10 + spike_total * 0.03, 0.10, 0.55),
            "eval_success": int(gaussian(d, 0.267, 0.008) * 1.5),
            "eval_fail_prob": clamp(spike_eval * 0.12, 0.0, 0.9),
        }

    # Day 5: 대응 완료, 안정화
    elif day_int == 5:
        recovery   = math.exp(-hour_frac * 10)
        eval_burst = gaussian(hour_frac, 0.60, 0.02)
        return {
            "n_chat":  max(0, int(jitter(6  + work * 18))),
            "n_sched": max(0, int(jitter(3  + work * 10))),
            "n_task":  max(0, int(jitter(12 + work * 38))),
            "chat_p50": jitter(clamp(1.2 + recovery * 3.5, 1.0, 5.0)),
            "chat_p95": jitter(clamp(1.8 + recovery * 4.5, 1.5, 8.0)),
            "chat_p99": jitter(clamp(2.2 + recovery * 5.5, 1.8, 10.0)),
            "sched_p50": jitter(clamp(1.5 + recovery * 3.0, 1.0, 5.0)),
            "sched_p95": jitter(clamp(2.0 + recovery * 4.0, 1.5, 8.0)),
            "sched_p99": jitter(clamp(2.5 + recovery * 5.0, 2.0, 10.0)),
            "task_p50": jitter(clamp(0.07 + recovery * 0.10, 0.05, 0.3)),
            "task_p95": jitter(clamp(0.11 + recovery * 0.15, 0.08, 0.5)),
            "task_p99": jitter(clamp(0.16 + recovery * 0.20, 0.12, 0.8)),
            "ws_base": clamp(int(jitter(2 + work * 4)), 0, 10),
            "error_prob":      clamp(recovery * 0.04, 0.0, 0.08),
            "disconnect_prob": 0.0, "sched_fail_prob": 0.0,
            "accept_rate": clamp(0.88 + eval_burst * 0.04, 0.85, 0.95),
            "reject_rate": clamp(0.09 - eval_burst * 0.02, 0.05, 0.12),
            "eval_success": int(eval_burst * 4),
            "eval_fail_prob": 0.0,
        }

    # Day 6: 완전 정상, 마감 준비
    elif day_int == 6:
        sched_burst = gaussian(hour_frac, 0.40, 0.02) * 1.5
        return {
            "n_chat":  max(0, int(jitter(5  + work * 14))),
            "n_sched": max(0, int(jitter(4  + work * 12 + sched_burst * 6))),
            "n_task":  max(0, int(jitter(15 + work * 45))),
            "chat_p50": jitter(1.1), "chat_p95": jitter(1.6), "chat_p99": jitter(2.0),
            "sched_p50": jitter(1.3), "sched_p95": jitter(1.8), "sched_p99": jitter(2.2),
            "task_p50": jitter(0.06), "task_p95": jitter(0.10), "task_p99": jitter(0.14),
            "ws_base": int(jitter(2 + work * 3)),
            "error_prob": 0.0, "disconnect_prob": 0.0, "sched_fail_prob": 0.0,
            "accept_rate": 0.92, "reject_rate": 0.05,
            "eval_success": 0, "eval_fail_prob": 0.0,
        }

    # Day 7: 최종 마감, 평가 제출 폭증 ✅
    else:
        final_work = work * 1.3
        eval_burst = gaussian(hour_frac, 0.567, 0.018)
        load_bump  = gaussian(hour_frac, 0.567, 0.025) * 1.5
        return {
            "n_chat":  max(0, int(jitter(8  + final_work * 22 + load_bump * 5))),
            "n_sched": max(0, int(jitter(4  + final_work * 12))),
            "n_task":  max(0, int(jitter(20 + final_work * 55))),
            "chat_p50": jitter(clamp(1.2 + load_bump * 0.2, 1.0, 2.5)),
            "chat_p95": jitter(clamp(1.8 + load_bump * 0.5, 1.5, 3.5)),
            "chat_p99": jitter(clamp(2.2 + load_bump * 0.8, 1.8, 4.5)),
            "sched_p50": jitter(clamp(1.4 + load_bump * 0.2, 1.0, 2.5)),
            "sched_p95": jitter(clamp(2.0 + load_bump * 0.5, 1.5, 3.5)),
            "sched_p99": jitter(clamp(2.5 + load_bump * 0.8, 2.0, 4.5)),
            "task_p50": jitter(clamp(0.07 + load_bump * 0.01, 0.05, 0.2)),
            "task_p95": jitter(clamp(0.11 + load_bump * 0.03, 0.08, 0.4)),
            "task_p99": jitter(clamp(0.15 + load_bump * 0.05, 0.10, 0.6)),
            "ws_base": int(jitter(3 + final_work * 5 + load_bump * 2)),
            "error_prob": 0.0, "disconnect_prob": 0.0, "sched_fail_prob": 0.0,
            "accept_rate": 0.92, "reject_rate": 0.05,
            "eval_success": int(eval_burst * 6),
            "eval_fail_prob": 0.0,
        }

def compute_buckets(bounds, p50, p95, p99, n):
    n_eff = max(n, 100)
    result = []
    for b in bounds:
        if p99 <= p50:
            frac = 0.99
        elif b <= p50:
            frac = 0.5 * (b / p50) if p50 > 0 else 0.5
        elif b <= p95:
            frac = 0.5 + 0.45 * (b - p50) / max(p95 - p50, 0.001)
        elif b <= p99:
            frac = 0.95 + 0.04 * (b - p95) / max(p99 - p95, 0.001)
        else:
            frac = 0.99
        result.append(int(n_eff * clamp(frac, 0, 1)))
    result.append(n_eff)
    return result

def generate():
    lines = []
    total_ts = (DAYS * DAY) // STEP + 1
    print(f"총 {total_ts:,}개 타임스탬프 생성 중... (7일치)")

    c = {
        "chat_count": 0, "chat_sum": 0.0,
        "ext_count":  0, "ext_sum":  0.0,
        "sched_count": 0, "sched_sum": 0.0,
        "task_count":  0, "task_sum":  0.0,
        "disconnect": 0,
        "sched_fail_timeout": 0,
        "sched_accept": 0, "sched_reject": 0, "sched_modify": 0,
        "eval_success": 0, "eval_fail_dup": 0,
        "http_err_teams": 0, "http_err_tasks": 0, "http_err_ai_503": 0,
        "ws_total": {1: 0, 2: 0, 3: 0},
        "ws_msg":   {1: 0, 2: 0, 3: 0},
    }

    SLOW_BOUNDS = [0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0]
    FAST_BOUNDS = [0.05, 0.1, 0.25, 0.5, 1.0, 2.0]

    chat_bkts  = [0] * (len(SLOW_BOUNDS) + 1)
    ext_bkts   = [0] * (len(SLOW_BOUNDS) + 1)
    sched_bkts = [0] * (len(SLOW_BOUNDS) + 1)
    task_bkts  = [0] * (len(FAST_BOUNDS) + 1)
    http_bkts  = [0] * (len(SLOW_BOUNDS) + 1)

    def emit(name, value, extra_labels=""):
        lbl = f"{{{JOB},{extra_labels}}}" if extra_labels else f"{{{JOB}}}"
        lines.append(f"{name}{lbl} {float(value):.6f} {ts}")

    def add_bkts(bkts, bounds, p50, p95, p99, n):
        if n <= 0:
            return
        deltas = compute_buckets(bounds, p50, p95, p99, n)
        for i in range(len(bkts)):
            bkts[i] += deltas[i]

    for i, ts in enumerate(ts_range(START, NOW, STEP)):
        if i % 20000 == 0:
            pct = 100 * i // total_ts
            print(f"  {i:,}/{total_ts:,} ({pct}%)")

        p = get_params(ts)
        n_chat  = p["n_chat"]
        n_sched = p["n_sched"]
        n_task  = p["n_task"]

        c["chat_count"] += n_chat
        c["chat_sum"]   += n_chat * p["chat_p50"]
        c["ext_count"]  += n_chat
        c["ext_sum"]    += n_chat * p["chat_p50"] * 0.85
        c["sched_count"] += n_sched
        c["sched_sum"]   += n_sched * p["sched_p50"]
        c["task_count"]  += n_task
        c["task_sum"]    += n_task * p["task_p50"]

        if random.random() < p["disconnect_prob"]:
            c["disconnect"] += 1
        if n_sched > 0:
            if random.random() < p["sched_fail_prob"]:
                c["sched_fail_timeout"] += max(1, int(n_sched * p["sched_fail_prob"]))
            else:
                c["sched_accept"] += max(0, int(n_sched * p["accept_rate"]))
                c["sched_reject"] += max(0, int(n_sched * p["reject_rate"]))
                c["sched_modify"] += max(0, int(n_sched * 0.12))

        if random.random() < p["error_prob"]:
            c["http_err_teams"] += 1
            c["http_err_tasks"] += random.randint(0, 1)
        if random.random() < p["error_prob"] * 0.7:
            c["http_err_ai_503"] += 1

        c["eval_success"] += p["eval_success"]
        if random.random() < p["eval_fail_prob"]:
            c["eval_fail_dup"] += 1

        for room in [1, 2, 3]:
            ws_share = max(p["ws_base"] // 3, 0)
            if ws_share > 0:
                c["ws_total"][room] += random.randint(0, 1)
                c["ws_msg"][room]   += random.randint(0, 2)

        add_bkts(chat_bkts,  SLOW_BOUNDS, p["chat_p50"],        p["chat_p95"],        p["chat_p99"],        n_chat)
        add_bkts(ext_bkts,   SLOW_BOUNDS, p["chat_p50"] * 0.85, p["chat_p95"] * 0.85, p["chat_p99"] * 0.85, n_chat)
        add_bkts(sched_bkts, SLOW_BOUNDS, p["sched_p50"],       p["sched_p95"],       p["sched_p99"],       n_sched)
        add_bkts(task_bkts,  FAST_BOUNDS, p["task_p50"],        p["task_p95"],        p["task_p99"],        n_task)
        n_http   = n_chat + n_sched + n_task
        http_p95 = (p["chat_p95"] * n_chat + p["sched_p95"] * n_sched + p["task_p95"] * n_task) / max(n_http, 1)
        add_bkts(http_bkts, SLOW_BOUNDS, http_p95 * 0.55, http_p95, http_p95 * 1.3, n_http)

        for bi, b in enumerate(SLOW_BOUNDS):
            emit("ai_chat_summary_latency_seconds_bucket", chat_bkts[bi], f'le="{b}"')
        emit("ai_chat_summary_latency_seconds_bucket", chat_bkts[-1], 'le="+Inf"')
        emit("ai_chat_summary_latency_seconds_count", c["chat_count"])
        emit("ai_chat_summary_latency_seconds_sum",   c["chat_sum"])

        for bi, b in enumerate(SLOW_BOUNDS):
            emit("ai_chat_external_api_latency_seconds_bucket", ext_bkts[bi], f'le="{b}"')
        emit("ai_chat_external_api_latency_seconds_bucket", ext_bkts[-1], 'le="+Inf"')
        emit("ai_chat_external_api_latency_seconds_count", c["ext_count"])
        emit("ai_chat_external_api_latency_seconds_sum",   c["ext_sum"])

        for bi, b in enumerate(SLOW_BOUNDS):
            emit("ai_schedule_latency_seconds_bucket", sched_bkts[bi], f'le="{b}"')
        emit("ai_schedule_latency_seconds_bucket", sched_bkts[-1], 'le="+Inf"')
        emit("ai_schedule_latency_seconds_count", c["sched_count"])
        emit("ai_schedule_latency_seconds_sum",   c["sched_sum"])

        emit("ai_schedule_failure_total",     c["sched_fail_timeout"], 'error_type="timeout"')
        emit("ai_schedule_accept_total",      c["sched_accept"])
        emit("ai_schedule_reject_total",      c["sched_reject"])
        emit("ai_schedule_task_modify_total", c["sched_modify"])

        for bi, b in enumerate(FAST_BOUNDS):
            emit("task_list_mine_latency_seconds_bucket", task_bkts[bi], f'le="{b}"')
        emit("task_list_mine_latency_seconds_bucket", task_bkts[-1], 'le="+Inf"')
        emit("task_list_mine_latency_seconds_count", c["task_count"])
        emit("task_list_mine_latency_seconds_sum",   c["task_sum"])
        emit("task_list_mine_requests_total",        c["task_count"])

        for bi, b in enumerate(SLOW_BOUNDS):
            emit("http_request_duration_seconds_bucket", http_bkts[bi], f'le="{b}"')
        emit("http_request_duration_seconds_bucket", http_bkts[-1], 'le="+Inf"')

        emit("ai_chat_client_disconnect_total", c["disconnect"])

        emit("http_requests_errors_total", c["http_err_teams"],  'endpoint="/api/teams",status_code="500",error_type="db_error"')
        emit("http_requests_errors_total", c["http_err_tasks"],  'endpoint="/api/tasks",status_code="500",error_type="db_error"')
        emit("http_requests_errors_total", c["http_err_ai_503"], 'endpoint="/api/ai-sessions",status_code="503",error_type="upstream_timeout"')

        emit("evaluation_submit_total", c["eval_success"],  'status="success",error_type=""')
        emit("evaluation_submit_total", c["eval_fail_dup"], 'status="failure",error_type="duplicate"')

        for room in [1, 2, 3]:
            ws_now = clamp(p["ws_base"] // 3 + random.randint(-1, 1), 0, 12)
            emit("ws_chat_active_connections",      ws_now,              f'room_id="{room}"')
            emit("ws_chat_connections_total",       c["ws_total"][room], f'room_id="{room}"')
            emit("ws_chat_messages_received_total", c["ws_msg"][room],   f'room_id="{room}"')

    lines.append("# EOF")
    return lines

if __name__ == "__main__":
    print("=== TeamTeam 7일치 가짜 데이터 생성 ===")
    lines = generate()

    with open(OUTPUT_FILE, "w") as f:
        f.write("\n".join(lines))

    size_mb = os.path.getsize(OUTPUT_FILE) / 1_000_000
    print(f"\n✅ 완료: {OUTPUT_FILE}")
    print(f"   크기: {size_mb:.1f} MB / 라인 수: {len(lines):,}")
    print()
    print("다음 단계:")
    print('  docker run --rm -v "$(pwd):/data" prom/prometheus:v2.52.0 \\')
    print("    promtool tsdb create-blocks-from openmetrics \\")
    print("    /data/teamteam_metrics.openmetrics /data/tsdb_blocks_new")
    print()
    print("  docker restart teamteam_backend-prometheus-1")