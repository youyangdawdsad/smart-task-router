#!/usr/bin/env python3
"""SIE v3.2.0 integration script - line-level modifications to verify_engine.py"""
import os, sys, re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ENGINE_PATH = os.path.join(SCRIPT_DIR, "verify_engine.py")

with open(ENGINE_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Add imports
content = content.replace(
    "from datetime import datetime, timezone, timedelta\n",
    "from datetime import datetime, timezone, timedelta\nfrom difflib import SequenceMatcher\n",
    1
)

# 2. Insert NLU module before TaskProfiler
NLU_MODULE = r'''# ============================================================
#  Module 13: NaturalLanguageUnderstanding (NLU)
# ============================================================

class NaturalLanguageUnderstanding:
    """NLU module - loads nlu_config.json, keyword+regex matching, tool/device binding"""

    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "nlu_config.json")
        self.config = self._load_config(config_path)
        self.intents = self.config.get("intents", {})
        self._compiled_patterns = {}
        for intent_name, intent_data in self.intents.items():
            patterns = intent_data.get("patterns", [])
            self._compiled_patterns[intent_name] = [
                re.compile(p, re.IGNORECASE) for p in patterns
            ]

    def _load_config(self, config_path):
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return self._default_config()

    def _default_config(self):
        return {"version": "3.2.0", "intents": {}}

    def parse(self, text):
        if not text or not text.strip():
            return {"intent": "unknown", "confidence": 0.0, "tool": None, "device": None,
                    "match_method": "none", "entities": {}}
        text_lower = text.lower().strip()
        best_match = None
        best_score = 0.0
        for intent_name, intent_data in self.intents.items():
            score = 0.0
            match_method = "none"
            # Pattern matching (highest priority)
            patterns = self._compiled_patterns.get(intent_name, [])
            for pattern in patterns:
                if pattern.search(text):
                    score = max(score, 0.95)
                    match_method = "pattern"
                    break
            # Keyword matching
            if score < 0.95:
                keywords = intent_data.get("keywords", [])
                matched_keywords = [kw for kw in keywords if kw.lower() in text_lower]
                if matched_keywords:
                    kw_score = min(0.9, len(matched_keywords) / max(len(keywords), 1) * 3)
                    if kw_score > score:
                        score = kw_score
                        match_method = "keyword"
            # Fuzzy matching
            if score < 0.5:
                keywords = intent_data.get("keywords", [])
                for kw in keywords:
                    ratio = SequenceMatcher(None, text_lower, kw.lower()).ratio()
                    if ratio > 0.6:
                        fuzzy_score = ratio * 0.7
                        if fuzzy_score > score:
                            score = fuzzy_score
                            match_method = "fuzzy"
            if score > best_score:
                best_score = score
                best_match = {
                    "intent": intent_name,
                    "confidence": round(score, 4),
                    "tool": intent_data.get("tool"),
                    "device": intent_data.get("device"),
                    "match_method": match_method,
                    "entities": self._extract_entities(text),
                }
        if best_match is None or best_match["confidence"] < 0.1:
            return {"intent": "unknown", "confidence": 0.0, "tool": None, "device": None,
                    "match_method": "none", "entities": {}}
        return best_match

    def _extract_entities(self, text):
        entities = {}
        time_patterns = [
            (r'(明天|今天|后天|大后天)', "date"),
            (r'(早上|上午|中午|下午|晚上|凌晨)', "time_of_day"),
            (r'(\d{1,2})[点时:](\d{0,2})', "time"),
            (r'(\d+)(分钟|秒|小时)', "duration"),
        ]
        for pattern, entity_type in time_patterns:
            match = re.search(pattern, text)
            if match:
                entities[entity_type] = match.group(0)
        name_match = re.search(r'(?:给|跟|和|向|对)([^\s，,。.！!？?]{1,4})', text)
        if name_match:
            entities["person"] = name_match.group(1)
        return entities

    def detect_cross_device(self, text):
        cross_keywords = [
            "传到", "发到", "同步到", "复制到", "移动到",
            "传给", "发给", "传到电脑", "发到电脑", "传到手机", "发到手机",
        ]
        text_lower = text.lower()
        for kw in cross_keywords:
            if kw in text_lower:
                return True
        cross_patterns = [
            r'(?:传|发|同步|复制|移动).*(?:到|给).*(?:电脑|手机|平板|设备)',
            r'(?:把|将).*(?:传|发|同步|复制|移动).*(?:到|给).*(?:电脑|手机|平板|设备)',
        ]
        for pattern in cross_patterns:
            if re.search(pattern, text):
                return True
        return False


'''

content = content.replace(
    "#  Module 1: TaskProfiler (unchanged from v1.2)\n# ============================================================\n\nclass TaskProfiler:",
    NLU_MODULE + "#  Module 1: TaskProfiler (v3.2 NLU integrated)\n# ============================================================\n\nclass TaskProfiler:",
    1
)

# 3. Add __init__ to TaskProfiler
content = content.replace(
    "    # 预编译：按关键词长度降序排列，避免短词误匹配，且只遍历一次\n    _sorted_keywords = None\n\n    @classmethod",
    "    # 预编译：按关键词长度降序排列，避免短词误匹配，且只遍历一次\n    _sorted_keywords = None\n\n    def __init__(self, nlu=None):\n        self.nlu = nlu\n\n    @classmethod",
    1
)

# 4. Update analyze() to use NLU
content = content.replace(
    "    def analyze(self, task_text):\n        tools = set()\n        text_lower = task_text.lower()\n        self._ensure_sorted()\n        for kw_lower, tool in self._sorted_keywords:\n            if kw_lower in text_lower:\n                tools.add(tool)\n        tools_list = sorted(tools)",
    "    def analyze(self, task_text):\n        tools = set()\n        text_lower = task_text.lower()\n        nlu_result = None\n        # 优先使用 NLU 解析\n        if self.nlu is not None:\n            nlu_result = self.nlu.parse(task_text)\n            if nlu_result and nlu_result.get(\"tool\") and nlu_result[\"confidence\"] >= 0.3:\n                tools.add(nlu_result[\"tool\"])\n        # 回退到关键词匹配（始终执行，作为补充）\n        self._ensure_sorted()\n        for kw_lower, tool in self._sorted_keywords:\n            if kw_lower in text_lower:\n                tools.add(tool)\n        tools_list = sorted(tools)",
    1
)

# 5. Update return value to include nlu field
content = content.replace(
    '        return {\n            "task_id": task_id, "original_text": task_text,\n            "tools_required": tools_list, "complexity": complexity,\n            "environment": environment, "splittable": splittable,\n            "urgency": urgency, "estimated_duration_seconds": estimated_duration,\n            "sub_tasks": sub_tasks,\n        }',
    '        result = {\n            "task_id": task_id, "original_text": task_text,\n            "tools_required": tools_list, "complexity": complexity,\n            "environment": environment, "splittable": splittable,\n            "urgency": urgency, "estimated_duration_seconds": estimated_duration,\n            "sub_tasks": sub_tasks,\n        }\n        if nlu_result:\n            result["nlu"] = nlu_result\n        return result',
    1
)

# 6. Add cross-device detection to RoutingRules
content = content.replace(
    "    @staticmethod\n    def route(task_profile, devices):\n        candidates = [d for d in devices if d[\"online\"]]",
    """    # Cross-device keywords
    CROSS_DEVICE_KEYWORDS = [
        "传到", "发到", "同步到", "复制到", "移动到",
        "传给", "发给", "传到电脑", "发到电脑", "传到手机", "发到手机",
    ]

    @staticmethod
    def is_cross_device_task(task_text):
        text_lower = task_text.lower()
        for kw in RoutingRules.CROSS_DEVICE_KEYWORDS:
            if kw in text_lower:
                return True
        cross_patterns = [
            r'(?:传|发|同步|复制|移动).*(?:到|给).*(?:电脑|手机|平板|设备)',
            r'(?:把|将).*(?:传|发|同步|复制|移动).*(?:到|给).*(?:电脑|手机|平板|设备)',
        ]
        for pattern in cross_patterns:
            if re.search(pattern, task_text):
                return True
        return False

    @staticmethod
    def route(task_profile, devices):
        # Cross-device task -> route to device_coord
        original_text = task_profile.get("original_text", "")
        if RoutingRules.is_cross_device_task(original_text):
            return {
                "target": "device_coord",
                "method": "cross_device",
                "reason": "Cross-device task, route to device_coord",
            }
        candidates = [d for d in devices if d["online"]]""",
    1
)

# 7. Update run_tests profiler initialization
content = content.replace(
    "    profiler = TaskProfiler()\n",
    "    nlu = NaturalLanguageUnderstanding()\n    profiler = TaskProfiler(nlu=nlu)\n",
    1
)

# 8. Add new test modules before Summary
NEW_TESTS = '''
    # ============================================================
    #  Module 13: NaturalLanguageUnderstanding (NLU)
    # ============================================================
    print("\\n[Module 13] NaturalLanguageUnderstanding")

    nlu_result1 = nlu.parse("帮我发条短信给妈妈")
    check_eq("nlu sms intent", nlu_result1["intent"], "message_send")
    check_eq("nlu sms tool", nlu_result1["tool"], "sms")
    check_eq("nlu sms device", nlu_result1["device"], "phone")
    check_true("nlu sms confidence > 0.3", nlu_result1["confidence"] > 0.3)
    check_eq("nlu sms match_method", nlu_result1["match_method"], "keyword")

    nlu_result2 = nlu.parse("打开手电筒")
    check_eq("nlu device_control intent", nlu_result2["intent"], "device_control")
    check_eq("nlu device_control tool", nlu_result2["tool"], "miot_control_device")
    check_eq("nlu pattern match", nlu_result2["match_method"], "pattern")
    check_true("nlu pattern confidence >= 0.9", nlu_result2["confidence"] >= 0.9)

    nlu_result3 = nlu.parse("明天天气怎么样")
    check_eq("nlu weather intent", nlu_result3["intent"], "weather_query")
    check_eq("nlu weather tool", nlu_result3["tool"], "weather")

    nlu_result4 = nlu.parse("运行Python代码")
    check_eq("nlu code intent", nlu_result4["intent"], "code_execute")
    check_eq("nlu code tool", nlu_result4["tool"], "code")
    check_eq("nlu code device", nlu_result4["device"], "pc")

    nlu_result5 = nlu.parse("帮我做个PPT")
    check_eq("nlu office intent", nlu_result5["intent"], "office_work")
    check_eq("nlu office tool", nlu_result5["tool"], "office")

    nlu_result6 = nlu.parse("播放音乐")
    check_eq("nlu media intent", nlu_result6["intent"], "media_play")
    check_eq("nlu media tool", nlu_result6["tool"], "media")

    nlu_result7 = nlu.parse("设个明天早上7点的闹钟")
    check_eq("nlu alarm intent", nlu_result7["intent"], "alarm_set")
    check_eq("nlu alarm tool", nlu_result7["tool"], "alarm")

    nlu_result8 = nlu.parse("附近的餐厅在哪")
    check_eq("nlu location intent", nlu_result8["intent"], "location_query")
    check_eq("nlu location tool", nlu_result8["tool"], "location")

    nlu_result9 = nlu.parse("帮我搜索一下Python教程")
    check_eq("nlu search intent", nlu_result9["intent"], "search_info")
    check_eq("nlu search tool", nlu_result9["tool"], "search")

    nlu_result10 = nlu.parse("帮我订一张明天去北京的机票")
    check_eq("nlu booking intent", nlu_result10["intent"], "booking")
    check_eq("nlu booking tool", nlu_result10["tool"], "tongcheng")

    nlu_empty = nlu.parse("")
    check_eq("nlu empty input", nlu_empty["intent"], "unknown")
    check_eq("nlu empty confidence", nlu_empty["confidence"], 0.0)

    nlu_weather_kw = nlu.parse("今天天气真好啊")
    check_eq("nlu weather keyword match", nlu_weather_kw["intent"], "weather_query")

    nlu_entity = nlu.parse("明天下午3点提醒我开会")
    check_true("nlu has entities", len(nlu_entity.get("entities", {})) > 0)

    check_true("cross device: 传到电脑", nlu.detect_cross_device("把文件传到电脑"))
    check_true("cross device: 发到手机", nlu.detect_cross_device("发到手机"))
    check_true("cross device: 同步到平板", nlu.detect_cross_device("同步到平板"))
    check_true("not cross device: 发短信", not nlu.detect_cross_device("帮我发短信"))
    check_true("not cross device: 查天气", not nlu.detect_cross_device("查天气"))

    # ============================================================
    #  Module 14: TaskProfiler NLU Integration
    # ============================================================
    print("\\n[Module 14] TaskProfiler NLU Integration")

    p_nlu1 = profiler.analyze("帮我发条短信给妈妈")
    check_in("nlu profiler sms", "sms", p_nlu1["tools_required"])
    check_true("nlu profiler has nlu field", "nlu" in p_nlu1)
    check_eq("nlu profiler nlu intent", p_nlu1["nlu"]["intent"], "message_send")

    p_nlu2 = profiler.analyze("打开手电筒")
    check_in("nlu profiler device_control", "miot_control_device", p_nlu2["tools_required"])

    p_nlu3 = profiler.analyze("明天天气怎么样")
    check_in("nlu profiler weather", "weather", p_nlu3["tools_required"])

    p_nlu4 = profiler.analyze("运行Python代码")
    check_in("nlu profiler code", "code", p_nlu4["tools_required"])

    p_nlu5 = profiler.analyze("帮我做个PPT")
    check_in("nlu profiler office", "office", p_nlu5["tools_required"])

    p_nlu6 = profiler.analyze("帮我写一段Python代码然后发短信通知我")
    check_true("nlu profiler cross-device still splittable", p_nlu6["splittable"])
    check_in("nlu profiler has code", "code", p_nlu6["tools_required"])
    check_in("nlu profiler has sms", "sms", p_nlu6["tools_required"])

    # ============================================================
    #  Module 15: Routing Logic Fix
    # ============================================================
    print("\\n[Module 15] Routing Logic Fix")

    cross_profile = profiler.analyze("把文件传到电脑")
    cross_route = RoutingRules.route(cross_profile, [phone, pc])
    check_eq("cross device routes to device_coord", cross_route["target"], "device_coord")
    check_eq("cross device method", cross_route["method"], "cross_device")

    cross_profile2 = profiler.analyze("把这个照片发到手机")
    cross_route2 = RoutingRules.route(cross_profile2, [phone, pc])
    check_eq("cross device to phone routes to device_coord", cross_route2["target"], "device_coord")

    normal_profile = profiler.analyze("发短信")
    normal_route = RoutingRules.route(normal_profile, [phone, pc])
    check_eq("normal sms still routes to phone", normal_route["target"], "phone-01")
    check_eq("normal sms via hard_rule", normal_route["method"], "hard_rule")

    code_profile2 = profiler.analyze("写代码")
    code_route2 = RoutingRules.route(code_profile2, [phone, pc])
    check_eq("normal code still routes to pc", code_route2["target"], "pc-01")

    check_true("is_cross_device: 传到电脑", RoutingRules.is_cross_device_task("把文件传到电脑"))
    check_true("is_cross_device: 发到手机", RoutingRules.is_cross_device_task("发到手机"))
    check_true("is_cross_device: 同步到平板", RoutingRules.is_cross_device_task("同步到平板"))
    check_true("not is_cross_device: 发短信", not RoutingRules.is_cross_device_task("帮我发短信"))
    check_true("not is_cross_device: 查天气", not RoutingRules.is_cross_device_task("查天气"))
    check_true("not is_cross_device: 写代码", not RoutingRules.is_cross_device_task("写代码"))

    # ============================================================
    #  Module 16: SIE Constraints
    # ============================================================
    print("\\n[Module 16] SIE Constraints")

    weather_nlu = nlu.parse("明天天气怎么样")
    check_eq("weather tool is external", weather_nlu["tool"], "weather")
    check_true("weather tool is not sie_internal", weather_nlu["tool"] != "sie_internal")

    device_nlu = nlu.parse("打开蓝牙")
    check_eq("device tool is external", device_nlu["tool"], "miot_control_device")
    check_true("device tool is not sie_internal", device_nlu["tool"] != "sie_internal")

    sms_nlu = nlu.parse("发短信给妈妈")
    check_eq("sms tool is external", sms_nlu["tool"], "sms")
    check_true("sms tool is not sie_internal", sms_nlu["tool"] != "sie_internal")

    config_path = os.path.join(SCRIPT_DIR, "nlu_config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
        check_true("config has no cross_device intent", "cross_device" not in config.get("intents", {}))
        check_true("config delete_cross_device_rule", config.get("routing_rules", {}).get("delete_cross_device_rule", False))
        check_true("config no_sms_send", config.get("sie_constraints", {}).get("no_sms_send", False))
        check_true("config no_weather_query", config.get("sie_constraints", {}).get("no_weather_query", False))
        check_true("config no_device_control", config.get("sie_constraints", {}).get("no_device_control", False))
        check_true("config no_side_effects", config.get("sie_constraints", {}).get("no_side_effects", False))

'''

content = content.replace(
    "    # -- Summary --",
    NEW_TESTS + "    # -- Summary --",
    1
)

# 9. Update file header comment
content = content.replace(
    "Target: 200+ assertions covering all 12 modules (v3.0 optimized)",
    "Target: 300+ assertions covering all 16 modules (v3.2.0 NLU integrated)"
)

# Write back
with open(ENGINE_PATH, "w", encoding="utf-8") as f:
    f.write(content)

print("Done! verify_engine.py updated to v3.2.0")
print("File size: {} bytes".format(os.path.getsize(ENGINE_PATH)))
