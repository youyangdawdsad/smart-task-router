#!/usr/bin/env python3
"""
SIE Quick Test — NLU 识别率快速验证
测试 nlu_config.json 中所有意图的关键词和模式匹配效果
"""
import os
import sys
import json
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "nlu_config.json")

passed = 0
failed = 0
total = 0

def check(name, condition):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print("  PASS: {}".format(name))
    else:
        failed += 1
        print("  FAIL: {}".format(name))


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


class QuickNLU:
    """Minimal NLU engine for testing, mirrors verify_engine.py logic"""

    def __init__(self, config):
        self.intents = config.get("intents", {})
        self._compiled = {}
        for name, data in self.intents.items():
            patterns = data.get("patterns", [])
            self._compiled[name] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def parse(self, text):
        text_lower = text.lower().strip()
        best_intent = None
        best_score = 0.0
        best_method = "none"

        for name, data in self.intents.items():
            score = 0.0
            method = "none"

            # Pattern matching
            for p in self._compiled[name]:
                if p.search(text):
                    score = 0.95
                    method = "pattern"
                    break

            # Keyword matching
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
            return {"intent": "unknown", "confidence": 0.0, "match_method": "none", "tool": None, "device": None}

        intent_data = self.intents.get(best_intent, {})
        return {
            "intent": best_intent,
            "confidence": round(best_score, 2),
            "match_method": best_method,
            "tool": intent_data.get("tool"),
            "device": intent_data.get("device"),
        }


def run_tests():
    global passed, failed, total

    print("=" * 60)
    print("SIE Quick Test — NLU 识别率验证")
    print("=" * 60)

    # Load config
    config = load_config()
    nlu = QuickNLU(config)

    # ============================================================
    # 1. 配置文件完整性检查
    # ============================================================
    print("\n[1] 配置文件完整性检查")
    check("version is 3.3.0", config.get("version") == "3.3.0")
    check("has description", bool(config.get("description")))
    check("has intents", len(config.get("intents", {})) > 0)
    check("has cross_device_keywords", len(config.get("cross_device_keywords", [])) > 0)
    check("has unknown_fallback", "template" in config.get("unknown_fallback", {}))

    intents = config.get("intents", {})
    check("intent count >= 15", len(intents) >= 15)

    # Each intent has required fields
    for name, data in intents.items():
        check("intent '{}' has keywords_zh".format(name), len(data.get("keywords_zh", data.get("keywords", []))) > 0)
        check("intent '{}' has patterns".format(name), len(data.get("patterns", [])) > 0)
        check("intent '{}' has tool".format(name), bool(data.get("tool")))
        check("intent '{}' has device".format(name), bool(data.get("device")))

    # ============================================================
    # 2. 意图识别测试 — 每个 intent 至少一个 example 能正确匹配
    # ============================================================
    print("\n[2] 意图识别测试 (examples)")

    test_cases = [
        # (input_text, expected_intent, description)
                ("帮我发条短信给妈妈", "message_send", "短信发送"),
        ("看看最近的短信", "sms_read", "短信查看"),
        ("打电话给妈妈", "call_make", "拨打电话"),
        ("明天下午3点加个会议", "calendar_create", "创建日程"),
        ("今天有什么安排", "calendar_query", "查询日程"),
        ("明天早上7点叫我", "alarm_set", "设置闹钟"),
        ("明天天气怎么样", "weather_query", "查询天气"),
        ("加个待办买牛奶", "todo_manage", "待办管理"),
        ("帮我记一下这个想法", "note_manage", "笔记管理"),
        ("加个新联系人", "contact_manage", "联系人管理"),
                ("播放音乐", "media_play", "媒体控制"),
        ("打开手电筒", "device_control", "设备控制"),
        ("开客厅的灯", "home_control", "智能家居"),
        ("找一下昨天拍的照片", "photo_manage", "照片管理"),
        ("我现在在哪", "location_query", "位置查询"),
        ("给我发个通知", "notification_send", "通知发送"),
                ("写一段Python爬虫代码", "code_execute", "写代码"),
                ("搜一下人工智能", "search_info", "联网搜索"),
        ("打开这个文件", "file_read", "读取文件"),
        ("保存到文件里", "file_write", "写入文件"),
    ]

    correct = 0
    for text, expected, desc in test_cases:
        result = nlu.parse(text)
        is_correct = result["intent"] == expected
        if is_correct:
            correct += 1
        check("{}: '{}' -> {} (expected {})".format(desc, text, result["intent"], expected), is_correct)

    accuracy = correct / len(test_cases) * 100 if test_cases else 0
    print("\n  识别准确率: {}/{} ({:.1f}%)".format(correct, len(test_cases), accuracy))

    # ============================================================
    # 3. 关键词匹配测试
    # ============================================================
    print("\n[3] 关键词匹配测试")

    keyword_tests = [
                ("发短信", "message_send"),
        ("发信息", "message_send"),
        ("看短信", "sms_read"),
        ("打电话", "call_make"),
        ("加日程", "calendar_create"),
        ("查日程", "calendar_query"),
        ("设闹钟", "alarm_set"),
        ("天气", "weather_query"),
        ("待办", "todo_manage"),
        ("笔记", "note_manage"),
        ("联系人", "contact_manage"),
                ("播放", "media_play"),
        ("手电筒", "device_control"),
        ("开灯", "home_control"),
        ("照片", "photo_manage"),
        ("导航", "location_query"),
        ("通知我", "notification_send"),
                ("写代码", "code_execute"),
        ("搜索", "search_info"),
        ("打开文件", "file_read"),
    ]

    kw_correct = 0
    for keyword, expected in keyword_tests:
        result = nlu.parse(keyword)
        is_correct = result["intent"] == expected
        if is_correct:
            kw_correct += 1
        check("keyword '{}' -> {}".format(keyword, result["intent"]), is_correct)

    kw_accuracy = kw_correct / len(keyword_tests) * 100 if keyword_tests else 0
    print("\n  关键词准确率: {}/{} ({:.1f}%)".format(kw_correct, len(keyword_tests), kw_accuracy))

    # ============================================================
    # 4. 未知意图回退测试
    # ============================================================
    print("\n[4] 未知意图回退测试")

    unknown_texts = ["", "asdfghjkl", "1234567890"]
    for text in unknown_texts:
        result = nlu.parse(text)
        check("unknown '{}' -> unknown".format(text), result["intent"] == "unknown")

    # ============================================================
    # 5. 跨设备关键词测试
    # ============================================================
    print("\n[5] 跨设备关键词测试")

    cross_keywords = config.get("cross_device_keywords", [])
    check("has cross_device_keywords", len(cross_keywords) > 0)

    cross_texts = ["传到电脑", "发到手机", "同步到平板"]
    for text in cross_texts:
        matched = any(re.search(kw, text, re.IGNORECASE) for kw in cross_keywords)
        check("cross-device '{}' matches".format(text), matched)

    # ============================================================
    # 6. Tool 绑定验证 — 确保所有 tool 不是 sie_internal
    # ============================================================
    print("\n[6] Tool 绑定验证")

    for name, data in intents.items():
        tool = data.get("tool", "")
        check("intent '{}' tool is not sie_internal".format(name), "sie_internal" not in tool)

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    print("Results: {}/{} passed, {} failed".format(passed, total, failed))
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print("{} tests FAILED".format(failed))
    print("NLU 识别准确率: {:.1f}% (examples) / {:.1f}% (keywords)".format(accuracy, kw_accuracy))
    print("=" * 60)
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
