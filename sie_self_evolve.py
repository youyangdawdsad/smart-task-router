#!/usr/bin/env python3
"""
SIE Self-Evolution Module — 自我进化架构
==========================================

核心能力：
1. 未知意图捕获 — NLU 识别不了时，记录并生成请教请求
2. 知识请教协议 — 标准化的 learn_request / learn_response 格式
3. 自动配置更新 — 收到教学回复后，自动写入 nlu_config.json
4. 学习日志 — 完整记录每次请教和学习过程

使用方式：
    from sie_self_evolve import SelfEvolvingNLU

    se_nlu = SelfEvolvingNLU()
    result = se_nlu.parse("帮我订个外卖")
    if result["intent"] == "unknown":
        request = se_nlu.create_learn_request("帮我订个外卖")
        # → 发送给大爱（手机端）
        # 收到回复后：
        se_nlu.apply_learn_response(response_dict)
"""

import os
import re
import json
import copy
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
        event_type: "unknown_captured" | "learn_request_sent" | "learn_response_received" | "intent_learned" | "learn_failed"
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
            elif et == "learn_request_sent":
                stats["total_requests_sent"] += 1
            elif et == "intent_learned":
                stats["total_intents_learned"] += 1
            elif et == "learn_failed":
                stats["total_learn_failed"] += 1
        stats["unique_unknown_inputs"] = len(stats["unique_unknown_inputs"])
        return stats


# ============================================================
#  Module: LearnProtocol — 知识请教协议
# ============================================================

class LearnProtocol:
    """
    标准化的请教协议格式

    请求格式 (SIE → 大爱):
    {
        "type": "learn_request",
        "request_id": "LR-20260504-001",
        "input": "用户说的话",
        "context": "当时的上下文",
        "question": "这个意图应该映射到什么工具？关键词有哪些？",
        "timestamp": "2026-05-04T00:14:00"
    }

    回复格式 (大爱 → SIE):
    {
        "type": "learn_response",
        "request_id": "LR-20260504-001",
        "intent": "新意图名",
        "description": "意图描述",
        "keywords": ["关键词列表"],
        "patterns": ["正则模式"],
        "tool": "对应工具",
        "device": "目标设备",
        "examples": ["示例语句"]
    }
    """

    @staticmethod
    def create_request(input_text, context="", question=None):
        """创建请教请求"""
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
    def validate_response(response):
        """验证教学回复的格式是否正确"""
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
        # 如果没有提供 patterns，根据 keywords 自动生成基础 patterns
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
            # 为每个关键词生成一个精确匹配模式
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
        return {"version": "3.2.0", "intents": {}}

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

        # 检查是否已存在
        if intent_name in intents:
            existing = intents[intent_name]
            # 如果已有 learned 标记，允许覆盖更新
            if existing.get("learned"):
                old_keywords = set(existing.get("keywords", []))
                new_keywords = set(intent_entry.get("keywords", []))
                # 合并关键词（去重）
                merged_keywords = list(old_keywords | new_keywords)
                existing["keywords"] = merged_keywords
                # 合并 patterns
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

        # 新增意图
        intents[intent_name] = intent_entry
        config["intents"] = intents
        # 更新版本号
        config["version"] = self._bump_version(config.get("version", "3.2.0"))
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
#  Module: UnknownIntentHandler — 未知意图处理
# ============================================================

class UnknownIntentHandler:
    """当 NLU 识别不了时，捕获并管理未知输入"""

    def __init__(self, logger=None, max_pending=50):
        self.logger = logger or LearningLogger()
        self.max_pending = max_pending
        self._pending_requests = []  # 待回复的请教请求
        self._unknown_cache = {}     # input -> count，去重计数

    def capture(self, input_text, context="", nlu_result=None):
        """
        捕获一个未知输入
        返回: learn_request dict (可直接发送给大爱)
        """
                # 去重：相同输入只生成一次请求
        cache_key = input_text.strip().lower()
        if cache_key in self._unknown_cache:
            self._unknown_cache[cache_key] += 1
            # 已经有 pending 请求，更新 context（如果新 context 非空）
            for req in self._pending_requests:
                if req["input"].strip().lower() == cache_key:
                    if context and not req.get("context"):
                        req["context"] = context
                    return req
            # 如果 pending 已清空但还在缓存，重新创建
            pass
        else:
            self._unknown_cache[cache_key] = 1

        # 限制 pending 数量
        if len(self._pending_requests) >= self.max_pending:
            # 移除最旧的
            self._pending_requests.pop(0)

        # 创建请教请求
        request = LearnProtocol.create_request(input_text, context)
        self._pending_requests.append(request)

        # 记录日志
        self.logger.log_event("unknown_captured", {
            "input": input_text,
            "context": context,
            "nlu_result": nlu_result,
            "request_id": request["request_id"],
        })

        return request

    def get_pending_requests(self):
        """获取所有待回复的请求"""
        return list(self._pending_requests)

    def mark_sent(self, request_id):
        """标记请求已发送"""
        self.logger.log_event("learn_request_sent", {
            "request_id": request_id,
        })

    def resolve(self, request_id):
        """标记请求已解决（收到回复）"""
        self._pending_requests = [
            r for r in self._pending_requests
            if r.get("request_id") != request_id
        ]

    def get_unknown_stats(self):
        """获取未知输入统计"""
        return {
            "pending_count": len(self._pending_requests),
            "unique_unknown_count": len(self._unknown_cache),
            "total_unknown_occurrences": sum(self._unknown_cache.values()),
        }


# ============================================================
#  Module: SelfEvolvingNLU — 自我进化 NLU（核心入口）
# ============================================================

class SelfEvolvingNLU:
    """
    包装现有 NLU，添加自我进化能力

    使用流程：
    1. parse(text) — 正常解析，如果 unknown 则自动捕获
    2. create_learn_request(text) — 生成请教请求
    3. apply_learn_response(response) — 应用教学回复，自动更新配置
    4. parse(text) — 再次解析，验证学习效果
    """

    def __init__(self, config_path=None, log_dir=None):
        self.config_path = config_path
        self.logger = LearningLogger(log_dir)
        self.config_updater = AutoConfigUpdater(config_path)
        self.unknown_handler = UnknownIntentHandler(self.logger)
        self._nlu = None
        self._reload_nlu()

    def _reload_nlu(self):
        """重新加载 NLU（配置更新后需要刷新）"""
        # 从 verify_engine 导入 NLU 类
        try:
            from verify_engine import NaturalLanguageUnderstanding
            self._nlu = NaturalLanguageUnderstanding(self.config_path)
        except ImportError:
            # 如果无法导入，使用内联的简化版
            self._nlu = _SimpleNLU(self.config_path)

    def parse(self, text):
        """
        解析用户输入
        如果识别为 unknown，自动捕获并记录
        """
        result = self._nlu.parse(text)

        if result.get("intent") == "unknown" and text and text.strip():
            # 自动捕获未知输入
            request = self.unknown_handler.capture(
                input_text=text,
                context="",
                nlu_result=result,
            )
            result["learn_request"] = request
            result["learn_hint"] = (
                "此意图尚未学习。已生成请教请求 [{}]，"
                "可发送给大爱获取教学回复。"
            ).format(request["request_id"])

        return result

    def create_learn_request(self, input_text, context=""):
        """手动创建请教请求"""
        return self.unknown_handler.capture(input_text, context)

    def apply_learn_response(self, response):
        """
        应用教学回复，自动更新 nlu_config.json

        参数:
            response: dict, 格式见 LearnProtocol

        返回:
            (success: bool, message: str)
        """
        # 验证回复格式
        valid, errors = LearnProtocol.validate_response(response)
        if not valid:
            self.logger.log_event("learn_failed", {
                "response": response,
                "errors": errors,
            })
            return False, "Invalid response: {}".format("; ".join(errors))

        # 转换为配置条目
        intent_name, intent_entry = LearnProtocol.response_to_config_entry(response)

        # 写入配置
        success, message = self.config_updater.add_intent(intent_name, intent_entry)

        if success:
            # 记录成功日志
            self.logger.log_event("intent_learned", {
                "request_id": response.get("request_id"),
                "intent": intent_name,
                "keywords": intent_entry.get("keywords", []),
                "tool": intent_entry.get("tool"),
                "device": intent_entry.get("device"),
            })
            # 解决 pending 请求
            request_id = response.get("request_id")
            if request_id:
                self.unknown_handler.resolve(request_id)
            # 重新加载 NLU 以使用新配置
            self._reload_nlu()
        else:
            self.logger.log_event("learn_failed", {
                "request_id": response.get("request_id"),
                "intent": intent_name,
                "error": message,
            })

        return success, message

    def get_learning_stats(self):
        """获取学习统计"""
        return {
            "logger_stats": self.logger.get_stats(),
            "unknown_stats": self.unknown_handler.get_unknown_stats(),
            "learned_intents": list(self.config_updater.list_learned_intents().keys()),
        }

    def get_learning_history(self, limit=50):
        """获取学习历史"""
        return self.logger.get_history(limit)

    def rollback_intent(self, intent_name):
        """回滚一个已学习的意图（删除）"""
        success, message = self.config_updater.remove_learned_intent(intent_name)
        if success:
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
    print("SIE Self-Evolution — 交互式学习模式")
    print("=" * 60)
    print("输入用户语句，SIE 会尝试识别。")
    print("如果无法识别，会自动生成请教请求。")
    print("输入 'stats' 查看学习统计，'history' 查看历史，'quit' 退出。")
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

        # 解析
        result = se_nlu.parse(user_input)
        print("  识别结果: {}".format(json.dumps(result, ensure_ascii=False, indent=4)))

        if result.get("intent") == "unknown":
            request = result.get("learn_request", {})
            print("\n  📤 请教请求已生成 [{}]:".format(request.get("request_id")))
            print("  {}".format(json.dumps(request, ensure_ascii=False, indent=4)))

            # 模拟大爱回复
            print("\n  模拟大爱回复 (输入 JSON 或 skip 跳过):")
            try:
                response_input = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if response_input.lower() == "skip":
                continue
            try:
                response = json.loads(response_input)
                success, msg = se_nlu.apply_learn_response(response)
                print("  结果: {} — {}".format("✅" if success else "❌", msg))
            except json.JSONDecodeError as e:
                print("  ❌ JSON 解析失败: {}".format(e))

    print("\n再见！")


if __name__ == "__main__":
    interactive_learn()
