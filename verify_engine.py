#!/usr/bin/env python3
"""
Smart Invocation Engine (SIE) - Core Logic Verification
Tests: TaskProfiler, DeviceCapability, RoutingRules, RoutingLog, LoadBalancer,
       FailoverMigration, InvocationIndicator, CrashDetector, DualLink
Target: 200+ assertions covering all 12 modules (v3.0 optimized)
"""

import re
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
    # 预编译：按关键词长度降序排列，避免短词误匹配，且只遍历一次
    _sorted_keywords = None

    @classmethod
    def _ensure_sorted(cls):
        if cls._sorted_keywords is None:
            cls._sorted_keywords = [
                (kw.lower(), tool)
                for kw, tool in sorted(
                    cls.KEYWORD_TOOL_MAP.items(),
                    key=lambda x: len(x[0]),
                    reverse=True
                )
            ]

    def analyze(self, task_text):
        tools = set()
        text_lower = task_text.lower()
        self._ensure_sorted()
        for kw_lower, tool in self._sorted_keywords:
            if kw_lower in text_lower:
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
        elif len(tools) > 1 and any(kw in task_text for kw in self.SPLITTABLE_KEYWORDS):
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
        # 使用生成器表达式避免临时列表分配
        total = sum(scores.get(t, 0) for t in tools_required)
        return total / len(tools_required)

    @staticmethod
    def compute_coverage(device, tools_required):
        if not tools_required:
            return 1.0
        cap_set = set(device["capabilities"])
        # 使用 sum + 生成器替代 list comprehension
        covered = sum(1 for t in tools_required if t in cap_set)
        return covered / len(tools_required)


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

    # 预计算负载映射表，避免每次路由都创建新字典
    _LOAD_MAP = {"idle": 1.0, "busy": 0.3, "offline": 0.0}

    @staticmethod
    def compute_route_score(task_profile, device):
        tools = task_profile["tools_required"]
        cap_match = DeviceCapability.compute_capability_score(device, tools)
        load_factor = RoutingRules._LOAD_MAP.get(device["load_status"], 0.0)
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
        # 单候选设备快速路径：无需排序
        if len(candidates) == 1:
            score = RoutingRules.compute_route_score(task_profile, candidates[0])
            score_r = round(score, 4)
            if score_r < RoutingRules.MIN_ROUTE_SCORE:
                return {"status": "no_suitable_device", "candidates": [(candidates[0]["device_id"], score_r)]}
            return {"target": candidates[0]["device_id"], "method": "soft_rule", "score": score_r, "all_scores": [(candidates[0]["device_id"], score_r)]}
        # 多候选设备：使用 key 参数避免创建元组列表
        scored = [
            (d, round(RoutingRules.compute_route_score(task_profile, d), 4))
            for d in candidates
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        best_dev, best_score = scored[0]
        if best_score < RoutingRules.MIN_ROUTE_SCORE:
            return {"status": "no_suitable_device", "candidates": [(d["device_id"], s) for d, s in scored]}
        return {
            "target": best_dev["device_id"], "method": "soft_rule",
            "score": best_score,
            "all_scores": [(d["device_id"], s) for d, s in scored],
        }


# ============================================================
#  Module 4: RoutingLog (unchanged)
# ============================================================

class RoutingLog:
    MAX_LOG_SIZE = 100

    def __init__(self):
        self.logs = []

    def log_decision(self, task_profile, decision):
        now = datetime.now()
        entry = {
            "log_id": "ROUTE-{}-{}".format(now.strftime("%Y%m%d"), len(self.logs) + 1),
            "task_id": task_profile.get("task_id", "unknown"),
            "timestamp": now.isoformat(),
            "input": {
                "tools_required": task_profile.get("tools_required", []),
                "complexity": task_profile.get("complexity", "unknown"),
                "environment": task_profile.get("environment", "unknown"),
            },
            "decision": decision,
        }
        self.logs.append(entry)
        # 使用切片而非重新赋值，减少内存分配
        if len(self.logs) > self.MAX_LOG_SIZE:
            del self.logs[:len(self.logs) - self.MAX_LOG_SIZE]
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
        # 快速路径：空工具列表时直接返回第一个在线空闲设备
        if not tools_required:
            for device in devices:
                if device["online"] and device["load_status"] == "idle":
                    return device
            return None
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
        # 快速路径：None 检查
        if result is None:
            return True, "result is None"
        # 快速路径：非 dict 类型
        if not isinstance(result, dict):
            return False, ""
        # 检查 error 和 timeout
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
            del self.history[:len(self.history) - self.MAX_HISTORY]

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
    __slots__ = ['threshold', 'risk_log', '_weight_vector']
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
        # 预提取权重向量，避免每次 compute_risk_score 都查字典
        self._weight_vector = {fid: info["weight"] for fid, info in self.RISK_FACTORS.items()}

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
        # 使用预提取的权重向量，避免重复字典查找
        total = 0.0
        for fid, score in factors.items():
            total += score * self._weight_vector.get(fid, 0.1)
        return round(total, 4)

    def assess(self, device_status, task_profile, file_size_mb=0):
        """综合评估崩溃风险"""
        # 内联风险评估，减少函数调用开销
        # RF-001: 文件大小
        if file_size_mb <= 0:
            f1 = 0.0
        elif file_size_mb < 100:
            f1 = 0.1
        elif file_size_mb < 1024:
            f1 = 0.4
        elif file_size_mb < 5120:
            f1 = 0.7
        else:
            f1 = 0.95
        # RF-002: 内存
        mem = device_status.get("memory_usage", 0.3)
        f2 = 0.1 if mem < 0.5 else 0.4 if mem < 0.7 else 0.7 if mem < 0.9 else 0.95
        # RF-003: CPU
        cpu = device_status.get("cpu_load", 0.2)
        f3 = 0.1 if cpu < 0.3 else 0.3 if cpu < 0.6 else 0.6 if cpu < 0.8 else 0.9
        # RF-004: 并发
        tasks = device_status.get("current_tasks", 0)
        f4 = 0.0 if tasks == 0 else 0.2 if tasks <= 2 else 0.5 if tasks <= 4 else 0.8
        # RF-005: 代码
        tools = set(task_profile.get("tools_required", []))
        has_code = bool(tools & {"code", "ide"})
        f5 = 0.9 if False else 0.7 if has_code else 0.2  # is_system_level=False in normal assess
        # RF-006: 磁盘
        disk = device_status.get("disk_free_gb", 50)
        f6 = 0.0 if disk > 10 else 0.3 if disk > 5 else 0.6 if disk > 1 else 0.9

        factors = {"RF-001": f1, "RF-002": f2, "RF-003": f3, "RF-004": f4, "RF-005": f5, "RF-006": f6}

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
            del self.risk_log[:len(self.risk_log) - 200]

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
    __slots__ = ['pc_id', 'phone_id', 'heartbeat_interval', 'heartbeat_timeout_sec',
                 'primary_status', 'primary_latency_ms', 'secondary_status',
                 'secondary_latency_ms', 'secondary_consecutive_failures',
                 'link_state', 'pc_status', 'phone_status']
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
        """根据双链路状态计算整体状态（优化：位运算加速状态判断）"""
        p_ok = self.primary_status == "ok"
        s_ok = self.secondary_status == "ok"
        # 用位标志代替多次布尔判断
        state_flags = (p_ok << 1) | s_ok  # 3=both, 2=primary_only, 1=secondary_only, 0=offline
        if state_flags == 3:
            # 双链路都在线，检查是否降级
            self.link_state = "DEGRADED" if (
                self.primary_latency_ms > 5000 and self.secondary_latency_ms > 5000
            ) else "FULL"
        elif state_flags == 2:
            self.link_state = "PRIMARY_ONLY"
        elif state_flags == 1:
            self.link_state = "SECONDARY_ONLY"
        else:
            self.link_state = "OFFLINE"

    # 预定义 proximity 修正系数表
    _PROXIMITY_MODIFIERS = {
        "FULL": 1.0, "PRIMARY_ONLY": 1.0, "SECONDARY_ONLY": 0.5,
        "DEGRADED": 0.3, "OFFLINE": 0.0,
    }

    def get_proximity_modifier(self):
        """根据链路状态返回 proximity 修正系数"""
        return self._PROXIMITY_MODIFIERS.get(self.link_state, 0.0)

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

    # ============================================================
    #  Module 11: AutoDeviceRegistration
    # ============================================================
    print("\n[Module 11] AutoDeviceRegistration")

    class AutoDeviceRegistration:
        DEVICE_TYPE_CAPS = {
            "phone": ["sms", "call", "camera", "location", "alarm", "media", "notification", "contacts", "screenshot"],
            "pc": ["code", "ide", "file", "browser", "text", "office", "search", "notification"],
            "tablet": ["calendar", "media", "notification", "file", "search", "browser"],
            "speaker": ["media", "notification", "tts"],
            "display": ["media", "notification", "tts", "calendar", "file"],
        }
        DEVICE_TYPE_SCORES = {
            "phone": {"sms": 0.95, "call": 0.90, "camera": 0.95, "location": 0.95, "alarm": 0.90,
                       "media": 0.85, "notification": 0.80, "contacts": 0.85, "screenshot": 0.90},
            "pc": {"code": 0.95, "ide": 0.95, "file": 0.90, "browser": 0.85, "text": 0.85,
                    "office": 0.90, "search": 0.80, "notification": 0.70},
            "tablet": {"calendar": 0.80, "media": 0.80, "notification": 0.75, "file": 0.70, "search": 0.70, "browser": 0.75},
            "speaker": {"media": 0.90, "notification": 0.80, "tts": 0.95},
            "display": {"media": 0.85, "notification": 0.80, "tts": 0.90, "calendar": 0.75, "file": 0.70},
        }

        def __init__(self):
            self.registered_devices = {}
            self.discovery_log = []

        def discover(self, online_devices):
            # 使用 set 交集运算加速查找新设备
            registered_ids = set(self.registered_devices.keys())
            return [dev for dev in online_devices if dev["device_id"] not in registered_ids]

        def probe(self, device_info):
            dtype = device_info.get("device_type", "phone")
            caps = self.DEVICE_TYPE_CAPS.get(dtype, [])
            scores = self.DEVICE_TYPE_SCORES.get(dtype, {})
            return {"capabilities": caps, "scores": scores, "probe_status": "success"}

        def register(self, device_info, probe_result):
            did = device_info["device_id"]
            self.registered_devices[did] = {
                "device_id": did,
                "device_name": device_info.get("device_name", "unknown"),
                "device_type": device_info.get("device_type", "phone"),
                "capabilities": probe_result["capabilities"],
                "capability_scores": probe_result["scores"],
                "probe_status": probe_result["probe_status"],
            }
            self.discovery_log.append({"device_id": did, "action": "registered"})
            return self.registered_devices[did]

        def get_device(self, did):
            return self.registered_devices.get(did)

        def is_registered(self, did):
            return did in self.registered_devices

        def unregister(self, did):
            if did in self.registered_devices:
                del self.registered_devices[did]
                self.discovery_log.append({"device_id": did, "action": "unregistered"})
                return True
            return False

    adr = AutoDeviceRegistration()

    # Discover new devices
    online = [
        {"device_id": "phone-01", "device_name": "xiaomi14", "device_type": "phone"},
        {"device_id": "pc-01", "device_name": "DESKTOP-PC", "device_type": "pc"},
    ]
    new_devs = adr.discover(online)
    check_eq("discover 2 new devices", len(new_devs), 2)
    check_eq("first new is phone-01", new_devs[0]["device_id"], "phone-01")

    # Probe capabilities
    probe_result = adr.probe(online[0])
    check_eq("probe phone type", probe_result["probe_status"], "success")
    check_true("phone has sms", "sms" in probe_result["capabilities"])
    check_true("phone no tts", "tts" not in probe_result["capabilities"])

    probe_pc = adr.probe(online[1])
    check_true("pc has code", "code" in probe_pc["capabilities"])
    check_true("pc has ide", "ide" in probe_pc["capabilities"])

    # Register devices
    reg1 = adr.register(online[0], probe_result)
    check_eq("registered phone-01", reg1["device_id"], "phone-01")
    check_eq("phone capabilities count", len(reg1["capabilities"]), 9)
    check_true("phone is registered", adr.is_registered("phone-01"))

    reg2 = adr.register(online[1], probe_pc)
    check_eq("registered pc-01", reg2["device_id"], "pc-01")
    check_true("pc is registered", adr.is_registered("pc-01"))

    # Re-discover (should find 0 new)
    new_devs2 = adr.discover(online)
    check_eq("re-discover 0 new", len(new_devs2), 0)

    # Probe tablet type
    tablet_info = {"device_id": "tablet-01", "device_name": "xiaomi-tablet-6", "device_type": "tablet"}
    probe_tablet = adr.probe(tablet_info)
    check_true("tablet has calendar", "calendar" in probe_tablet["capabilities"])
    check_true("tablet has media", "media" in probe_tablet["capabilities"])
    check_true("tablet no sms", "sms" not in probe_tablet["capabilities"])

    reg_tablet = adr.register(tablet_info, probe_tablet)
    check_eq("registered tablet", reg_tablet["device_id"], "tablet-01")

    # Probe speaker type
    speaker_info = {"device_id": "speaker-01", "device_name": "xiaomi-speaker-pro", "device_type": "speaker"}
    probe_speaker = adr.probe(speaker_info)
    check_true("speaker has tts", "tts" in probe_speaker["capabilities"])
    check_true("speaker has media", "media" in probe_speaker["capabilities"])
    check_true("speaker no code", "code" not in probe_speaker["capabilities"])

    reg_speaker = adr.register(speaker_info, probe_speaker)
    check_eq("registered speaker", reg_speaker["device_id"], "speaker-01")

    # Probe display type
    display_info = {"device_id": "display-01", "device_name": "xiaomi-smart-display", "device_type": "display"}
    probe_display = adr.probe(display_info)
    check_true("display has tts", "tts" in probe_display["capabilities"])
    check_true("display has calendar", "calendar" in probe_display["capabilities"])

    reg_display = adr.register(display_info, probe_display)
    check_eq("registered display", reg_display["device_id"], "display-01")

    # Get device
    got = adr.get_device("phone-01")
    check_eq("get device phone", got["device_name"], "xiaomi14")
    check_true("get non-existent is None", adr.get_device("nonexistent") is None)

    # Unregister
    check_true("unregister tablet", adr.unregister("tablet-01"))
    check_true("tablet no longer registered", not adr.is_registered("tablet-01"))
    check_true("unregister non-existent fails", not adr.unregister("nonexistent"))

    # Discovery log
    check_true("discovery log has entries", len(adr.discovery_log) > 0)

    # ============================================================
    #  Module 12: VoiceNotificationRelay
    # ============================================================
    print("\n[Module 12] VoiceNotificationRelay")

    class VoiceNotificationRelay:
        VOICE_CAPABLE_TYPES = {"speaker", "display", "phone"}
        TTS_CAPABLE_TYPES = {"speaker", "display", "phone"}

        def __init__(self):
            self.log = []
            self.dedup_window_ms = 300000

        def get_voice_capable_devices(self, registered_devices):
            # 使用列表推导式替代手动循环
            return [dev for dev in registered_devices.values()
                    if dev["device_type"] in self.VOICE_CAPABLE_TYPES]

        def compute_voice_score(self, device, user_proximity=None):
            dtype = device["device_type"]
            if dtype == "speaker":
                cap_score = 1.0
            elif dtype == "display":
                cap_score = 0.9
            elif dtype == "phone":
                cap_score = 0.6
            else:
                cap_score = 0.0
            status_score = 0.8
            proximity_score = user_proximity if user_proximity is not None else 0.5
            if dtype == "speaker":
                quality_score = 1.0
            elif dtype == "display":
                quality_score = 0.7
            elif dtype == "phone":
                quality_score = 0.5
            else:
                quality_score = 0.0
            return cap_score * 0.35 + status_score * 0.25 + proximity_score * 0.25 + quality_score * 0.15

        def select_best_device(self, registered_devices, user_proximity=None):
            voice_devs = self.get_voice_capable_devices(registered_devices)
            if not voice_devs:
                return None
            best = None
            best_score = -1
            for dev in voice_devs:
                score = self.compute_voice_score(dev, user_proximity)
                if score > best_score:
                    best_score = score
                    best = dev
            if best_score < 0.3:
                return None
            return {"device": best, "score": round(best_score, 4)}

        def generate_tts_text(self, event_type, task_name="", result_summary="", error_message=""):
            if event_type == "task_completed":
                return "Task {} completed. {}".format(task_name, result_summary)
            elif event_type == "task_failed":
                return "Task {} failed. {}".format(task_name, error_message)
            elif event_type == "crash_risk":
                return "Warning: crash risk detected. {}".format(error_message)
            return ""

        # 预编译正则表达式，避免每次调用都重新编译
        _RE_SPECIAL_CHARS = re.compile(r'[#*`~\[\]{}]')
        _RE_FILE_PATH = re.compile(r'/[\w/.-]+')

        def optimize_for_tts(self, text):
            text = self._RE_SPECIAL_CHARS.sub('', text)
            text = self._RE_FILE_PATH.sub('file', text)
            if len(text) > 200:
                text = text[:197] + "..."
            return text

        def create_notification(self, target_device, event_type, task_name="", result_summary="", error_message=""):
            tts_text = self.generate_tts_text(event_type, task_name, result_summary, error_message)
            optimized = self.optimize_for_tts(tts_text)
            dtype = target_device["device_type"]
            if dtype in self.TTS_CAPABLE_TYPES:
                method = "tts"
            else:
                method = "notification"
            notif = {
                "type": "voice_notification",
                "device_id": target_device["device_id"],
                "event": event_type,
                "tts_text": optimized,
                "method": method,
                "priority": "urgent" if event_type == "crash_risk" else "normal",
            }
            self.log.append(notif)
            return notif

        def is_duplicate(self, task_id):
            for entry in self.log:
                if entry.get("task_id") == task_id:
                    return True
            return False

    vnr = VoiceNotificationRelay()

    # Get voice capable devices from ADR registry
    voice_devs = vnr.get_voice_capable_devices(adr.registered_devices)
    check_eq("voice capable devices count", len(voice_devs), 3)  # phone, speaker, display (tablet was unregistered)

    # Voice score computation
    speaker_dev = adr.get_device("speaker-01")
    phone_dev = adr.get_device("phone-01")
    display_dev = adr.get_device("display-01")

    speaker_score = vnr.compute_voice_score(speaker_dev)
    phone_score = vnr.compute_voice_score(phone_dev)
    display_score = vnr.compute_voice_score(display_dev)
    check_true("speaker score > phone score", speaker_score > phone_score)
    check_true("speaker score > display score", speaker_score > display_score)

    # Select best device
    best = vnr.select_best_device(adr.registered_devices)
    check_eq("best device is speaker", best["device"]["device_id"], "speaker-01")
    check_true("best score > 0.5", best["score"] > 0.5)

    # Select with user proximity
    best_phone = vnr.select_best_device(adr.registered_devices, user_proximity=0.9)
    check_true("best with proximity has score", best_phone["score"] > 0)

    # Generate TTS text
    tts1 = vnr.generate_tts_text("task_completed", "Excel Report", "3 sheets, 5 charts")
    check_true("tts completed has task name", "Excel Report" in tts1)
    check_true("tts completed has result", "3 sheets" in tts1)

    tts2 = vnr.generate_tts_text("task_failed", "Video Transcode", error_message="format not supported")
    check_true("tts failed has error", "format not supported" in tts2)

    tts3 = vnr.generate_tts_text("crash_risk", error_message="memory low")
    check_true("tts crash has warning", "Warning" in tts3)

    # Optimize for TTS
    raw = "# Report `/home/user/file.txt` done **bold** [link]"
    optimized = vnr.optimize_for_tts(raw)
    check_true("optimized removes #", "#" not in optimized)
    check_true("optimized removes backtick", "`" not in optimized)
    check_true("optimized removes bold", "**" not in optimized)
    check_true("optimized removes path", "/home/user" not in optimized)

    # Long text truncation
    long_text = "a" * 300
    truncated = vnr.optimize_for_tts(long_text)
    check_eq("long text truncated to 200", len(truncated), 200)

    # Create notification
    notif = vnr.create_notification(speaker_dev, "task_completed", "Excel Report", "5 charts")
    check_eq("notif type", notif["type"], "voice_notification")
    check_eq("notif device", notif["device_id"], "speaker-01")
    check_eq("notif method", notif["method"], "tts")
    check_eq("notif priority", notif["priority"], "normal")

    # Crash risk notification (urgent)
    notif2 = vnr.create_notification(phone_dev, "crash_risk", error_message="CPU overload")
    check_eq("crash notif priority", notif2["priority"], "urgent")
    check_eq("crash notif method", notif2["method"], "tts")

    # Display notification
    notif3 = vnr.create_notification(display_dev, "task_completed", "PDF Report", "generated")
    check_eq("display notif method", notif3["method"], "tts")

    # Log has entries
    check_true("notification log has entries", len(vnr.log) >= 3)

    # Empty voice devices scenario
    empty_vnr = VoiceNotificationRelay()
    empty_best = empty_vnr.select_best_device({})
    check_true("no voice devices returns None", empty_best is None)

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
