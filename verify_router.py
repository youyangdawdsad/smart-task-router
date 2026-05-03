#!/usr/bin/env python3
"""
Smart Task Router - Core Logic Verification
Tests: TaskProfiler, DeviceCapability, RoutingRules, RoutingLog, LoadBalancer, FailoverMigration
Target: 70+ assertions covering all modules
"""

import time
import json
from datetime import datetime, timezone, timedelta


class TaskProfiler:
    """Analyze user tasks, generate structured TaskProfile"""
    KEYWORD_TOOL_MAP = {
        "短信": "sms", "消息": "sms", "text message": "sms",
        "打电话": "call", "来电": "call", "通话": "call", "call": "call",
        "拍照": "camera", "相机": "camera", "camera": "camera",
        "定位": "location", "在哪": "location", "位置": "location", "地址": "location",
        "日历": "calendar", "日程": "calendar", "会议": "calendar",
        "闹钟": "alarm", "定时提醒": "alarm",
        "播放": "media", "暂停": "media", "音乐": "media", "音量": "media",
        "通知": "notification", "推送": "notification",
        "代码": "code", "脚本": "code", "运行": "code", "python": "code",
        "IDE": "ide", "编辑器": "ide", "开发环境": "ide",
        "文件": "file", "保存": "file", "写入": "file", "导出": "file",
        "浏览器": "browser", "网页": "browser", "打开网站": "browser",
        "PPT": "office", "Word": "office", "Excel": "office",
        "报告": "text", "总结": "text", "文章": "text",
        "搜索": "search", "查找": "search", "search": "search",
    }
    PHONE_TOOLS = {"sms", "call", "camera", "location", "alarm", "media", "notification"}
    PC_TOOLS = {"code", "ide", "office"}
    SPLITTABLE_KEYWORDS = ["然后", "接着", "再", "并且", "同时"]
    URGENCY_KEYWORDS = ["马上", "立刻", "赶紧", "急"]

    def analyze(self, task_text):
        tools = set()
        text_lower = task_text.lower()
        for kw, tool in self.KEYWORD_TOOL_MAP.items():
            if kw.lower() in text_lower:
                tools.add(tool)
        tools_list = sorted(tools)
        has_phone = bool(tools & self.PHONE_TOOLS)
        has_pc = bool(tools & self.PC_TOOLS)
        if has_phone and not has_pc:
            environment = "phone-only"
        elif has_pc and not has_phone:
            environment = "pc-only"
        else:
            environment = "any"
        if len(tools) <= 1:
            complexity = "light"
        elif len(tools) <= 3:
            complexity = "medium"
        else:
            complexity = "heavy"
        splittable = False
        if has_phone and has_pc:
            splittable = True
        if any(kw in task_text for kw in self.SPLITTABLE_KEYWORDS) and len(tools) > 1:
            splittable = True
        urgency = "urgent" if any(kw in task_text for kw in self.URGENCY_KEYWORDS) else "normal"
        if "alarm" in tools or "call" in tools:
            urgency = "urgent"
        duration_map = {"light": 10, "medium": 30, "heavy": 120}
        estimated_duration = duration_map.get(complexity, 30)
        now = datetime.now()
        task_id = "T-{}-{}".format(now.strftime("%Y%m%d"), now.strftime("%H%M%S"))
        sub_tasks = []
        if splittable:
            idx = 1
            for tool in tools_list:
                st_env = "phone-only" if tool in self.PHONE_TOOLS else "pc-only" if tool in self.PC_TOOLS else "any"
                sub_tasks.append({"id": "ST-{}".format(idx), "tools": [tool], "environment": st_env})
                idx += 1
        return {
            "task_id": task_id,
            "original_text": task_text,
            "tools_required": tools_list,
            "complexity": complexity,
            "environment": environment,
            "splittable": splittable,
            "urgency": urgency,
            "estimated_duration_seconds": estimated_duration,
            "sub_tasks": sub_tasks,
        }


class DeviceCapability:
    PHONE_CAPS = {
        "sms": 0.95, "call": 0.90, "camera": 0.95, "location": 0.95,
        "calendar": 0.80, "alarm": 0.90, "media": 0.85, "notification": 0.80,
        "contacts": 0.85, "search": 0.60, "file": 0.40, "screenshot": 0.90,
    }
    PC_CAPS = {
        "code": 0.95, "ide": 0.95, "file": 0.90, "browser": 0.85,
        "text": 0.85, "office": 0.90, "search": 0.80, "notification": 0.70,
    }

    @staticmethod
    def create_device(device_id, device_type, online=True, load_status="idle",
                      current_tasks=0, heartbeat_latency_ms=None):
        caps = DeviceCapability.PHONE_CAPS if device_type == "phone" else DeviceCapability.PC_CAPS
        return {
            "device_id": device_id,
            "device_type": device_type,
            "online": online,
            "load_status": load_status,
            "current_tasks": current_tasks,
            "max_concurrent": 3,
            "capabilities": list(caps.keys()),
            "capability_scores": dict(caps),
            "heartbeat_latency_ms": heartbeat_latency_ms,
        }

    @staticmethod
    def compute_coverage(device, tools_required):
        if not tools_required:
            return 1.0
        cap_set = set(device["capabilities"])
        covered = len([t for t in tools_required if t in cap_set])
        return covered / len(tools_required)

    @staticmethod
    def compute_capability_score(device, tools_required):
        if not tools_required:
            return 0.0
        scores = device["capability_scores"]
        total = sum(scores.get(t, 0) for t in tools_required)
        return total / len(tools_required)


class RoutingRules:
    HARD_RULES = {
        "sms": "phone", "call": "phone", "camera": "phone",
        "location": "phone", "alarm": "phone", "media": "phone",
        "screenshot": "phone",
        "code": "pc", "ide": "pc", "office": "pc",
    }
    HIGH_RISK_OPS = {"payment", "refund", "delete_irreversible", "cancel_order"}
    MIN_ROUTE_SCORE = 0.2  # 低于此分数认为无合适设备

    @staticmethod
    def check_hard_rules(tools_required):
        for tool in tools_required:
            if tool in RoutingRules.HARD_RULES:
                return RoutingRules.HARD_RULES[tool]
        return None

    @staticmethod
    def compute_proximity(device):
        latency = device.get("heartbeat_latency_ms")
        if not device["online"]:
            return 0.0
        if latency is None:
            return 1.0
        if latency < 2000:
            return 1.0
        elif latency < 5000:
            return 0.8
        else:
            return 0.5

    @staticmethod
    def compute_route_score(task_profile, device):
        tools = task_profile["tools_required"]
        cap_match = DeviceCapability.compute_capability_score(device, tools)
        load_map = {"idle": 1.0, "busy": 0.3, "offline": 0.0}
        load_factor = load_map.get(device["load_status"], 0.0)
        proximity = RoutingRules.compute_proximity(device)
        return cap_match * 0.5 + load_factor * 0.3 + proximity * 0.2

    @staticmethod
    def route(task_profile, devices):
        candidates = [d for d in devices if d["online"]]
        if not candidates:
            return {"status": "all_offline"}
        hard_target = RoutingRules.check_hard_rules(task_profile["tools_required"])
        if hard_target:
            for d in candidates:
                if d["device_type"] == hard_target:
                    return {
                        "target": d["device_id"],
                        "method": "hard_rule",
                        "reason": "hard_rule: {}->{}".format(
                            task_profile["tools_required"][0], hard_target
                        ),
                    }
        scores = []
        for device in candidates:
            score = RoutingRules.compute_route_score(task_profile, device)
            scores.append((device["device_id"], round(score, 4)))
        scores.sort(key=lambda x: x[1], reverse=True)
        best = scores[0]
        if best[1] < RoutingRules.MIN_ROUTE_SCORE:
            return {"status": "no_suitable_device", "candidates": scores}
        return {"target": best[0], "method": "soft_rule", "score": best[1], "all_scores": scores}


class RoutingLog:
    """路由决策日志，记录每次路由决策的完整信息"""
    MAX_LOG_SIZE = 100

    def __init__(self):
        self.logs = []

    def log_decision(self, task_profile, decision):
        entry = {
            "log_id": "ROUTE-{}-{}".format(
                datetime.now().strftime("%Y%m%d"),
                len(self.logs) + 1,
            ),
            "task_id": task_profile.get("task_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "input": {
                "tools_required": task_profile.get("tools_required", []),
                "complexity": task_profile.get("complexity", "unknown"),
                "environment": task_profile.get("environment", "unknown"),
            },
            "decision": decision,
        }
        self.logs.append(entry)
        if len(self.logs) > self.MAX_LOG_SIZE:
            self.logs = self.logs[-self.MAX_LOG_SIZE:]
        return entry

    def get_recent(self, n=10):
        return self.logs[-n:]

    def clear(self):
        self.logs.clear()


class LoadBalancer:
    def __init__(self):
        self.heartbeat_interval = 30
        self.heartbeat_timeout = 10
        self.offline_threshold = 2
        self.max_queue_size = 10
        self.wait_timeout = 60

    def check_heartbeat(self, device, consecutive_failures):
        if device["online"]:
            return {"online": True, "consecutive_failures": 0, "status": device["load_status"]}
        else:
            new_failures = consecutive_failures + 1
            if new_failures >= self.offline_threshold:
                return {"online": False, "consecutive_failures": new_failures, "status": "offline"}
            return {"online": True, "consecutive_failures": new_failures, "status": device["load_status"]}

    def find_idle_device(self, devices, tools_required):
        for device in devices:
            if device["online"] and device["load_status"] == "idle":
                coverage = DeviceCapability.compute_coverage(device, tools_required)
                if coverage > 0:
                    return device
        return None

    def should_enqueue(self, task_urgency, target_device):
        if task_urgency == "urgent":
            return False
        if target_device and target_device["load_status"] == "idle":
            return False
        return True

    def compute_queue_priority(self, task_urgency):
        return 0 if task_urgency == "urgent" else 1


class FailoverMigration:
    MAX_L1_RETRIES = 3
    MAX_L2_MIGRATIONS = 2
    MAX_TOTAL_MIGRATIONS = 6
    TOOL_ALTERNATIVES = {
        "web_search": ["url_fetch"],
        "write_file": ["append_file"],
        "read_file": ["list_files"],
        "tool_search": [],
    }
    HIGH_RISK_OPS = {"payment", "refund", "delete_irreversible", "cancel_order"}

    def __init__(self):
        self.migration_log = []
        self.migration_count = 0
        self.l1_count = 0
        self.l2_count = 0

    def detect_failure(self, result):
        if result is None:
            return True, "result is None"
        if isinstance(result, dict):
            if result.get("error"):
                return True, result["error"]
            if result.get("timeout"):
                return True, "timeout"
        return False, ""

    def get_alternatives(self, failed_tool):
        return self.TOOL_ALTERNATIVES.get(failed_tool, [])

    def level1_same_device(self, failed_tool):
        if self.l1_count >= self.MAX_L1_RETRIES:
            return {"level": 1, "alternative": None, "retry": False, "reason": "L1 max retries exceeded"}
        alternatives = self.get_alternatives(failed_tool)
        if alternatives:
            self.l1_count += 1
            self.migration_count += 1
            return {"level": 1, "alternative": alternatives[0], "retry": True}
        return {"level": 1, "alternative": None, "retry": False}

    def level2_migrate_device(self, task_profile, current_device, all_devices):
        if self.l2_count >= self.MAX_L2_MIGRATIONS:
            return {"level": 2, "migrated": False, "reason": "L2 max migrations exceeded"}
        if self.migration_count >= self.MAX_TOTAL_MIGRATIONS:
            return {"level": 2, "migrated": False, "reason": "total migration limit exceeded"}
        other_devices = [
            d for d in all_devices
            if d["device_id"] != current_device["device_id"] and d["online"]
        ]
        if not other_devices:
            return {"level": 2, "migrated": False, "reason": "no other online devices"}
        result = RoutingRules.route(task_profile, other_devices)
        if result.get("status") == "all_offline":
            return {"level": 2, "migrated": False, "reason": "all devices offline"}
        self.l2_count += 1
        self.migration_count += 1
        return {
            "level": 2, "migrated": True,
            "target_device": result["target"],
            "reason": "migrate from {} to {}".format(current_device["device_id"], result["target"]),
        }

    def level3_human_fallback(self, completed_parts, failed_parts):
        output = {"completed": completed_parts, "pending_human": failed_parts}
        self.migration_log.append({
            "level": 3,
            "completed_count": len(completed_parts),
            "pending_count": len(failed_parts),
        })
        return output

    def is_high_risk(self, operation_type):
        return operation_type in self.HIGH_RISK_OPS

    def get_migration_count(self):
        return self.migration_count


# ============================================================
#  Test Suite
# ============================================================

def run_tests():
    passed = 0
    failed = 0
    total = 0

    def check_eq(name, actual, expected):
        nonlocal passed, failed, total
        total += 1
        if actual == expected:
            passed += 1
            print("  PASS: {}".format(name))
        else:
            failed += 1
            print("  FAIL: {} -- expected {!r}, got {!r}".format(name, expected, actual))

    def check_true(name, condition):
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print("  PASS: {}".format(name))
        else:
            failed += 1
            print("  FAIL: {} -- condition is False".format(name))

    def check_in(name, item, collection):
        nonlocal passed, failed, total
        total += 1
        if item in collection:
            passed += 1
            print("  PASS: {}".format(name))
        else:
            failed += 1
            print("  FAIL: {} -- {!r} not in {!r}".format(name, item, collection))

    profiler = TaskProfiler()
    phone = DeviceCapability.create_device("phone-01", "phone")
    pc = DeviceCapability.create_device("pc-01", "pc")
    phone_busy = DeviceCapability.create_device("phone-02", "phone", load_status="busy", current_tasks=3)
    phone_offline = DeviceCapability.create_device("phone-03", "phone", online=False)
    phone_slow = DeviceCapability.create_device("phone-04", "phone", heartbeat_latency_ms=6000)
    phone_medium = DeviceCapability.create_device("phone-05", "phone", heartbeat_latency_ms=3500)

    # -- Module 1: TaskProfiler --
    print("\n[Module 1] TaskProfiler")

    p1 = profiler.analyze("帮我发条短信给妈妈")
    check_eq("sms tool detected", p1["tools_required"], ["sms"])
    check_eq("phone-only environment", p1["environment"], "phone-only")
    check_eq("light complexity", p1["complexity"], "light")
    check_true("has task_id", p1["task_id"].startswith("T-"))
    check_eq("normal urgency", p1["urgency"], "normal")

    p2 = profiler.analyze("帮我写一段Python代码然后发短信通知我")
    check_true("cross-device splittable", p2["splittable"])
    check_eq("any environment", p2["environment"], "any")
    check_true("has sub_tasks", len(p2["sub_tasks"]) >= 2)

    p3 = profiler.analyze("马上打电话给老板")
    check_eq("urgent urgency", p3["urgency"], "urgent")
    check_in("call tool detected", "call", p3["tools_required"])

    p4 = profiler.analyze("帮我写代码做个PPT再拍张照然后发短信通知再搜索资料")
    check_eq("heavy complexity", p4["complexity"], "heavy")
    check_true("heavy task splittable", p4["splittable"])

    p5 = profiler.analyze("设个明天早上7点的闹钟")
    check_in("alarm tool detected", "alarm", p5["tools_required"])
    check_eq("alarm urgent urgency", p5["urgency"], "urgent")

    # -- Module 2: DeviceCapability --
    print("\n[Module 2] DeviceCapability")

    cov1 = DeviceCapability.compute_coverage(phone, ["sms", "call", "camera"])
    check_eq("phone full comms coverage", cov1, 1.0)

    cov2 = DeviceCapability.compute_coverage(pc, ["sms", "call"])
    check_eq("pc cannot cover sms/call", cov2, 0.0)

    cov3 = DeviceCapability.compute_coverage(pc, ["code", "office"])
    check_eq("pc full dev/office coverage", cov3, 1.0)

    score1 = DeviceCapability.compute_capability_score(phone, ["sms", "camera"])
    check_true("phone comms score > 0.9", score1 > 0.9)

    score2 = DeviceCapability.compute_capability_score(pc, ["code", "ide"])
    check_true("pc dev score > 0.9", score2 > 0.9)

    # -- Module 3: RoutingRules --
    print("\n[Module 3] RoutingRules")

    check_eq("sms hard rule -> phone", RoutingRules.check_hard_rules(["sms"]), "phone")
    check_eq("code hard rule -> pc", RoutingRules.check_hard_rules(["code"]), "pc")
    check_eq("calendar no hard rule", RoutingRules.check_hard_rules(["calendar"]), None)

    sms_profile = profiler.analyze("发短信")
    route1 = RoutingRules.route(sms_profile, [phone, pc])
    check_eq("sms routes to phone", route1["target"], "phone-01")
    check_eq("sms via hard_rule", route1["method"], "hard_rule")

    code_profile = profiler.analyze("写代码")
    route2 = RoutingRules.route(code_profile, [phone, pc])
    check_eq("code routes to pc", route2["target"], "pc-01")
    check_eq("code via hard_rule", route2["method"], "hard_rule")

    search_profile = profiler.analyze("搜索")
    route3 = RoutingRules.route(search_profile, [phone, pc])
    check_eq("search routes to pc (soft)", route3["target"], "pc-01")
    check_eq("search via soft_rule", route3["method"], "soft_rule")

    route4 = RoutingRules.route(sms_profile, [phone_offline])
    check_eq("all offline returns status", route4["status"], "all_offline")

    proximity_normal = RoutingRules.compute_proximity(phone)
    proximity_slow = RoutingRules.compute_proximity(phone_slow)
    proximity_medium = RoutingRules.compute_proximity(phone_medium)
    check_eq("normal latency proximity=1.0", proximity_normal, 1.0)
    check_eq("high latency proximity=0.5", proximity_slow, 0.5)
    check_eq("medium latency proximity=0.8", proximity_medium, 0.8)

    # -- Module 4: LoadBalancer --
    print("\n[Module 4] LoadBalancer")

    lb = LoadBalancer()

    hb1 = lb.check_heartbeat(phone, 0)
    check_true("online device heartbeat ok", hb1["online"])

    hb2 = lb.check_heartbeat(phone_offline, 0)
    check_true("offline 1x still online (grace)", hb2["online"])

    hb3 = lb.check_heartbeat(phone_offline, 2)
    check_true("offline 2x marked offline", not hb3["online"])

    idle_dev = lb.find_idle_device([phone_busy, phone], ["sms"])
    check_eq("idle device preferred", idle_dev["device_id"], "phone-01")

    check_true("urgent not enqueued", not lb.should_enqueue("urgent", phone_busy))
    check_true("normal+busy enqueued", lb.should_enqueue("normal", phone_busy))
    check_eq("urgent priority=0", lb.compute_queue_priority("urgent"), 0)
    check_eq("normal priority=1", lb.compute_queue_priority("normal"), 1)

    # -- Module 5: FailoverMigration --
    print("\n[Module 5] FailoverMigration")

    fm = FailoverMigration()

    is_fail1, _ = fm.detect_failure(None)
    check_true("None is failure", is_fail1)

    is_fail2, _ = fm.detect_failure({"error": "timeout"})
    check_true("error dict is failure", is_fail2)

    is_fail3, _ = fm.detect_failure({"data": "ok"})
    check_true("ok dict not failure", not is_fail3)

    alt1 = fm.get_alternatives("web_search")
    check_eq("web_search has alt", alt1, ["url_fetch"])

    alt2 = fm.get_alternatives("unknown_tool")
    check_eq("unknown tool no alt", alt2, [])

    l1 = fm.level1_same_device("web_search")
    check_eq("L1 level", l1["level"], 1)
    check_true("L1 retry ok", l1["retry"])

    other_phone = DeviceCapability.create_device("phone-06", "phone")
    task_p = profiler.analyze("搜索")
    l2 = fm.level2_migrate_device(task_p, phone_offline, [phone_offline, other_phone])
    check_eq("L2 level", l2["level"], 2)
    check_true("L2 migrated ok", l2["migrated"])

    l3 = fm.level3_human_fallback(["subtask1"], ["subtask2"])
    check_eq("L3 completed", l3["completed"], ["subtask1"])
    check_eq("L3 pending", l3["pending_human"], ["subtask2"])

    check_true("payment is high risk", fm.is_high_risk("payment"))
    check_true("send_sms not high risk", not fm.is_high_risk("send_sms"))

    # L2 migration limit
    fm2 = FailoverMigration()
    fm2.l2_count = FailoverMigration.MAX_L2_MIGRATIONS
    l2_limit = fm2.level2_migrate_device(task_p, phone_offline, [phone_offline, other_phone])
    check_true("L2 limit blocks migration", not l2_limit["migrated"])

    # L1 retry limit
    fm3 = FailoverMigration()
    fm3.l1_count = FailoverMigration.MAX_L1_RETRIES
    l1_limit = fm3.level1_same_device("web_search")
    check_true("L1 limit blocks retry", not l1_limit["retry"])

    # -- Module 6: RoutingLog --
    print("\n[Module 6] RoutingLog")

    rlog = RoutingLog()
    decision1 = {"target": "phone-01", "method": "hard_rule"}
    entry1 = rlog.log_decision(profiler.analyze("发短信"), decision1)
    check_true("log has log_id", entry1["log_id"].startswith("ROUTE-"))
    check_true("log has task_id", entry1["task_id"].startswith("T-"))
    check_eq("log recent count", len(rlog.get_recent()), 1)

    # Log overflow
    for i in range(105):
        rlog.log_decision(profiler.analyze("搜索"), {"target": "pc-01"})
    check_true("log capped at 100", len(rlog.logs) <= 100)

    rlog.clear()
    check_eq("log cleared", len(rlog.logs), 0)

    # -- Module 7: Edge Cases --
    print("\n[Module 7] Edge Cases")

    # Empty tools -> any environment, light complexity
    empty_profile = profiler.analyze("你好")
    check_eq("empty tools = any env", empty_profile["environment"], "any")
    check_eq("empty tools = light", empty_profile["complexity"], "light")
    check_eq("empty tools no sub_tasks", empty_profile["sub_tasks"], [])

        # Score threshold: device with very low capability match -> no_suitable_device
    # search on phone: cap=0.60, load=busy(0.3), proximity=1.0 → 0.60*0.5+0.3*0.3+1.0*0.2 = 0.59
    # Need a device with extremely low match. Use a phone for "code" task:
    # phone has no "code" cap → cap_match=0, load=busy → 0*0.5+0.3*0.3+1.0*0.2 = 0.29
    # Still above 0.2. Use offline-ish: phone with high latency
    phone_very_slow = DeviceCapability.create_device("phone-vs", "phone", load_status="busy", heartbeat_latency_ms=8000)
    code_p = profiler.analyze("写代码")
    route_low = RoutingRules.route(code_p, [phone_very_slow])
    # phone has no code capability → cap=0, busy=0.3, latency>=5s→0.2 → 0+0.09+0.04=0.13 < 0.2
    check_eq("low score returns no_suitable_device", route_low.get("status"), "no_suitable_device")

    # High risk operation detection
    check_true("refund is high risk", fm.is_high_risk("refund"))
    check_true("delete_irreversible is high risk", fm.is_high_risk("delete_irreversible"))
    check_true("normal op not high risk", not fm.is_high_risk("read_file"))

        # Multiple hard rules: tools sorted alphabetically, first match wins
    # "发短信写代码" → tools_required = ["code", "sms"] (sorted)
    # check_hard_rules iterates in order, "code" matches first → pc
    multi_profile = profiler.analyze("发短信写代码")
    route_multi = RoutingRules.route(multi_profile, [phone, pc])
    check_eq("multi hard rule code wins (alphabetical)", route_multi["target"], "pc-01")

    # Proximity with no latency data
    no_lat = DeviceCapability.create_device("phone-nolat", "phone", heartbeat_latency_ms=None)
    check_eq("no latency proximity=1.0", RoutingRules.compute_proximity(no_lat), 1.0)

    # Offline device proximity
    off_dev = DeviceCapability.create_device("phone-off", "phone", online=False)
    check_eq("offline proximity=0.0", RoutingRules.compute_proximity(off_dev), 0.0)

    # FailoverMigration: detect timeout
    is_timeout, _ = fm.detect_failure({"timeout": True})
    check_true("timeout detected", is_timeout)

    # FailoverMigration: non-failure
    is_ok, _ = fm.detect_failure({"data": "hello"})
    check_true("normal result not failure", not is_ok)

    # Level2 with no other devices
    l2_no_other = fm.level2_migrate_device(task_p, phone, [phone])
    check_true("L2 no other devices", not l2_no_other["migrated"])

    # -- Summary --
    print("\n" + "=" * 50)
    print("Results: {}/{} passed, {} failed".format(passed, total, failed))
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("{} tests FAILED".format(failed))
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
