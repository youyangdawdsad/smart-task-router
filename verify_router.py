#!/usr/bin/env python3
"""
Smart Invocation Engine - Core Logic Verification
Tests: TaskProfiler, DeviceCapability, RoutingRules, RoutingLog,
       LoadBalancer, FailoverMigration, SmartInvocationIndicator, CrashDetector
Target: 90+ assertions covering all modules
"""

import time
import json
import os
import sys
from datetime import datetime, timezone, timedelta


# ============================================================
#  Module 1: TaskProfiler
# ============================================================

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
        if not task_text or not task_text.strip():
            return self._empty_profile(task_text or "")
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
                st_env = ("phone-only" if tool in self.PHONE_TOOLS
                          else "pc-only" if tool in self.PC_TOOLS else "any")
                sub_tasks.append({
                    "id": "ST-{}".format(idx),
                    "tools": [tool],
                    "environment": st_env,
                })
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

    @staticmethod
    def _empty_profile(task_text):
        now = datetime.now()
        return {
            "task_id": "T-{}-{}".format(now.strftime("%Y%m%d"), now.strftime("%H%M%S")),
            "original_text": task_text,
            "tools_required": [],
            "complexity": "light",
            "environment": "any",
            "splittable": False,
            "urgency": "normal",
            "estimated_duration_seconds": 10,
            "sub_tasks": [],
        }


# ============================================================
#  Module 2: DeviceCapability
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
        if device_type not in ("phone", "pc"):
            raise ValueError("device_type must be 'phone' or 'pc', got '{}'".format(device_type))
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


# ============================================================
#  Module 3: RoutingRules
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


# ============================================================
#  Module 4: RoutingLog
# ============================================================

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


# ============================================================
#  Module 5: LoadBalancer
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
            return {
                "online": True,
                "consecutive_failures": 0,
                "status": device["load_status"],
            }
        new_failures = consecutive_failures + 1
        if new_failures >= self.offline_threshold:
            return {
                "online": False,
                "consecutive_failures": new_failures,
                "status": "offline",
            }
        return {
            "online": True,
            "consecutive_failures": new_failures,
            "status": device["load_status"],
        }

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
#  Module 6: FailoverMigration
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
            return {
                "level": 1, "alternative": None,
                "retry": False, "reason": "L1 max retries exceeded",
            }
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
            "reason": "migrate from {} to {}".format(
                current_device["device_id"], result["target"]
            ),
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
#  Module 7: SmartInvocationIndicator (NEW)
# ============================================================

class SmartInvocationIndicator:
    """
    智能调用指示器 — 在智能调用时提供可见的状态指示。

    功能：
    - 记录调用的生命周期（开始 → 进行中 → 完成/失败）
    - 提供结构化的日志输出，便于 UI 层展示
    - 支持通知回调，可推送到手机端大爱
    - 自动清理过期记录
    """

    STATUS_IDLE = "idle"
    STATUS_RUNNING = "running"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    MAX_HISTORY = 50

    def __init__(self):
        self._active_invocations = {}
        self._history = []
        self._invocation_counter = 0

    def start_invocation(self, task_id, target_device, task_description=""):
        """开始一次智能调用，返回 invocation_id"""
        self._invocation_counter += 1
        invocation_id = "INV-{}-{}".format(
            datetime.now().strftime("%Y%m%d%H%M%S"),
            self._invocation_counter,
        )
        record = {
            "invocation_id": invocation_id,
            "task_id": task_id,
            "target_device": target_device,
            "task_description": task_description,
            "status": self.STATUS_RUNNING,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "duration_ms": None,
            "result_summary": None,
            "error": None,
            "steps": [],
        }
        self._active_invocations[invocation_id] = record
        self._log_event(invocation_id, "STARTED", "智能调用开始: {} -> {}".format(
            task_id, target_device
        ))
        return invocation_id

    def update_step(self, invocation_id, step_name, step_status="running", detail=""):
        """更新调用步骤"""
        inv = self._active_invocations.get(invocation_id)
        if not inv:
            return False
        step = {
            "name": step_name,
            "status": step_status,
            "detail": detail,
            "timestamp": datetime.now().isoformat(),
        }
        inv["steps"].append(step)
        self._log_event(invocation_id, "STEP", "{}: {} ({})".format(
            step_name, step_status, detail
        ))
        return True

    def complete_invocation(self, invocation_id, success=True, summary="", error=None):
        """完成一次智能调用"""
        inv = self._active_invocations.get(invocation_id)
        if not inv:
            return False
        inv["status"] = self.STATUS_COMPLETED if success else self.STATUS_FAILED
        inv["completed_at"] = datetime.now().isoformat()
        inv["result_summary"] = summary
        inv["error"] = error
        # 计算耗时
        try:
            start = datetime.fromisoformat(inv["started_at"])
            end = datetime.fromisoformat(inv["completed_at"])
            inv["duration_ms"] = int((end - start).total_seconds() * 1000)
        except (ValueError, TypeError):
            inv["duration_ms"] = None
        # 移入历史
        self._history.append(inv)
        del self._active_invocations[invocation_id]
        # 清理过期历史
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
        status_label = "完成" if success else "失败"
        self._log_event(invocation_id, "FINISHED", "智能调用{}: {}".format(
            status_label, summary or error or "无详情"
        ))
        return True

    def cancel_invocation(self, invocation_id, reason=""):
        """取消一次智能调用"""
        inv = self._active_invocations.get(invocation_id)
        if not inv:
            return False
        inv["status"] = self.STATUS_CANCELLED
        inv["completed_at"] = datetime.now().isoformat()
        inv["error"] = reason or "用户取消"
        self._history.append(inv)
        del self._active_invocations[invocation_id]
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
        self._log_event(invocation_id, "CANCELLED", "智能调用已取消: {}".format(reason))
        return True

    def get_active_count(self):
        """获取当前活跃的调用数"""
        return len(self._active_invocations)

    def get_active_invocations(self):
        """获取所有活跃调用"""
        return list(self._active_invocations.values())

    def get_history(self, n=10):
        """获取最近的历史记录"""
        return self._history[-n:]

    def get_indicator_snapshot(self):
        """获取当前指示器快照，用于 UI 展示"""
        active = self.get_active_invocations()
        return {
            "active_count": len(active),
            "active_invocations": [
                {
                    "invocation_id": inv["invocation_id"],
                    "task_id": inv["task_id"],
                    "target_device": inv["target_device"],
                    "status": inv["status"],
                    "steps_count": len(inv["steps"]),
                    "started_at": inv["started_at"],
                }
                for inv in active
            ],
            "recent_history_count": len(self._history),
        }

    def _log_event(self, invocation_id, event_type, message):
        """内部日志输出（模拟日志/通知）"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_line = "[SmartInvocation] [{}] [{}] {}".format(
            timestamp, event_type, message
        )
        # 在实际运行中，这里会输出到日志系统或触发通知
        # 测试模式下静默
        return log_line


# ============================================================
#  Module 8: CrashDetector (NEW)
# ============================================================

class CrashDetector:
    """
    崩溃检测与分步执行引擎 — 在电脑端执行前检测风险，建议拆分任务。

    功能：
    - 检测操作是否可能导致系统崩溃（内存溢出、大文件处理等）
    - 评估风险等级（low / medium / high / critical）
    - 生成分步执行建议
    - 通知手机端大爱（通过回调函数）
    """

    RISK_LOW = "low"
    RISK_MEDIUM = "medium"
    RISK_HIGH = "high"
    RISK_CRITICAL = "critical"

    # 风险阈值
    LARGE_FILE_THRESHOLD_MB = 500
    HIGH_MEMORY_THRESHOLD_MB = 2048
    MAX_CONCURRENT_OPS = 5
    BATCH_SIZE_THRESHOLD = 100

    # 高风险操作关键词
    HIGH_RISK_KEYWORDS = {
        "批量处理", "全量", "所有文件", "整个目录", "递归",
        "batch", "bulk", "all files", "recursive",
    }
    MEMORY_HEAVY_KEYWORDS = {
        "视频", "图片批量", "大数据", "数据分析", "机器学习",
        "video", "big data", "machine learning", "dataset",
    }

    def __init__(self):
        self._risk_log = []
        self._notification_callback = None

    def set_notification_callback(self, callback):
        """设置通知回调函数（用于通知手机端大爱）"""
        self._notification_callback = callback

    def assess_risk(self, task_profile, target_device=None):
        """
        评估任务的崩溃风险。

        返回:
        {
            "risk_level": "low|medium|high|critical",
            "risk_factors": [...],
            "recommendations": [...],
            "should_split": False,
            "split_plan": [...],
        }
        """
        risk_factors = []
        recommendations = []
        tools = task_profile.get("tools_required", [])
        original_text = task_profile.get("original_text", "")
        complexity = task_profile.get("complexity", "light")

        # 1. 检查复杂度
        if complexity == "heavy":
            risk_factors.append({
                "type": "high_complexity",
                "severity": self.RISK_MEDIUM,
                "detail": "任务复杂度为 heavy，可能涉及大量计算",
            })
            recommendations.append("建议将任务拆分为多个子步骤执行")

        # 2. 检查关键词
        text_lower = original_text.lower()
        for kw in self.HIGH_RISK_KEYWORDS:
            if kw in text_lower:
                risk_factors.append({
                    "type": "high_risk_keyword",
                    "severity": self.RISK_HIGH,
                    "detail": "检测到高风险关键词: '{}'".format(kw),
                })
                recommendations.append("检测到批量/全量操作，建议分批处理")
                break

        for kw in self.MEMORY_HEAVY_KEYWORDS:
            if kw in text_lower:
                risk_factors.append({
                    "type": "memory_heavy",
                    "severity": self.RISK_HIGH,
                    "detail": "检测到内存密集型关键词: '{}'".format(kw),
                })
                recommendations.append("该操作可能占用大量内存，建议分步执行")
                break

                # 3. 检查工具组合风险
        heavy_tools = {"code", "office", "file"}
        tools_set = set(tools)
        if len(tools_set & heavy_tools) >= 2:
            risk_factors.append({
                "type": "tool_combination_risk",
                "severity": self.RISK_MEDIUM,
                                "detail": "多个重量级工具组合: {}".format(sorted(tools_set & heavy_tools)),
            })
            recommendations.append("多工具组合可能导致资源竞争，建议串行执行")

        # 4. 检查文件操作风险
        if "file" in tools:
            risk_factors.append({
                "type": "file_operation",
                "severity": self.RISK_LOW,
                "detail": "涉及文件操作，需注意文件大小",
            })

        # 5. 检查设备负载
        if target_device:
            load = target_device.get("load_status", "idle")
            current = target_device.get("current_tasks", 0)
            max_c = target_device.get("max_concurrent", 3)
            if load == "busy" or current >= max_c - 1:
                risk_factors.append({
                    "type": "device_overload",
                    "severity": self.RISK_MEDIUM,
                    "detail": "目标设备负载较高 (tasks={}/{})".format(current, max_c),
                })
                recommendations.append("目标设备负载较高，建议等待空闲或换设备")

        # 综合风险等级
        risk_level = self._compute_overall_risk(risk_factors)

        # 生成分步建议
        should_split = risk_level in (self.RISK_HIGH, self.RISK_CRITICAL)
        split_plan = []
        if should_split:
            split_plan = self._generate_split_plan(task_profile)

        result = {
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendations": recommendations,
            "should_split": should_split,
            "split_plan": split_plan,
        }

        # 记录日志
        self._risk_log.append({
            "task_id": task_profile.get("task_id", "unknown"),
            "timestamp": datetime.now().isoformat(),
            "risk_level": risk_level,
            "factor_count": len(risk_factors),
        })

        # 如果需要通知手机端
        if should_split and self._notification_callback:
            notification = self._build_notification(task_profile, result)
            self._notification_callback(notification)

        return result

        def get_risk_log(self, n=10):
        """获取最近的风险评估日志"""
        return self._risk_log[-n:]

    def _compute_overall_risk(self, risk_factors):
        """根据风险因子计算综合风险等级"""
        if not risk_factors:
            return self.RISK_LOW
        severity_order = {
            self.RISK_LOW: 0,
            self.RISK_MEDIUM: 1,
            self.RISK_HIGH: 2,
            self.RISK_CRITICAL: 3,
        }
        max_severity_val = max(
            severity_order.get(f["severity"], 0) for f in risk_factors
        )
        # 多个 medium 升级为 high
        medium_count = sum(
            1 for f in risk_factors if f["severity"] == self.RISK_MEDIUM
        )
        if medium_count >= 2 and max_severity_val < severity_order[self.RISK_HIGH]:
            max_severity_val = severity_order[self.RISK_HIGH]
        for level, val in severity_order.items():
            if val == max_severity_val:
                return level
        return self.RISK_LOW

    def _generate_split_plan(self, task_profile):
        """生成分步执行计划"""
        plan = []
        sub_tasks = task_profile.get("sub_tasks", [])
        if sub_tasks:
            for st in sub_tasks:
                plan.append({
                    "step": st["id"],
                    "tools": st["tools"],
                    "environment": st["environment"],
                    "action": "在{}设备上执行: {}".format(
                        st["environment"], ", ".join(st["tools"])
                    ),
                })
        else:
            # 无法自动拆分时，给出通用建议
            tools = task_profile.get("tools_required", [])
            for i, tool in enumerate(tools, 1):
                env = ("phone-only" if tool in TaskProfiler.PHONE_TOOLS
                       else "pc-only" if tool in TaskProfiler.PC_TOOLS else "any")
                plan.append({
                    "step": "S-{}".format(i),
                    "tools": [tool],
                    "environment": env,
                    "action": "步骤 {}: 在{}设备上执行 {}".format(i, env, tool),
                })
        return plan

    def _build_notification(self, task_profile, risk_result):
        """构建通知消息"""
        return {
            "type": "crash_risk_warning",
            "task_id": task_profile.get("task_id", "unknown"),
            "risk_level": risk_result["risk_level"],
            "message": "检测到任务 '{}' 可能存在崩溃风险 (等级: {})，建议拆分为 {} 个步骤分步执行。".format(
                task_profile.get("original_text", "")[:50],
                risk_result["risk_level"],
                len(risk_result["split_plan"]),
            ),
            "split_plan": risk_result["split_plan"],
            "recommendations": risk_result["recommendations"],
            "timestamp": datetime.now().isoformat(),
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
    phone_busy = DeviceCapability.create_device(
        "phone-02", "phone", load_status="busy", current_tasks=3
    )
    phone_offline = DeviceCapability.create_device("phone-03", "phone", online=False)
    phone_slow = DeviceCapability.create_device(
        "phone-04", "phone", heartbeat_latency_ms=6000
    )
    phone_medium = DeviceCapability.create_device(
        "phone-05", "phone", heartbeat_latency_ms=3500
    )

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

    # Empty input
    p_empty = profiler.analyze("")
    check_eq("empty input = any env", p_empty["environment"], "any")
    check_eq("empty input = light", p_empty["complexity"], "light")

    p_none = profiler.analyze(None)
    check_eq("None input = any env", p_none["environment"], "any")

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

    # Invalid device type
    try:
        DeviceCapability.create_device("bad", "tablet")
        check_true("invalid device type raises error", False)
    except ValueError:
        check_true("invalid device type raises error", True)

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
    l2_limit = fm2.level2_migrate_device(
        task_p, phone_offline, [phone_offline, other_phone]
    )
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

    # -- Module 7: SmartInvocationIndicator --
    print("\n[Module 7] SmartInvocationIndicator")

    indicator = SmartInvocationIndicator()

    # Start invocation
    inv_id = indicator.start_invocation("T-001", "phone-01", "发短信给妈妈")
    check_true("invocation started", inv_id.startswith("INV-"))
    check_eq("active count = 1", indicator.get_active_count(), 1)

    # Update step
    ok = indicator.update_step(inv_id, "routing", "completed", "路由到 phone-01")
    check_true("step update ok", ok)

    ok2 = indicator.update_step(inv_id, "sending", "running", "正在发送...")
    check_true("second step update ok", ok2)

    # Snapshot
    snap = indicator.get_indicator_snapshot()
    check_eq("snapshot active_count", snap["active_count"], 1)
    check_eq("snapshot steps_count", snap["active_invocations"][0]["steps_count"], 2)

    # Complete
    ok3 = indicator.complete_invocation(inv_id, success=True, summary="短信已发送")
    check_true("invocation completed", ok3)
    check_eq("active count = 0", indicator.get_active_count(), 0)
    check_eq("history count = 1", len(indicator.get_history()), 1)

    # History entry has duration
    hist = indicator.get_history(1)[0]
    check_true("history has duration_ms", hist["duration_ms"] is not None)
    check_eq("history status completed", hist["status"], SmartInvocationIndicator.STATUS_COMPLETED)

    # Cancel invocation
    inv_id2 = indicator.start_invocation("T-002", "pc-01", "写代码")
    ok4 = indicator.cancel_invocation(inv_id2, "用户取消")
    check_true("invocation cancelled", ok4)
    check_eq("active count = 0 after cancel", indicator.get_active_count(), 0)

    # History overflow
    for i in range(55):
        iid = indicator.start_invocation("T-overflow-{}".format(i), "pc-01")
        indicator.complete_invocation(iid, success=True, summary="done")
    check_true("history capped at 50", len(indicator._history) <= 50)

    # Non-existent invocation
    ok_bad = indicator.update_step("INV-nonexistent", "step", "running")
    check_true("update non-existent returns False", not ok_bad)

    ok_bad2 = indicator.complete_invocation("INV-nonexistent")
    check_true("complete non-existent returns False", not ok_bad2)

    # -- Module 8: CrashDetector --
    print("\n[Module 8] CrashDetector")

    cd = CrashDetector()

    # Low risk: simple task
    simple_profile = profiler.analyze("发短信")
    risk1 = cd.assess_risk(simple_profile)
    check_eq("simple task risk=low", risk1["risk_level"], CrashDetector.RISK_LOW)
    check_true("simple task no split", not risk1["should_split"])

    # Medium risk: heavy complexity
    heavy_profile = profiler.analyze("帮我写代码做个PPT再拍张照然后发短信通知再搜索资料")
    risk2 = cd.assess_risk(heavy_profile)
    check_in("heavy task has medium+ risk", risk2["risk_level"],
             [CrashDetector.RISK_MEDIUM, CrashDetector.RISK_HIGH, CrashDetector.RISK_CRITICAL])

    # High risk: batch processing keyword
    batch_profile = profiler.analyze("批量处理所有文件")
    risk3 = cd.assess_risk(batch_profile)
    check_in("batch task has high+ risk", risk3["risk_level"],
             [CrashDetector.RISK_HIGH, CrashDetector.RISK_CRITICAL])
    check_true("batch task should split", risk3["should_split"])
    check_true("batch task has split_plan", len(risk3["split_plan"]) > 0)

    # High risk: memory heavy keyword
    memory_profile = profiler.analyze("处理大数据集")
    risk4 = cd.assess_risk(memory_profile)
    check_in("memory-heavy task has high+ risk", risk4["risk_level"],
             [CrashDetector.RISK_HIGH, CrashDetector.RISK_CRITICAL])

    # Device overload risk
    busy_device = DeviceCapability.create_device(
        "pc-busy", "pc", load_status="busy", current_tasks=3
    )
    risk5 = cd.assess_risk(profiler.analyze("写代码"), target_device=busy_device)
    check_true("overloaded device has risk factors", len(risk5["risk_factors"]) > 0)

    # Notification callback
    notifications = []
    cd2 = CrashDetector()
    cd2.set_notification_callback(lambda n: notifications.append(n))
    cd2.assess_risk(batch_profile)
    check_true("notification sent for high risk", len(notifications) == 1)
    check_eq("notification type", notifications[0]["type"], "crash_risk_warning")
    check_true("notification has split_plan", len(notifications[0]["split_plan"]) > 0)

    # Risk log
    risk_log = cd.get_risk_log()
    check_true("risk log has entries", len(risk_log) > 0)

    # Multiple medium risks upgrade to high
    multi_medium = profiler.analyze("帮我写代码做个PPT再拍张照然后发短信通知再搜索资料")
    risk6 = cd.assess_risk(multi_medium)
    # heavy complexity + tool combination risk = 2 mediums -> should upgrade
    check_true("multi-medium upgrades risk",
               risk6["risk_level"] in [CrashDetector.RISK_HIGH, CrashDetector.RISK_CRITICAL])

    # -- Module 9: Edge Cases --
    print("\n[Module 9] Edge Cases")

    # Empty tools -> any environment, light complexity
    empty_profile = profiler.analyze("你好")
    check_eq("empty tools = any env", empty_profile["environment"], "any")
    check_eq("empty tools = light", empty_profile["complexity"], "light")
    check_eq("empty tools no sub_tasks", empty_profile["sub_tasks"], [])

    # Score threshold
    phone_very_slow = DeviceCapability.create_device(
        "phone-vs", "phone", load_status="busy", heartbeat_latency_ms=8000
    )
    code_p = profiler.analyze("写代码")
    route_low = RoutingRules.route(code_p, [phone_very_slow])
    check_eq("low score returns no_suitable_device",
             route_low.get("status"), "no_suitable_device")

    # High risk operation detection
    check_true("refund is high risk", fm.is_high_risk("refund"))
    check_true("delete_irreversible is high risk", fm.is_high_risk("delete_irreversible"))
    check_true("normal op not high risk", not fm.is_high_risk("read_file"))

    # Multiple hard rules
    multi_profile = profiler.analyze("发短信写代码")
    route_multi = RoutingRules.route(multi_profile, [phone, pc])
    check_eq("multi hard rule code wins (alphabetical)",
             route_multi["target"], "pc-01")

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

    # CrashDetector: no risk for calendar task
    cal_profile = profiler.analyze("查看日历")
    risk_cal = cd.assess_risk(cal_profile)
    check_eq("calendar task risk=low", risk_cal["risk_level"], CrashDetector.RISK_LOW)

    # SmartInvocationIndicator: get_active_invocations returns list
    active_list = indicator.get_active_invocations()
    check_eq("no active invocations", len(active_list), 0)

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
    sys.exit(0 if success else 1)
