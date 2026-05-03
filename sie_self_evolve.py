#!/usr/bin/env python3
"""
SIE Self-Evolution Module — 自我进化架构 (v3.4.0)
==================================================

核心能力：
1. 未知意图批量捕获 — NLU 识别不了时，缓存到本地，攒够 3-5 个后一次性请教
2. 知识请教协议 — 标准化的 batch_learn_request / batch_learn_response 格式
3. 自动配置更新 — 收到教学回复后，自动写入 nlu_config.json
4. 本地兜底日志 — device_coord 不通时记录到 pending_learn.jsonl，连接恢复后批量请教
5. 路由结果 LRU 缓存 — 相同/相似输入跳过 NLU，直接返回缓存结果（5 分钟有效期）
6. 心跳检测复用 miclaw device_list — 不再自己实现心跳协议

使用方式：
    from sie_self_evolve import SelfEvolvingNLU, RouteCache

    se_nlu = SelfEvolvingNLU()
    result = se_nlu.parse("帮我订个外卖")
    if result["intent"] == "unknown":
        # 自动缓存，攒够后可批量请教
        pass

    # 路由缓存
    cache = RouteCache()
    cached = cache.get("帮我订个外卖")
    if cached:
        # 直接使用缓存结果
        pass
"""

import os
import re
import json
import copy
import hashlib
import time
from collections import OrderedDict
from datetime import datetime


# ============================================================
#  Module: LearningLogger — 学习日志
# ============================================================

class LearningLogger:
    """记录每次请教和学习的过程"""

    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = os.path.join(os.path.expanduser("~"), ".sie_logs")
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self._log_file = os.path.join(log_dir, "sie_learning.jsonl")

    def log_event(self, event_type, data):
        """
        event_type: "unknown_captured" | "batch_learn_request_sent" |
                    "batch_learn_response_received" | "intent_learned" | "learn_failed"
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "data": data,
        }
        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def get_history(self, limit=50):
        """读取最近的学习历史"""
        if not os.path.exists(self._log_file):
            return []
        entries = []
        with open(self._log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries[-limit:]

    def get_stats(self):
        """获取学习统计"""
        history = self.get_history(limit=1000)
        stats = {
            "total_unknown_captured": 0,
            "total_requests_sent": 0,
            "total_intents_learned": 0,
            "total_learn_failed": 0,
            "unique_unknown_inputs": set(),
        }
        for entry in history:
            et = entry.get("event_type", "")
            if et == "unknown_captured":
                stats["total_unknown_captured"] += 1
                stats["unique_unknown_inputs"].add(entry["data"].get("input", ""))
            elif et in ("batch_learn_request_sent", "learn_request_sent"):
                stats["total_requests_sent"] += 1
            elif et == "intent_learned":
                stats["total_intents_learned"] += 1
            elif et == "learn_failed":
                stats["total_learn_failed"] += 1
        stats["unique_unknown_inputs"] = len(stats["unique_unknown_inputs"])
        return stats


# ============================================================
#  Module: LocalFallbackLogger — 本地兜底日志 (v3.4.0)
# ============================================================

class LocalFallbackLogger:
    """
    device_coord 不通时，将未知意图记录到本地日志。
    连接恢复后可批量读取并请教。
    """

    def __init__(self, log_path=None):
        if log_path is None:
            log_path = os.path.join(
                os.path.expanduser("~"), ".sie_logs", "pending_learn.jsonl"
            )
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def record(self, input_text, context="", nlu_result=None):
        """记录一个未知意图到本地兜底日志"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "input": input_text,
            "context": context,
            "nlu_result": nlu_result,
            "status": "pending",
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry

    def get_pending(self):
        """读取所有待处理的未知意图"""
        if not os.path.exists(self.log_path):
            return []
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if entry.get("status") == "pending":
                            entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        return entries

    def mark_resolved(self, input_text):
        """标记某个未知意图已解决（更新状态）"""
        if not os.path.exists(self.log_path):
            return
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if entry.get("input") == input_text and entry.get("status") == "pending":
                            entry["status"] = "resolved"
                            entry["resolved_at"] = datetime.now().isoformat()
                        entries.append(entry)
                    except json.JSONDecodeError:
                        continue
        with open(self.log_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def clear_resolved(self):
        """清理已解决的记录，只保留 pending"""
        if not os.path.exists(self.log_path):
            return
        entries = self.get_pending()
        with open(self.log_path, "w", encoding="utf-8") as f:
            for entry in entries:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def get_stats(self):
        """获取兜底日志统计"""
        if not os.path.exists(self.log_path):
            return {"pending": 0, "resolved": 0, "total": 0}
        pending = 0
        resolved = 0
        with open(self.log_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if entry.get("status") == "pending":
                            pending += 1
                        elif entry.get("status") == "resolved":
                            resolved += 1
                    except json.JSONDecodeError:
                        continue
        return {"pending": pending, "resolved": resolved, "total": pending + resolved}


# ============================================================
#  Module: RouteCache — 路由结果 LRU 缓存 (v3.4.0)
# ============================================================

class RouteCache:
    """
    LRU 缓存：相同或相似的用户输入直接返回上次的路由结果。

    策略：
    - 缓存键：用户输入的 MD5 哈希
    - 相似度匹配：语义相似度 > 0.9 的输入视为相同（SequenceMatcher）
    - 有效期：5 分钟（可配置）
    - 缓存容量：最多 200 条
    - 缓存命中时跳过 NLU，直接返回路由结果
    """

    def __init__(self, ttl_seconds=300, max_size=200, similarity_threshold=0.9):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self.similarity_threshold = similarity_threshold
        self._cache = OrderedDict()  # hash -> (result, timestamp)
        self._input_map = {}  # hash -> input_text (用于相似度比较)
        self._hits = 0
        self._misses = 0

    @staticmethod
    def _hash_input(text):
        """计算输入的 MD5 哈希"""
        normalized = text.strip().lower()
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    @staticmethod
    def _similarity(a, b):
        """计算两个字符串的相似度（SequenceMatcher）"""
        from difflib import SequenceMatcher
        return SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def get(self, input_text):
        """
        查找缓存
        返回: (result_dict, hit: bool)
        """
        key = self._hash_input(input_text)
        now = time.time()

        # 精确匹配
        if key in self._cache:
            result, ts = self._cache[key]
            if now - ts < self.ttl_seconds:
                # 移到末尾（LRU）
                self._cache.move_to_end(key)
                self._hits += 1
                return result, True
            else:
                # 过期，删除
                del self._cache[key]
                self._input_map.pop(key, None)

        # 相似度匹配（遍历缓存，找相似输入）
        for cached_key, (result, ts) in list(self._cache.items()):
            if now - ts >= self.ttl_seconds:
                # 过期，清理
                del self._cache[cached_key]
                self._input_map.pop(cached_key, None)
                continue
            cached_input = self._input_map.get(cached_key, "")
            if cached_input and self._similarity(input_text, cached_input) >= self.similarity_threshold:
                self._cache.move_to_end(cached_key)
                self._hits += 1
                return result, True

        self._misses += 1
        return None, False

    def put(self, input_text, result):
        """存入缓存"""
        key = self._hash_input(input_text)

        # 如果已存在，更新
        if key in self._cache:
            self._cache[key] = (result, time.time())
            self._cache.move_to_end(key)
            return

        # 超过容量，淘汰最旧的
        while len(self._cache) >= self.max_size:
            oldest_key, _ = self._cache.popitem(last=False)
            self._input_map.pop(oldest_key, None)

        self._cache[key] = (result, time.time())
        self._input_map[key] = input_text

    def clear(self):
        """清空缓存"""
        self._cache.clear()
        self._input_map.clear()

    def invalidate_on_config_change(self):
        """配置变更时清空缓存（路由可能变化）"""
        self.clear()

    def get_stats(self):
        """获取缓存统计"""
        total = self._hits + self._misses
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total, 4) if total > 0 else 0.0,
            "ttl_seconds": self.ttl_seconds,
        }


# ============================================================
#  Module: LearnProtocol — 知识请教协议 (v3.4.0 批量模式)
# ============================================================

class LearnProtocol:
    """
    标准化的请教协议格式（v3.4.0 升级为批量模式）

    批量请求格式 (SIE → 大爱):
    {
        "type": "batch_learn_request",
        "request_id": "BLR-20260504-001",
        "items": [
            {"input": "用户说的话1", "context": "...", "capture_count": 3},
            {"input": "用户说的话2", "context": "", "capture_count": 1}
        ],
        "question": "这些意图应该映射到什么工具？关键词有哪些？",
        "timestamp": "2026-05-04T00:14:00"
    }

    批量回复格式 (大爱 → SIE):
    {
        "type": "batch_learn_response",
        "request_id": "BLR-20260504-001",
        "results": [
            {
                "input": "用户说的话1",
                "intent": "新意图名",
                "description": "意图描述",
                "keywords": ["关键词列表"],
                "patterns": ["正则模式"],
                "tool": "对应工具",
                "device": "目标设备",
                "examples": ["示例语句"]
            }
        ]
    }
    """

    @staticmethod
    def create_batch_request(items, question=None):
        """
        创建批量请教请求

        items: list of dict, 每个 dict 包含 input, context, capture_count
        """
        now = datetime.now()
        request_id = "BLR-{}-{:03d}".format(
            now.strftime("%Y%m%d"),
            now.microsecond % 1000
        )
        if question is None:
            inputs_str = "、".join(["「{}」".format(item["input"]) for item in items[:5]])
            question = (
                "用户说了 {} 等 {} 条输入，但当前 NLU 无法识别。"
                "请告诉我：每个意图应该叫什么名字？关键词有哪些？对应什么工具？目标设备是什么？"
            ).format(inputs_str, len(items))

        return {
            "type": "batch_learn_request",
            "request_id": request_id,
            "items": items,
            "question": question,
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def create_request(input_text, context="", question=None):
        """创建单条请教请求（兼容旧接口）"""
        now = datetime.now()
        request_id = "LR-{}-{:03d}".format(
            now.strftime("%Y%m%d"),
            now.microsecond % 1000
        )
        if question is None:
            question = (
                "用户说了「{}」，但当前 NLU 无法识别。"
                "请告诉我：这个意图应该叫什么名字？"
                "关键词有哪些？对应什么工具？目标设备是什么？"
            ).format(input_text)

        return {
            "type": "learn_request",
            "request_id": request_id,
            "input": input_text,
            "context": context,
            "question": question,
            "timestamp": now.isoformat(),
        }

    @staticmethod
    def validate_batch_response(response):
        """验证批量教学回复的格式"""
        errors = []
        if not isinstance(response, dict):
            return False, ["Response must be a dict"]
        if response.get("type") != "batch_learn_response":
            errors.append("Missing or wrong 'type' (expected 'batch_learn_response')")
        if not response.get("request_id"):
            errors.append("Missing 'request_id'")
        results = response.get("results", [])
        if not results or not isinstance(results, list):
            errors.append("Missing or invalid 'results' (must be non-empty list)")
        else:
            for i, item in enumerate(results):
                if not item.get("intent"):
                    errors.append("results[{}]: missing 'intent'".format(i))
                if not item.get("keywords") or not isinstance(item["keywords"], list):
                    errors.append("results[{}]: missing or invalid 'keywords'".format(i))
                if not item.get("tool"):
                    errors.append("results[{}]: missing 'tool'".format(i))
                if not item.get("device"):
                    errors.append("results[{}]: missing 'device'".format(i))
        return len(errors) == 0, errors

    @staticmethod
    def validate_response(response):
        """验证单条教学回复的格式（兼容旧接口）"""
        errors = []
        if not isinstance(response, dict):
            return False, ["Response must be a dict"]
        if response.get("type") != "learn_response":
            errors.append("Missing or wrong 'type' (expected 'learn_response')")
        if not response.get("intent"):
            errors.append("Missing 'intent'")
        if not response.get("keywords") or not isinstance(response["keywords"], list):
            errors.append("Missing or invalid 'keywords' (must be non-empty list)")
        if not response.get("tool"):
            errors.append("Missing 'tool'")
        if not response.get("device"):
            errors.append("Missing 'device'")
        return len(errors) == 0, errors

    @staticmethod
    def response_to_config_entry(response):
        """将教学回复转换为 nlu_config.json 中的意图条目"""
        intent_name = response["intent"]
        keywords = response.get("keywords", [])
        patterns = response.get("patterns", [])
        if not patterns:
            patterns = LearnProtocol._auto_generate_patterns(keywords)
        entry = {
            "description": response.get("description", ""),
            "keywords": keywords,
            "patterns": patterns,
            "device": response.get("device", "any"),
            "tool": response.get("tool", "unknown"),
            "examples": response.get("examples", []),
            "learned": True,
            "learned_at": datetime.now().isoformat(),
        }
        return intent_name, entry

    @staticmethod
    def _auto_generate_patterns(keywords):
        """根据关键词自动生成正则模式"""
        patterns = []
        for kw in keywords:
            escaped = re.escape(kw)
            patterns.append(escaped)
        return patterns


# ============================================================
#  Module: AutoConfigUpdater — 自动配置更新
# ============================================================

class AutoConfigUpdater:
    """自动将新学到的意图写入 nlu_config.json"""

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "nlu_config.json"
            )
        self.config_path = config_path

    def load_config(self):
        """加载当前配置"""
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "3.4.0", "intents": {}}

    def save_config(self, config):
        """保存配置到文件"""
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def add_intent(self, intent_name, intent_entry):
        """
        添加新意图到配置
        返回: (success: bool, message: str)
        """
        config = self.load_config()
        intents = config.get("intents", {})

        if intent_name in intents:
            existing = intents[intent_name]
            if existing.get("learned"):
                old_keywords = set(existing.get("keywords", []))
                new_keywords = set(intent_entry.get("keywords", []))
                merged_keywords = list(old_keywords | new_keywords)
                existing["keywords"] = merged_keywords
                old_patterns = existing.get("patterns", [])
                new_patterns = intent_entry.get("patterns", [])
                existing["patterns"] = list(set(old_patterns + new_patterns))
                existing["learned_at"] = intent_entry.get("learned_at", existing.get("learned_at"))
                if intent_entry.get("description"):
                    existing["description"] = intent_entry["description"]
                self.save_config(config)
                return True, "Intent '{}' updated (merged {} new keywords)".format(
                    intent_name, len(new_keywords - old_keywords)
                )
            else:
                return False, "Intent '{}' already exists (not learned). Cannot overwrite built-in intent.".format(intent_name)

        intents[intent_name] = intent_entry
        config["intents"] = intents
        config["version"] = self._bump_version(config.get("version", "3.4.0"))
        self.save_config(config)
        return True, "Intent '{}' learned and added to config".format(intent_name)

    def remove_learned_intent(self, intent_name):
        """移除一个已学习的意图"""
        config = self.load_config()
        intents = config.get("intents", {})
        if intent_name not in intents:
            return False, "Intent '{}' not found".format(intent_name)
        entry = intents[intent_name]
        if not entry.get("learned"):
            return False, "Cannot remove built-in intent '{}'".format(intent_name)
        del intents[intent_name]
        config["intents"] = intents
        self.save_config(config)
        return True, "Learned intent '{}' removed".format(intent_name)

    def list_learned_intents(self):
        """列出所有已学习的意图"""
        config = self.load_config()
        learned = {}
        for name, data in config.get("intents", {}).items():
            if data.get("learned"):
                learned[name] = data
        return learned

    @staticmethod
    def _bump_version(version_str):
        """版本号 minor +1"""
        parts = version_str.split(".")
        if len(parts) >= 2:
            try:
                parts[1] = str(int(parts[1]) + 1)
                parts[2] = "0"
            except ValueError:
                pass
        return ".".join(parts)


# ============================================================
#  Module: UnknownIntentHandler — 未知意图处理 (v3.4.0 批量模式)
# ============================================================

class UnknownIntentHandler:
    """
    当 NLU 识别不了时，批量捕获并管理未知输入。

    v3.4.0 变更：
    - 从逐条请求改为批量模式：攒够 threshold 个后一次性请教
    - 增加本地兜底：device_coord 不通时记录到 pending_learn.jsonl
    """

    def __init__(self, logger=None, max_pending=10, threshold=3,
                 local_fallback=None):
        self.logger = logger or LearningLogger()
        self.max_pending = max_pending
        self.threshold = threshold
        self.local_fallback = local_fallback
        self._pending_requests = []
        self._unknown_cache = {}  # input -> count
        self._batch_buffer = []   # 批量缓冲区

    def capture(self, input_text, context="", nlu_result=None):
        """
        捕获一个未知输入
        返回: learn_request dict (单条兼容格式)
        """
        cache_key = input_text.strip().lower()
        if cache_key in self._unknown_cache:
            self._unknown_cache[cache_key] += 1
            for req in self._pending_requests:
                if req["input"].strip().lower() == cache_key:
                    if context and not req.get("context"):
                        req["context"] = context
                    req["capture_count"] = self._unknown_cache[cache_key]
                    return req
        else:
            self._unknown_cache[cache_key] = 1

        if len(self._pending_requests) >= self.max_pending:
            self._pending_requests.pop(0)

        request = LearnProtocol.create_request(input_text, context)
        request["capture_count"] = 1
        self._pending_requests.append(request)

        # 添加到批量缓冲区
        self._batch_buffer.append({
            "input": input_text,
            "context": context,
            "capture_count": 1,
            "nlu_result": nlu_result,
        })

        self.logger.log_event("unknown_captured", {
            "input": input_text,
            "context": context,
            "nlu_result": nlu_result,
            "request_id": request["request_id"],
        })

        # 记录本地兜底日志
        if self.local_fallback:
            self.local_fallback.record(input_text, context, nlu_result)

        return request

    def should_batch_send(self):
        """检查是否攒够了批量请教的数量"""
        return len(self._batch_buffer) >= self.threshold

    def get_batch_items(self):
        """获取批量缓冲区的所有条目并清空缓冲区"""
        items = list(self._batch_buffer)
        self._batch_buffer = []
        return items

    def create_batch_request(self):
        """创建批量请教请求"""
        items = self.get_batch_items()
        if not items:
            return None
        return LearnProtocol.create_batch_request(items)

    def get_pending_requests(self):
        """获取所有待回复的请求"""
        return list(self._pending_requests)

    def mark_sent(self, request_id):
        """标记请求已发送"""
        self.logger.log_event("batch_learn_request_sent", {
            "request_id": request_id,
        })

    def resolve(self, request_id):
        """标记请求已解决（收到回复）"""
        self._pending_requests = [
            r for r in self._pending_requests
            if r.get("request_id") != request_id
        ]

    def resolve_by_input(self, input_text):
        """根据输入文本标记已解决"""
        cache_key = input_text.strip().lower()
        self._pending_requests = [
            r for r in self._pending_requests
            if r.get("input", "").strip().lower() != cache_key
        ]
        if self.local_fallback:
            self.local_fallback.mark_resolved(input_text)

    def get_unknown_stats(self):
        """获取未知输入统计"""
        return {
            "pending_count": len(self._pending_requests),
            "batch_buffer_count": len(self._batch_buffer),
            "threshold": self.threshold,
            "unique_unknown_count": len(self._unknown_cache),
            "total_unknown_occurrences": sum(self._unknown_cache.values()),
        }


# ============================================================
#  Module: SelfEvolvingNLU — 自我进化 NLU（核心入口）(v3.4.0)
# ============================================================

class SelfEvolvingNLU:
    """
    包装现有 NLU，添加自我进化能力

    v3.4.0 新增：
    - 批量自学习：未知意图攒够 threshold 个后一次性请教
    - 本地兜底：device_coord 不通时记录到本地日志
    - 路由结果 LRU 缓存：相同/相似输入跳过 NLU
    - 心跳检测复用 miclaw device_list

    使用流程：
    1. parse(text) — 先查缓存，未命中再走 NLU
    2. 如果 unknown，自动捕获到批量缓冲区
    3. 攒够 threshold 个后，create_batch_request() 一次性请教
    4. apply_batch_learn_response(response) — 批量应用教学回复
    5. parse(text) — 再次解析，验证学习效果
    """

    def __init__(self, config_path=None, log_dir=None):
        self.config_path = config_path
        self.logger = LearningLogger(log_dir)
        self.config_updater = AutoConfigUpdater(config_path)

        # 加载配置中的批量学习参数
        batch_config = self._load_batch_config()

        # 本地兜底日志
        fallback_path = batch_config.get("local_fallback_path", "~/.sie_logs/pending_learn.jsonl")
        fallback_path = os.path.expanduser(fallback_path)
        self.local_fallback = LocalFallbackLogger(fallback_path) if batch_config.get("local_fallback_enabled", True) else None

        self.unknown_handler = UnknownIntentHandler(
            self.logger,
            max_pending=batch_config.get("max_pending", 10),
            threshold=batch_config.get("threshold", 3),
            local_fallback=self.local_fallback,
        )

        # 路由缓存
        cache_config = self._load_cache_config()
        self.route_cache = RouteCache(
            ttl_seconds=cache_config.get("ttl_seconds", 300),
            max_size=cache_config.get("max_size", 200),
            similarity_threshold=cache_config.get("similarity_threshold", 0.9),
        ) if cache_config.get("enabled", True) else None

        self._nlu = None
        self._reload_nlu()

    def _load_batch_config(self):
        """从 nlu_config.json 加载批量学习配置"""
        config_path = self.config_path
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "nlu_config.json"
            )
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("batch_learn", {})
        return {}

    def _load_cache_config(self):
        """从 nlu_config.json 加载路由缓存配置"""
        config_path = self.config_path
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "nlu_config.json"
            )
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("route_cache", {})
        return {}

    def _reload_nlu(self):
        """重新加载 NLU（配置更新后需要刷新）"""
        try:
            from verify_engine import NaturalLanguageUnderstanding
            self._nlu = NaturalLanguageUnderstanding(self.config_path)
        except ImportError:
            self._nlu = _SimpleNLU(self.config_path)

    def parse(self, text):
        """
        解析用户输入
        先查路由缓存，未命中再走 NLU
        """
        if not text or not text.strip():
            return {"intent": "unknown", "confidence": 0.0, "tool": None, "device": None,
                    "match_method": "none"}

        # 1. 查路由缓存
        if self.route_cache:
            cached_result, hit = self.route_cache.get(text)
            if hit:
                cached_result["cache_hit"] = True
                return cached_result

        # 2. 走 NLU
        result = self._nlu.parse(text)

        # 3. 如果识别为 unknown，自动捕获
        if result.get("intent") == "unknown" and text and text.strip():
            request = self.unknown_handler.capture(
                input_text=text,
                context="",
                nlu_result=result,
            )
            result["learn_request"] = request
            result["learn_hint"] = (
                "此意图尚未学习。已缓存到批量缓冲区 [{}/{}]，"
                "攒够后将一次性请教大爱。"
            ).format(
                len(self.unknown_handler._batch_buffer),
                self.unknown_handler.threshold,
            )

        # 4. 缓存路由结果（非 unknown 的结果才缓存）
        if self.route_cache and result.get("intent") != "unknown":
            self.route_cache.put(text, copy.deepcopy(result))

        return result

    def create_learn_request(self, input_text, context=""):
        """手动创建单条请教请求（兼容旧接口）"""
        return self.unknown_handler.capture(input_text, context)

    def create_batch_learn_request(self):
        """
        创建批量请教请求
        返回: batch_learn_request dict，可发送给大爱
        """
        return self.unknown_handler.create_batch_request()

    def should_batch_send(self):
        """检查是否攒够了批量请教的数量"""
        return self.unknown_handler.should_batch_send()

    def apply_learn_response(self, response):
        """
        应用单条教学回复（兼容旧接口）
        """
        valid, errors = LearnProtocol.validate_response(response)
        if not valid:
            self.logger.log_event("learn_failed", {
                "response": response,
                "errors": errors,
            })
            return False, "Invalid response: {}".format("; ".join(errors))

        intent_name, intent_entry = LearnProtocol.response_to_config_entry(response)
        success, message = self.config_updater.add_intent(intent_name, intent_entry)

        if success:
            self.logger.log_event("intent_learned", {
                "request_id": response.get("request_id"),
                "intent": intent_name,
                "keywords": intent_entry.get("keywords", []),
                "tool": intent_entry.get("tool"),
                "device": intent_entry.get("device"),
            })
            request_id = response.get("request_id")
            if request_id:
                self.unknown_handler.resolve(request_id)
            # 清空路由缓存（配置已变更）
            if self.route_cache:
                self.route_cache.invalidate_on_config_change()
            self._reload_nlu()
        else:
            self.logger.log_event("learn_failed", {
                "request_id": response.get("request_id"),
                "intent": intent_name,
                "error": message,
            })

        return success, message

    def apply_batch_learn_response(self, response):
        """
        应用批量教学回复

        参数:
            response: dict, 格式见 LearnProtocol (batch_learn_response)

        返回:
            (success_count: int, fail_count: int, messages: list)
        """
        valid, errors = LearnProtocol.validate_batch_response(response)
        if not valid:
            self.logger.log_event("learn_failed", {
                "response": response,
                "errors": errors,
            })
            return 0, len(errors), ["Invalid response: {}".format("; ".join(errors))]

        results = response.get("results", [])
        success_count = 0
        fail_count = 0
        messages = []

        for item in results:
            intent_name, intent_entry = LearnProtocol.response_to_config_entry(item)
            success, message = self.config_updater.add_intent(intent_name, intent_entry)

            if success:
                success_count += 1
                self.logger.log_event("intent_learned", {
                    "request_id": response.get("request_id"),
                    "intent": intent_name,
                    "keywords": intent_entry.get("keywords", []),
                    "tool": intent_entry.get("tool"),
                    "device": intent_entry.get("device"),
                })
                # 标记对应的 pending 请求已解决
                input_text = item.get("input", "")
                if input_text:
                    self.unknown_handler.resolve_by_input(input_text)
            else:
                fail_count += 1
                messages.append(message)

        # 清空路由缓存（配置已变更）
        if self.route_cache and success_count > 0:
            self.route_cache.invalidate_on_config_change()
            self._reload_nlu()

        return success_count, fail_count, messages

    def get_pending_fallback_items(self):
        """
        从本地兜底日志读取待处理的未知意图
        用于 device_coord 恢复后批量请教
        """
        if not self.local_fallback:
            return []
        return self.local_fallback.get_pending()

    def get_learning_stats(self):
        """获取学习统计"""
        stats = {
            "logger_stats": self.logger.get_stats(),
            "unknown_stats": self.unknown_handler.get_unknown_stats(),
            "learned_intents": list(self.config_updater.list_learned_intents().keys()),
        }
        if self.route_cache:
            stats["route_cache_stats"] = self.route_cache.get_stats()
        if self.local_fallback:
            stats["fallback_stats"] = self.local_fallback.get_stats()
        return stats

    def get_learning_history(self, limit=50):
        """获取学习历史"""
        return self.logger.get_history(limit)

    def rollback_intent(self, intent_name):
        """回滚一个已学习的意图（删除）"""
        success, message = self.config_updater.remove_learned_intent(intent_name)
        if success:
            if self.route_cache:
                self.route_cache.invalidate_on_config_change()
            self._reload_nlu()
        return success, message


# ============================================================
#  内联简化版 NLU（当 verify_engine 不可用时的后备）
# ============================================================

class _SimpleNLU:
    """简化版 NLU，仅用于 self_evolve 模块独立测试"""

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "nlu_config.json"
            )
        self.config = self._load_config(config_path)
        self.intents = self.config.get("intents", {})
        self._compiled = {}
        for name, data in self.intents.items():
            patterns = data.get("patterns", [])
            self._compiled[name] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def _load_config(self, path):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"intents": {}}

    def parse(self, text):
        if not text or not text.strip():
            return {"intent": "unknown", "confidence": 0.0, "tool": None, "device": None,
                    "match_method": "none"}
        text_lower = text.lower().strip()
        best_intent = None
        best_score = 0.0
        best_method = "none"
        for name, data in self.intents.items():
            score = 0.0
            method = "none"
            for p in self._compiled.get(name, []):
                if p.search(text):
                    score = 0.95
                    method = "pattern"
                    break
            if score < 0.95:
                keywords = data.get("keywords_zh", data.get("keywords", []))
                matched = [kw for kw in keywords if kw.lower() in text_lower]
                if matched:
                    kw_score = min(0.9, len(matched) / max(len(keywords), 1) * 3)
                    if kw_score > score:
                        score = kw_score
                        method = "keyword"
            if score > best_score:
                best_score = score
                best_intent = name
                best_method = method
        if best_score < 0.1:
            return {"intent": "unknown", "confidence": 0.0, "match_method": "none",
                    "tool": None, "device": None}
        intent_data = self.intents.get(best_intent, {})
        return {
            "intent": best_intent,
            "confidence": round(best_score, 2),
            "match_method": best_method,
            "tool": intent_data.get("tool"),
            "device": intent_data.get("device"),
        }


# ============================================================
#  CLI 入口 — 交互式学习模式
# ============================================================

def interactive_learn():
    """交互式学习模式 — 模拟 SIE 向大爱请教的完整流程"""
    se_nlu = SelfEvolvingNLU()

    print("=" * 60)
    print("SIE Self-Evolution — 交互式学习模式 (v3.4.0)")
    print("=" * 60)
    print("输入用户语句，SIE 会尝试识别。")
    print("如果无法识别，会自动缓存到批量缓冲区。")
    print("输入 'stats' 查看学习统计，'history' 查看历史，")
    print("'batch' 查看批量缓冲区，'send' 模拟批量发送，'quit' 退出。")
    print()

    while True:
        try:
            user_input = input("用户说: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue
        if user_input.lower() == "quit":
            break
        if user_input.lower() == "stats":
            stats = se_nlu.get_learning_stats()
            print(json.dumps(stats, ensure_ascii=False, indent=2))
            continue
        if user_input.lower() == "history":
            history = se_nlu.get_learning_history()
            for h in history:
                print(json.dumps(h, ensure_ascii=False))
            continue
        if user_input.lower() == "batch":
            items = se_nlu.unknown_handler._batch_buffer
            print("批量缓冲区 ({} 个):".format(len(items)))
            for item in items:
                print("  - {} (捕获 {} 次)".format(item["input"], item["capture_count"]))
            print("是否攒够: {}".format("是 ✅" if se_nlu.should_batch_send() else "否 (还差 {})".format(
                se_nlu.unknown_handler.threshold - len(items))))
            continue
        if user_input.lower() == "send":
            batch_req = se_nlu.create_batch_learn_request()
            if batch_req:
                print("\n📤 批量请教请求:")
                print(json.dumps(batch_req, ensure_ascii=False, indent=4))
                print("\n模拟大爱批量回复 (输入 JSON 或 skip 跳过):")
                try:
                    response_input = input("  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    break
                if response_input.lower() != "skip":
                    try:
                        response = json.loads(response_input)
                        s, f, msgs = se_nlu.apply_batch_learn_response(response)
                        print("  结果: 成功 {} 个, 失败 {} 个".format(s, f))
                        if msgs:
                            for m in msgs:
                                print("  ❌ {}".format(m))
                    except json.JSONDecodeError as e:
                        print("  ❌ JSON 解析失败: {}".format(e))
            else:
                print("  批量缓冲区为空，没有待发送的请求")
            continue

        # 解析
        result = se_nlu.parse(user_input)
        print("  识别结果: {}".format(json.dumps(result, ensure_ascii=False, indent=4)))

        if result.get("intent") == "unknown":
            batch_info = "批量缓冲区: {}/{}".format(
                len(se_nlu.unknown_handler._batch_buffer),
                se_nlu.unknown_handler.threshold,
            )
            print("\n  📤 已缓存到批量缓冲区 ({})".format(batch_info))
            if se_nlu.should_batch_send():
                print("  ✅ 攒够了！输入 'send' 可批量请教大爱")

    print("\n再见！")


if __name__ == "__main__":
    interactive_learn()
