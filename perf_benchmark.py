#!/usr/bin/env python3
"""SIE v3.3.1 Performance Benchmark
Tests:
  1. NLU single recognition latency (target < 50ms)
  2. Cache hit routing latency (target < 10ms)
  3. Batch learning processing time (3 unknown intents)
"""

import os
import sys
import json
import time
import statistics

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from sie_self_evolve import SelfEvolvingNLU

# ── Helpers ──
passed = 0
failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} {detail}")

def bench(name, func, iterations=100):
    """Run func multiple times, return median latency in ms."""
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        func()
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)
    median = statistics.median(times)
    p95 = sorted(times)[int(len(times) * 0.95)]
    return median, p95, times

# ── Init ──
print("=" * 60)
print("SIE v3.3.1 Performance Benchmark")
print("=" * 60)

nlu = SelfEvolvingNLU()

# ── Test 1: NLU Single Recognition Latency ──
print("\n[1] NLU 单次识别耗时 (目标 < 50ms)")

test_inputs = [
    "帮我发条短信给妈妈",
    "明天天气怎么样",
    "打开客厅的灯",
    "写一个Python脚本",
    "帮我做个PPT",
    "播放音乐",
    "明天早上7点叫我",
    "今天有什么安排",
    "搜一下人工智能",
    "帮我订个外卖",
]

# Warm up
for inp in test_inputs:
    nlu.parse(inp)

# Benchmark each input
all_medians = []
all_p95s = []
for inp in test_inputs:
    median, p95, _ = bench(f"parse('{inp[:8]}...')", lambda i=inp: nlu.parse(i), iterations=200)
    all_medians.append(median)
    all_p95s.append(p95)

overall_median = statistics.median(all_medians)
overall_p95 = statistics.median(all_p95s)
worst_median = max(all_medians)

print(f"\n  各输入中位数: {[f'{m:.2f}ms' for m in all_medians]}")
print(f"  整体中位数: {overall_median:.2f}ms")
print(f"  整体 P95: {overall_p95:.2f}ms")
print(f"  最慢单项中位数: {worst_median:.2f}ms")

check("NLU 中位数 < 50ms", overall_median < 50, f"实际: {overall_median:.2f}ms")
check("NLU P95 < 100ms", overall_p95 < 100, f"实际: {overall_p95:.2f}ms")
check("NLU 最慢单项 < 50ms", worst_median < 50, f"实际: {worst_median:.2f}ms")

# ── Test 2: Cache Hit Routing Latency ──
print("\n[2] 缓存命中路由耗时 (目标 < 10ms)")

# First call to populate cache
for inp in test_inputs:
    nlu.parse(inp)

# Benchmark cache hits
cache_medians = []
for inp in test_inputs:
    median, p95, _ = bench(f"cached('{inp[:8]}...')", lambda i=inp: nlu.parse(i), iterations=500)
    cache_medians.append(median)

cache_median = statistics.median(cache_medians)
cache_worst = max(cache_medians)

print(f"\n  缓存命中中位数: {cache_median:.2f}ms")
print(f"  缓存命中最慢: {cache_worst:.2f}ms")

check("缓存命中中位数 < 10ms", cache_median < 10, f"实际: {cache_median:.2f}ms")
check("缓存命中最慢 < 20ms", cache_worst < 20, f"实际: {cache_worst:.2f}ms")

# ── Test 3: Batch Learning Processing Time ──
print("\n[3] 批量学习处理时间 (攒满 3 个未知意图)")

unknown_inputs = [
    "帮我养一只猫",
    "给我变个魔术",
    "帮我算一下这道高等数学题",
]

# Reset batch buffer
nlu.unknown_handler._batch_buffer.clear()

t_start = time.perf_counter()

# Simulate 3 unknown inputs accumulating
learn_requests = []
for inp in unknown_inputs:
    result = nlu.parse(inp)
    if result.get("intent") == "unknown" and result.get("learn_request"):
        learn_requests.append(result["learn_request"])

# Check if batch threshold reached
batch_ready = nlu.unknown_handler.should_batch_send()

t_end = time.perf_counter()
batch_time_ms = (t_end - t_start) * 1000

print(f"\n  未知意图数: {len(unknown_inputs)}")
print(f"  learn_request 数: {len(learn_requests)}")
print(f"  批量缓冲区大小: {len(nlu.unknown_handler._batch_buffer)}")
print(f"  阈值: {nlu.unknown_handler.threshold}")
print(f"  批量就绪: {batch_ready}")
print(f"  总处理时间: {batch_time_ms:.2f}ms")

check("生成了 learn_request", len(learn_requests) == 3, f"实际: {len(learn_requests)}")
check("批量缓冲区达到阈值", batch_ready)
check("批量处理时间 < 500ms", batch_time_ms < 500, f"实际: {batch_time_ms:.2f}ms")

# ── Summary ──
print("\n" + "=" * 60)
print(f"Results: {passed}/{passed + failed} passed, {failed} failed")
if failed == 0:
    print("ALL PERFORMANCE BENCHMARKS PASSED")
else:
    print("SOME BENCHMARKS FAILED")
print("=" * 60)

sys.exit(0 if failed == 0 else 1)
