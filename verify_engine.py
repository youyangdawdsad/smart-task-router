#!/usr/bin/env python3
"""
Smart Invocation Engine (SIE) - Core Logic Verification
Tests: TaskProfiler, DeviceCapability, RoutingRules, RoutingLog, LoadBalancer,
       FailoverMigration, InvocationIndicator, CrashDetector, DualLink
Target: 95+ assertions covering all 10 modules
"""

import time
import json
from datetime import datetime, timezone, timedelta


# ============================================================
#  Module 1: TaskProfiler (unchanged from v1.2)
# ============================================================

class TaskProfiler:
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
            "task_id": task_id, "original_text": task_text,
            "tools_required": tools_list, "complexity": complexity,
            "environment": environment, "splittable": splittable,
            "urgency": urgency, "estimated_duration_seconds": estimated_duration,
            "sub_tasks": sub_tasks,
        }


# ============================================================
#  Module 2: DeviceCapability (unchanged from v1.2)
# ============================================================

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
            "device_id": device_id, "device_type": device_type,
            "online": online, "load_status": load_status,
            "current_tasks": current_tasks, "max_concurrent": 3,
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


# ============================================================
#  Module 3: RoutingRules (updated for v2.0)
# ============================================================

class RoutingRules:
    HARD_RULES = {
        "sms": "phone", "call": "phone", "camera": "phone",
        "location": "phone", "alarm": "phone", "media": "phone",
        "screenshot": "phone",
        "code": "pc", "ide": "pc", "office": "pc",
    }
    HIGH_RISK_OPS = {"payment", "refund", "delete_irreversible", "cancel_order"}
    MIN_ROUTE_SCORE = 0.2

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
                        "target": d["device_id"], "method": "hard_rule",
                        "reason": "hard_rule: {}->{}".format(task_profile["tools_required"][0], hard_target),
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


# ============================================================
#  Module 4: RoutingLog (unchanged)
# ============================================================

class RoutingLog:
    MAX_LOG_SIZE = 100

    def __init__(self):
        self.logs = []

    def log_decision(self, task_profile, decision):
        entry = {
            "log_id": "ROUTE-{}-{}".format(datetime.now().strftime("%Y%m%d"), len(self.logs) + 1),
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


# ============================================================
#  Module 5: LoadBalancer (unchanged)
# ============================================================

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


# ============================================================
#  Module 6: FailoverMigration (updated for v2.0)
# ============================================================

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
#  Module 7: InvocationIndicator (NEW in v2.0)
# ============================================================

class InvocationIndicator:
    """智能调用指示器 — 每次路由决策产生可见反馈"""
    MAX_HISTORY = 50

    INDICATOR_TYPES = {
        "route_decision": {"icon": "🔀", "title_template": "智能调用 → {target}"},
        "crash_risk": {"icon": "⚠️", "title_template": "检测到崩溃风险"},
        "failover": {"icon": "🔄", "title_template": "任务迁移"},
        "completion": {"icon": "✅", "title_template": "任务完成"},
        "link_status": {"icon": "🔗", "title_template": "通信链路状态变化"},
    }

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.history = []

    def create_route_indicator(self, task_id, target_device, method, reason, score=None):
        indicator = {
            "type": "route_decision",
            "indicator_id": "IND-{}".format(int(time.time() * 1000)),
            "task_id": task_id,
            "status": "routing",
            "decision": {
                "target_device": target_device,
                "method": method,
                "reason": reason,
                "score": score,
                "confidence": "high" if method == "hard_rule" else "medium",
            },
            "visual": {
                "icon": "🔀",
                "title": "智能调用 → {}".format(target_device),
                "subtitle": reason,
                "progress": None,
            },
        }
        self._record(indicator)
        return indicator

    def create_crash_risk_indicator(self, task_id, device, risk_score, risk_factors, sub_task_count):
        indicator = {
            "type": "crash_risk",
            "indicator_id": "IND-{}".format(int(time.time() * 1000)),
            "task_id": task_id,
            "status": "risk_detected",
            "risk": {
                "device": device,
                "risk_level": risk_score,
                "risk_factors": risk_factors,
                "action": "split_and_notify",
                "sub_task_count": sub_task_count,
            },
            "visual": {
                "icon": "⚠️",
                "title": "检测到崩溃风险",
                "subtitle": "已拆分为{}个子任务，通知手机端分步执行".format(sub_task_count),
                "progress": None,
            },
        }
        self._record(indicator)
        return indicator

    def create_failover_indicator(self, task_id, from_device, to_device, level, reason):
        indicator = {
            "type": "failover",
            "indicator_id": "IND-{}".format(int(time.time() * 1000)),
            "task_id": task_id,
            "status": "migrating",
            "migration": {
                "level": level,
                "from_device": from_device,
                "to_device": to_device,
                "reason": reason,
            },
            "visual": {
                "icon": "🔄",
                "title": "任务迁移",
                "subtitle": "{} → {} (Level {})".format(from_device, to_device, level),
                "progress": None,
            },
        }
        self._record(indicator)
        return indicator

    def create_completion_indicator(self, task_id, device, duration_seconds, sub_tasks_completed, migrations):
        indicator = {
            "type": "completion",
            "indicator_id": "IND-{}".format(int(time.time() * 1000)),
            "task_id": task_id,
            "status": "completed",
            "result": {
                "device": device,
                "duration_seconds": duration_seconds,
                "sub_tasks_completed": sub_tasks_completed,
                "migrations": migrations,
            },
            "visual": {
                "icon": "✅",
                "title": "任务完成",
                "subtitle": "由{}执行，耗时{}秒".format(device, duration_seconds),
                "progress": 100,
            },
        }
        self._record(indicator)
        return indicator

    def create_link_status_indicator(self, primary_status, primary_latency, secondary_status, secondary_latency):
        indicator = {
            "type": "link_status",
            "indicator_id": "IND-{}".format(int(time.time() * 1000)),
            "status": "link_change",
            "links": {
                "primary": {"status": primary_status, "latency_ms": primary_latency},
                "secondary": {"status": secondary_status, "latency_ms": secondary_latency},
            },
            "visual": {
                "icon": "🔗",
                "title": "通信链路状态变化",
                "subtitle": "主链路 {} {}ms | 副链路 {} {}ms".format(
                    primary_status, primary_latency, secondary_status, secondary_latency
                ),
                "progress": None,
            },
        }
        self._record(indicator)
        return indicator

    def _record(self, indicator):
        if not self.enabled:
            return
        self.history.append(indicator)
        if len(self.history) > self.MAX_HISTORY:
            self.history = self.history[-self.MAX_HISTORY:]

    def get_history(self, n=10):
        return self.history[-n:]

    def get_by_task(self, task_id):
        return [ind for ind in self.history if ind.get("task_id") == task_id]

    def clear(self):
        self.history.clear()


# ============================================================
#  Module 8: CrashDetector (NEW in v2.0)
# ============================================================

class CrashDetector:
    """崩溃风险检测 — 监控PC端执行环境，高风险时拆分任务通知手机端"""
    DEFAULT_THRESHOLD = 0.7

    RISK_FACTORS = {
        "RF-001": {"name": "文件大小风险", "weight": 0.25},
        "RF-002": {"name": "内存占用风险", "weight": 0.25},
        "RF-003": {"name": "CPU负载风险", "weight": 0.15},
        "RF-004": {"name": "并发任务风险", "weight": 0.15},
        "RF-005": {"name": "代码风险", "weight": 0.10},
        "RF-006": {"name": "磁盘空间风险", "weight": 0.10},
    }

    def __init__(self, threshold=None):
        self.threshold = threshold or self.DEFAULT_THRESHOLD
        self.risk_log = []

    def assess_file_risk(self, file_size_mb):
        if file_size_mb < 100:
            return 0.1
        elif file_size_mb < 1024:
            return 0.4
        elif file_size_mb < 5120:
            return 0.7
        else:
            return 0.95

    def assess_memory_risk(self, estimated_peak_ratio):
        if estimated_peak_ratio < 0.5:
            return 0.1
        elif estimated_peak_ratio < 0.7:
            return 0.4
        elif estimated_peak_ratio < 0.9:
            return 0.7
        else:
            return 0.95

    def assess_cpu_risk(self, current_cpu_ratio):
        if current_cpu_ratio < 0.3:
            return 0.1
        elif current_cpu_ratio < 0.6:
            return 0.3
        elif current_cpu_ratio < 0.8:
            return 0.6
        else:
            return 0.9

    def assess_concurrent_risk(self, current_tasks):
        if current_tasks == 0:
            return 0.0
        elif current_tasks <= 2:
            return 0.2
        elif current_tasks <= 4:
            return 0.5
        else:
            return 0.8

    def assess_code_risk(self, is_third_party=False, is_system_level=False):
        if is_system_level:
            return 0.9
        elif is_third_party:
            return 0.7
        else:
            return 0.2

    def assess_disk_risk(self, free_gb):
        if free_gb > 10:
            return 0.0
        elif free_gb > 5:
            return 0.3
        elif free_gb > 1:
            return 0.6
        else:
            return 0.9

    def compute_risk_score(self, factors):
        """factors: dict of {factor_id: score}"""
        total = 0.0
        for fid, score in factors.items():
            weight = self.RISK_FACTORS.get(fid, {}).get("weight", 0.1)
            total += score * weight
        return round(total, 4)

    def assess(self, device_status, task_profile, file_size_mb=0):
        """综合评估崩溃风险"""
        factors = {}
        factors["RF-001"] = self.assess_file_risk(file_size_mb) if file_size_mb > 0 else 0.0
        factors["RF-002"] = self.assess_memory_risk(device_status.get("memory_usage", 0.3))
        factors["RF-003"] = self.assess_cpu_risk(device_status.get("cpu_load", 0.2))
        factors["RF-004"] = self.assess_concurrent_risk(device_status.get("current_tasks", 0))
        # code risk based on task tools
        tools = set(task_profile.get("tools_required", []))
        has_code = bool(tools & {"code", "ide"})
        factors["RF-005"] = self.assess_code_risk(is_third_party=has_code)
        factors["RF-006"] = self.assess_disk_risk(device_status.get("disk_free_gb", 50))

        risk_score = self.compute_risk_score(factors)

        result = {
            "risk_score": risk_score,
            "factors": factors,
            "above_threshold": risk_score >= self.threshold,
            "risk_level": "high" if risk_score >= self.threshold else "medium" if risk_score >= 0.3 else "low",
        }

        # Log
        self.risk_log.append({
            "task_id": task_profile.get("task_id", "unknown"),
            "device": device_status.get("device_id", "unknown"),
            "risk_score": risk_score,
            "above_threshold": result["above_threshold"],
            "timestamp": datetime.now().isoformat(),
        })
        if len(self.risk_log) > 200:
            self.risk_log = self.risk_log[-200:]

        return result

    def split_task(self, task_profile, risk_result):
        """将高风险任务拆分为更小的子任务"""
        tools = task_profile.get("tools_required", [])
        sub_tasks = []
        for i, tool in enumerate(tools, 1):
            sub_tasks.append({
                "id": "ST-{}".format(i),
                "text": "子任务: {}".format(tool),
                "tools": [tool],
                "estimated_memory_mb": 256,
            })
        # Add aggregation task
        sub_tasks.append({
            "id": "ST-{}".format(len(tools) + 1),
            "text": "汇总所有结果",
            "tools": ["file"],
            "estimated_memory_mb": 128,
        })
        return {
            "original_task_id": task_profile.get("task_id"),
            "risk_score": risk_result["risk_score"],
            "sub_tasks": sub_tasks,
            "execution_plan": {
                "strategy": "sequential",
                "delay_between_ms": 2000,
                "max_concurrent": 1,
            },
        }


# ============================================================
#  Module 9: DualLink (NEW in v2.0)
# ============================================================

class DualLink:
    """双链路通信 — device_chat主链路 + 网络心跳副链路"""
    LINK_STATES = {"FULL", "PRIMARY_ONLY", "SECONDARY_ONLY", "DEGRADED", "OFFLINE"}
    OFFLINE_THRESHOLD = 3

    def __init__(self, pc_id, phone_id, heartbeat_interval=15, heartbeat_timeout_sec=5):
        self.pc_id = pc_id
        self.phone_id = phone_id
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout_sec = heartbeat_timeout_sec
        # Primary link (device_chat)
        self.primary_status = "ok"
        self.primary_latency_ms = 150
        # Secondary link (network heartbeat)
        self.secondary_status = "ok"
        self.secondary_latency_ms = 300
        self.secondary_consecutive_failures = 0
        # Overall state
        self.link_state = "FULL"
        # PC status (updated via heartbeat)
        self.pc_status = {}
        self.phone_status = {}

    def establish_secondary(self):
        """PC端启动时建立副链路"""
        return {
            "type": "link_establish",
            "from": self.pc_id,
            "to": self.phone_id,
            "timestamp": datetime.now().isoformat(),
            "link": "secondary",
        }

    def acknowledge_link(self):
        """手机端确认副链路"""
        self.secondary_status = "ok"
        self.secondary_consecutive_failures = 0
        self._update_state()
        return {
            "type": "link_ack",
            "from": self.phone_id,
            "to": self.pc_id,
            "timestamp": datetime.now().isoformat(),
            "link": "secondary",
        }

    def send_heartbeat(self):
        """PC端发送心跳"""
        return {
            "type": "heartbeat",
            "from": self.pc_id,
            "to": self.phone_id,
            "timestamp": datetime.now().isoformat(),
            "link": "secondary",
            "payload": {"pc_status": self.pc_status},
        }

    def receive_heartbeat_response(self, phone_status=None, latency_ms=None):
        """PC端收到心跳响应"""
        self.secondary_consecutive_failures = 0
        self.secondary_status = "ok"
        if latency_ms is not None:
            self.secondary_latency_ms = latency_ms
        if phone_status:
            self.phone_status = phone_status
        self._update_state()
        return True

    def heartbeat_timeout(self):
        """PC端心跳超时"""
        self.secondary_consecutive_failures += 1
        if self.secondary_consecutive_failures >= self.OFFLINE_THRESHOLD:
            self.secondary_status = "offline"
        self._update_state()
        return self.secondary_consecutive_failures

    def set_primary_status(self, status, latency_ms=None):
        """设置主链路状态"""
        self.primary_status = status
        if latency_ms is not None:
            self.primary_latency_ms = latency_ms
        self._update_state()

    def _update_state(self):
        """根据双链路状态计算整体状态"""
        p_ok = self.primary_status == "ok"
        s_ok = self.secondary_status == "ok"
        p_slow = self.primary_latency_ms > 5000 if p_ok else False
        s_slow = self.secondary_latency_ms > 5000 if s_ok else False

        if p_ok and s_ok:
            if p_slow and s_slow:
                self.link_state = "DEGRADED"
            else:
                self.link_state = "FULL"
        elif p_ok and not s_ok:
            self.link_state = "PRIMARY_ONLY"
        elif not p_ok and s_ok:
            self.link_state = "SECONDARY_ONLY"
        else:
            self.link_state = "OFFLINE"

    def get_proximity_modifier(self):
        """根据链路状态返回 proximity 修正系数"""
        modifiers = {
            "FULL": 1.0,
            "PRIMARY_ONLY": 1.0,
            "SECONDARY_ONLY": 0.5,
            "DEGRADED": 0.3,
            "OFFLINE": 0.0,
        }
        return modifiers.get(self.link_state, 0.0)

    def is_device_reachable(self):
        """设备是否可达（任一链路可用）"""
        return self.primary_status == "ok" or self.secondary_status == "ok"

    def send_emergency_notification(self, notification_type, payload):
        """通过副链路发送紧急通知"""
        return {
            "type": notification_type,
            "from": self.pc_id,
            "to": self.phone_id,
            "timestamp": datetime.now().isoformat(),
            "link": "secondary",
            "payload": payload,
        }

    def terminate(self):
        """断开副链路"""
        self.secondary_status = "offline"
        self._update_state()
        return {
            "type": "link_terminate",
            "from": self.pc_id,
            "to": self.phone_id,
            "timestamp": datetime.now().isoformat(),
            "link": "secondary",
        }


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

    fm2 = FailoverMigration()
    fm2.l2_count = FailoverMigration.MAX_L2_MIGRATIONS
    l2_limit = fm2.level2_migrate_device(task_p, phone_offline, [phone_offline, other_phone])
    check_true("L2 limit blocks migration", not l2_limit["migrated"])

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

    for i in range(105):
        rlog.log_decision(profiler.analyze("搜索"), {"target": "pc-01"})
    check_true("log capped at 100", len(rlog.logs) <= 100)

    rlog.clear()
    check_eq("log cleared", len(rlog.logs), 0)

    # -- Module 7: Edge Cases --
    print("\n[Module 7] Edge Cases")

    empty_profile = profiler.analyze("你好")
    check_eq("empty tools = any env", empty_profile["environment"], "any")
    check_eq("empty tools = light", empty_profile["complexity"], "light")
    check_eq("empty tools no sub_tasks", empty_profile["sub_tasks"], [])

    phone_very_slow = DeviceCapability.create_device("phone-vs", "phone", load_status="busy", heartbeat_latency_ms=8000)
    code_p = profiler.analyze("写代码")
    route_low = RoutingRules.route(code_p, [phone_very_slow])
    check_eq("low score returns no_suitable_device", route_low.get("status"), "no_suitable_device")

    check_true("refund is high risk", fm.is_high_risk("refund"))
    check_true("delete_irreversible is high risk", fm.is_high_risk("delete_irreversible"))
    check_true("normal op not high risk", not fm.is_high_risk("read_file"))

    multi_profile = profiler.analyze("发短信写代码")
    route_multi = RoutingRules.route(multi_profile, [phone, pc])
    check_eq("multi hard rule code wins (alphabetical)", route_multi["target"], "pc-01")

    no_lat = DeviceCapability.create_device("phone-nolat", "phone", heartbeat_latency_ms=None)
    check_eq("no latency proximity=1.0", RoutingRules.compute_proximity(no_lat), 1.0)

    off_dev = DeviceCapability.create_device("phone-off", "phone", online=False)
    check_eq("offline proximity=0.0", RoutingRules.compute_proximity(off_dev), 0.0)

    is_timeout, _ = fm.detect_failure({"timeout": True})
    check_true("timeout detected", is_timeout)

    is_ok, _ = fm.detect_failure({"data": "hello"})
    check_true("normal result not failure", not is_ok)

    l2_no_other = fm.level2_migrate_device(task_p, phone, [phone])
    check_true("L2 no other devices", not l2_no_other["migrated"])

    # ============================================================
    #  Module 8: InvocationIndicator (NEW)
    # ============================================================
    print("\n[Module 8] InvocationIndicator")

    ind = InvocationIndicator(enabled=True)

    # Route decision indicator
    ri = ind.create_route_indicator("T-001", "pc-01", "hard_rule", "代码执行→电脑端", score=0.95)
    check_eq("route indicator type", ri["type"], "route_decision")
    check_eq("route indicator icon", ri["visual"]["icon"], "🔀")
    check_true("route indicator has target", "pc-01" in ri["visual"]["title"])
    check_eq("route indicator confidence high", ri["decision"]["confidence"], "high")

    # Crash risk indicator
    ci = ind.create_crash_risk_indicator("T-002", "pc-01", 0.85, ["large_file", "memory"], 3)
    check_eq("crash indicator type", ci["type"], "crash_risk")
    check_eq("crash indicator icon", ci["visual"]["icon"], "⚠️")
    check_eq("crash indicator sub_task_count", ci["risk"]["sub_task_count"], 3)
    check_eq("crash indicator action", ci["risk"]["action"], "split_and_notify")

    # Failover indicator
    fi = ind.create_failover_indicator("T-003", "pc-01", "phone-01", 2, "PC超时")
    check_eq("failover indicator type", fi["type"], "failover")
    check_eq("failover indicator icon", fi["visual"]["icon"], "🔄")
    check_eq("failover indicator level", fi["migration"]["level"], 2)

    # Completion indicator
    cpi = ind.create_completion_indicator("T-004", "pc-01", 12, 3, 0)
    check_eq("completion indicator type", cpi["type"], "completion")
    check_eq("completion indicator icon", cpi["visual"]["icon"], "✅")
    check_eq("completion indicator progress", cpi["visual"]["progress"], 100)

    # Link status indicator
    lsi = ind.create_link_status_indicator("ok", 150, "offline", 0)
    check_eq("link status indicator type", lsi["type"], "link_status")
    check_eq("link status indicator icon", lsi["visual"]["icon"], "🔗")

    # History management
    check_eq("indicator history count", len(ind.get_history()), 5)
    check_eq("indicator history limit", len(ind.get_history(2)), 2)

    # Get by task
    by_task = ind.get_by_task("T-001")
    check_eq("get by task count", len(by_task), 1)
    check_eq("get by task type", by_task[0]["type"], "route_decision")

    # Overflow test
    for i in range(55):
        ind.create_route_indicator("T-overflow", "pc-01", "soft_rule", "test")
    check_true("indicator history capped at 50", len(ind.history) <= 50)

    # Disabled indicator
    ind_disabled = InvocationIndicator(enabled=False)
    ind_disabled.create_route_indicator("T-disabled", "pc-01", "soft_rule", "test")
    check_eq("disabled indicator no history", len(ind_disabled.history), 0)

    ind.clear()
    check_eq("indicator cleared", len(ind.history), 0)

    # ============================================================
    #  Module 9: CrashDetector (NEW)
    # ============================================================
    print("\n[Module 9] CrashDetector")

    cd = CrashDetector(threshold=0.7)

    # File risk scoring
    check_eq("file <100MB low risk", cd.assess_file_risk(50), 0.1)
    check_eq("file 100MB-1GB medium", cd.assess_file_risk(500), 0.4)
    check_eq("file 1-5GB high", cd.assess_file_risk(2000), 0.7)
    check_eq("file >5GB very high", cd.assess_file_risk(6000), 0.95)

    # Memory risk scoring
    check_eq("memory <50% low", cd.assess_memory_risk(0.3), 0.1)
    check_eq("memory 50-70% medium", cd.assess_memory_risk(0.6), 0.4)
    check_eq("memory 70-90% high", cd.assess_memory_risk(0.8), 0.7)
    check_eq("memory >90% very high", cd.assess_memory_risk(0.95), 0.95)

    # CPU risk scoring
    check_eq("cpu <30% low", cd.assess_cpu_risk(0.2), 0.1)
    check_eq("cpu 30-60% medium", cd.assess_cpu_risk(0.45), 0.3)
    check_eq("cpu 60-80% high", cd.assess_cpu_risk(0.7), 0.6)
    check_eq("cpu >80% very high", cd.assess_cpu_risk(0.85), 0.9)

    # Concurrent risk scoring
    check_eq("concurrent 0 low", cd.assess_concurrent_risk(0), 0.0)
    check_eq("concurrent 1-2 low-med", cd.assess_concurrent_risk(2), 0.2)
    check_eq("concurrent 3-4 medium", cd.assess_concurrent_risk(4), 0.5)
    check_eq("concurrent 5+ high", cd.assess_concurrent_risk(6), 0.8)

    # Code risk scoring
    check_eq("no code low", cd.assess_code_risk(), 0.2)
    check_eq("third party medium-high", cd.assess_code_risk(is_third_party=True), 0.7)
    check_eq("system level very high", cd.assess_code_risk(is_system_level=True), 0.9)

    # Disk risk scoring
    check_eq("disk >10GB low", cd.assess_disk_risk(50), 0.0)
    check_eq("disk 5-10GB medium", cd.assess_disk_risk(7), 0.3)
    check_eq("disk 1-5GB high", cd.assess_disk_risk(3), 0.6)
    check_eq("disk <1GB very high", cd.assess_disk_risk(0.5), 0.9)

    # Compute risk score
    test_factors = {"RF-001": 0.7, "RF-002": 0.9, "RF-003": 0.3, "RF-004": 0.2, "RF-005": 0.0, "RF-006": 0.1}
    risk = cd.compute_risk_score(test_factors)
    check_true("risk score computed correctly", 0.3 < risk < 0.5)

    # Full assessment - low risk
    low_device = {"device_id": "pc-01", "cpu_load": 0.2, "memory_usage": 0.3, "current_tasks": 0, "disk_free_gb": 50}
    low_task = profiler.analyze("搜索")
    low_result = cd.assess(low_device, low_task)
    check_eq("low risk level", low_result["risk_level"], "low")
    check_true("low risk below threshold", not low_result["above_threshold"])

    # Full assessment - high risk
    high_device = {"device_id": "pc-01", "cpu_load": 0.85, "memory_usage": 0.92, "current_tasks": 5, "disk_free_gb": 0.5}
    high_task = profiler.analyze("写代码")
    high_result = cd.assess(high_device, high_task, file_size_mb=6000)
    check_eq("high risk level", high_result["risk_level"], "high")
    check_true("high risk above threshold", high_result["above_threshold"])

    # Task splitting
    split = cd.split_task(high_task, high_result)
    check_true("split has sub_tasks", len(split["sub_tasks"]) > 0)
    check_eq("split strategy sequential", split["execution_plan"]["strategy"], "sequential")
    check_eq("split max_concurrent 1", split["execution_plan"]["max_concurrent"], 1)
    check_eq("split delay 2s", split["execution_plan"]["delay_between_ms"], 2000)

    # Risk log
    check_true("risk log has entries", len(cd.risk_log) > 0)

    # ============================================================
    #  Module 10: DualLink (NEW)
    # ============================================================
    print("\n[Module 10] DualLink")

    dl = DualLink("pc-01", "phone-01")

    # Initial state
    check_eq("initial link state FULL", dl.link_state, "FULL")
    check_true("initial device reachable", dl.is_device_reachable())
    check_eq("initial proximity modifier 1.0", dl.get_proximity_modifier(), 1.0)

    # Establish secondary link
    est = dl.establish_secondary()
    check_eq("establish type", est["type"], "link_establish")
    check_eq("establish from pc", est["from"], "pc-01")
    check_eq("establish to phone", est["to"], "phone-01")

    # Acknowledge
    ack = dl.acknowledge_link()
    check_eq("ack type", ack["type"], "link_ack")
    check_eq("ack from phone", ack["from"], "phone-01")

    # Heartbeat
    hb = dl.send_heartbeat()
    check_eq("heartbeat type", hb["type"], "heartbeat")
    check_eq("heartbeat link secondary", hb["link"], "secondary")

    # Heartbeat response
    dl.receive_heartbeat_response(phone_status={"battery": 0.85}, latency_ms=200)
    check_eq("after response state FULL", dl.link_state, "FULL")
    check_eq("secondary latency updated", dl.secondary_latency_ms, 200)
    check_eq("phone status updated", dl.phone_status["battery"], 0.85)

    # Heartbeat timeout - 1 time (grace)
    dl.heartbeat_timeout()
    check_eq("1 timeout still ok", dl.secondary_status, "ok")
    check_eq("1 timeout failures=1", dl.secondary_consecutive_failures, 1)

    # Heartbeat timeout - 2 times
    dl.heartbeat_timeout()
    check_eq("2 timeouts still ok (grace)", dl.secondary_status, "ok")
    check_eq("2 timeouts failures=2", dl.secondary_consecutive_failures, 2)

    # Heartbeat timeout - 3 times (offline)
    dl.heartbeat_timeout()
    check_eq("3 timeouts secondary offline", dl.secondary_status, "offline")
    check_eq("state PRIMARY_ONLY", dl.link_state, "PRIMARY_ONLY")
    check_eq("proximity modifier still 1.0", dl.get_proximity_modifier(), 1.0)
    check_true("still reachable via primary", dl.is_device_reachable())

    # Primary link also goes down
    dl.set_primary_status("error", latency_ms=0)
    check_eq("both down state OFFLINE", dl.link_state, "OFFLINE")
    check_eq("proximity modifier 0.0", dl.get_proximity_modifier(), 0.0)
    check_true("not reachable", not dl.is_device_reachable())

    # Primary recovers
    dl.set_primary_status("ok", latency_ms=100)
    check_eq("primary only state", dl.link_state, "PRIMARY_ONLY")
    check_true("reachable again", dl.is_device_reachable())

    # Secondary recovers
    dl.receive_heartbeat_response(latency_ms=250)
    check_eq("both recovered FULL", dl.link_state, "FULL")

    # Degraded state
    dl.primary_latency_ms = 6000
    dl.secondary_latency_ms = 7000
    dl._update_state()
    check_eq("high latency both DEGRADED", dl.link_state, "DEGRADED")
    check_eq("degraded proximity 0.3", dl.get_proximity_modifier(), 0.3)

    # Emergency notification
    notif = dl.send_emergency_notification("crash_risk_split", {"task_id": "T-001", "risk_score": 0.85})
    check_eq("emergency type", notif["type"], "crash_risk_split")
    check_eq("emergency link secondary", notif["link"], "secondary")
    check_eq("emergency from pc", notif["from"], "pc-01")

    # Terminate
    term = dl.terminate()
    check_eq("terminate type", term["type"], "link_terminate")
    check_eq("terminate state PRIMARY_ONLY (only secondary terminated)", dl.link_state, "PRIMARY_ONLY")

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
