#!/usr/bin/env python3
"""
SIE Self-Evolution Test — 自我进化流程完整测试
===============================================
"""

import os
import sys
import json
import copy
import shutil
import io
from datetime import datetime

# Windows UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from sie_self_evolve import (
    SelfEvolvingNLU,
    LearnProtocol,
    AutoConfigUpdater,
    UnknownIntentHandler,
    LearningLogger,
)

passed = 0
failed = 0
total = 0
CONFIG_PATH = os.path.join(SCRIPT_DIR, "nlu_config.json")
BACKUP_PATH = os.path.join(SCRIPT_DIR, "nlu_config.json.bak_evolve_test")


def check(name, condition, detail=""):
    global passed, failed, total
    total += 1
    if condition:
        passed += 1
        print("  PASS: {}".format(name))
    else:
        failed += 1
        msg = "  FAIL: {}".format(name)
        if detail:
            msg += " -- {}".format(detail)
        print(msg)


def backup_config():
    if os.path.exists(CONFIG_PATH):
        shutil.copy2(CONFIG_PATH, BACKUP_PATH)


def restore_config():
    if os.path.exists(BACKUP_PATH):
        shutil.copy2(BACKUP_PATH, CONFIG_PATH)
        os.remove(BACKUP_PATH)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def run_tests():
    global passed, failed, total

    print("=" * 70)
    print("SIE Self-Evolution Test")
    print("=" * 70)

    backup_config()

    try:
        # [1] 初始化
        print("\n[1] 初始化测试")
        se_nlu = SelfEvolvingNLU()
        check("SelfEvolvingNLU 初始化成功", se_nlu is not None)
        check("NLU 引擎已加载", se_nlu._nlu is not None)
        check("Logger 已初始化", se_nlu.logger is not None)
        check("ConfigUpdater 已初始化", se_nlu.config_updater is not None)
        check("UnknownHandler 已初始化", se_nlu.unknown_handler is not None)

        # [2] 已知意图识别
        print("\n[2] 已知意图识别（回归测试）")
        known_cases = [
            ("帮我发条短信给妈妈", "message_send"),
            ("看看最近的短信", "sms_read"),
            ("打电话给妈妈", "call_make"),
            ("明天下午3点加个会议", "calendar_create"),
            ("今天有什么安排", "calendar_query"),
            ("明天早上7点叫我", "alarm_set"),
            ("明天天气怎么样", "weather_query"),
            ("加个待办买牛奶", "todo_manage"),
            ("帮我记一下这个想法", "note_manage"),
            ("播放音乐", "media_play"),
            ("打开手电筒", "device_control"),
            ("开客厅的灯", "home_control"),
            ("搜一下人工智能", "search_info"),
            ("帮我做个PPT", "office_work"),
        ]
        known_correct = 0
        for text, expected in known_cases:
            result = se_nlu.parse(text)
            is_correct = result["intent"] == expected
            if is_correct:
                known_correct += 1
            check("已知: '{}' -> {}".format(text, result["intent"]),
                  is_correct, "expected: {}".format(expected))
            check("  无 learn_request", result.get("learn_request") is None)
        print("  已知意图准确率: {}/{} ({:.1f}%)".format(
            known_correct, len(known_cases),
            known_correct / len(known_cases) * 100))

                        # [3] 未知意图捕获
        print("\n[3] 未知意图捕获")
        unknown_cases = [
            "帮我订个外卖",
            "帮我算一下这个数学题",
            "给我讲个笑话",
            "帮我养只猫",
            "帮我预约个牙医",
        ]
        for text in unknown_cases:
            result = se_nlu.parse(text)
            check("未知 '{}' -> unknown".format(text),
                  result["intent"] == "unknown")
            check("  生成了 learn_request",
                  result.get("learn_request") is not None)
            check("  learn_request 有 request_id",
                  bool(result.get("learn_request", {}).get("request_id")))
            check("  learn_request.input == 原文",
                  result["learn_request"]["input"] == text)

        # [4] 请教请求格式验证
        print("\n[4] 请教请求格式验证")
        request = se_nlu.create_learn_request("帮我订个外卖", context="用户在问午餐")
        check("type == 'learn_request'", request["type"] == "learn_request")
        check("有 request_id", bool(request["request_id"]))
        check("有 input", request["input"] == "帮我订个外卖")
        check("有 context", "context" in request)
        check("有 question", bool(request["question"]))
        check("有 timestamp", bool(request["timestamp"]))
        check("request_id 格式 LR-YYYYMMDD-NNN",
              request["request_id"].startswith("LR-"))

        # [5] 教学回复应用
        print("\n[5] 教学回复应用 -- 核心流程")
        learn_response = {
            "type": "learn_response",
            "request_id": request["request_id"],
            "intent": "food_order",
            "description": "订外卖/点餐",
            "keywords": ["外卖", "订餐", "点餐", "送餐", "饿了", "吃什么"],
            "patterns": ["订.*外卖", "点.*餐", "饿了"],
            "tool": "food_order",
            "device": "phone",
            "examples": ["帮我订个外卖", "点个餐", "饿了想吃东西"],
        }
        valid, errors = LearnProtocol.validate_response(learn_response)
        check("回复格式验证通过", valid, str(errors))
        success, message = se_nlu.apply_learn_response(learn_response)
        check("apply_learn_response 成功", success, message)
        config = load_config()
        check("food_order 已写入配置", "food_order" in config.get("intents", {}))
        food_entry = config["intents"].get("food_order", {})
        check("有 learned 标记", food_entry.get("learned") is True)
        check("有 learned_at", bool(food_entry.get("learned_at")))
        check("关键词含 '外卖'", "外卖" in food_entry.get("keywords", []))
        check("关键词含 '点餐'", "点餐" in food_entry.get("keywords", []))
        check("patterns 含 '订.*外卖'", "订.*外卖" in food_entry.get("patterns", []))
        check("tool == 'food_order'", food_entry.get("tool") == "food_order")
        check("device == 'phone'", food_entry.get("device") == "phone")
        check("版本号已更新", config.get("version") != "3.2.0")

        # [6] 学习后识别
        print("\n[6] 学习后识别 -- 验证学习效果")
        r1 = se_nlu.parse("帮我订个外卖")
        check("学习后: '帮我订个外卖' -> food_order",
              r1["intent"] == "food_order", "got: {}".format(r1["intent"]))
        check("  无 learn_request", r1.get("learn_request") is None)
        r2 = se_nlu.parse("饿了想吃东西")
        check("学习后: '饿了想吃东西' -> food_order",
              r2["intent"] == "food_order", "got: {}".format(r2["intent"]))
        r3 = se_nlu.parse("帮我点个餐")
        check("学习后: '帮我点个餐' -> food_order",
              r3["intent"] == "food_order", "got: {}".format(r3["intent"]))

        # [7] 回归验证
        print("\n[7] 已知意图不受影响（回归验证）")
        for text, expected in [("帮我发条短信给妈妈", "message_send"),
                                ("明天天气怎么样", "weather_query"),
                                ("打电话给妈妈", "call_make"),
                                ("播放音乐", "media_play")]:
            result = se_nlu.parse(text)
            check("回归: '{}' -> {}".format(text, expected),
                  result["intent"] == expected, "got: {}".format(result["intent"]))

        # [8] 多意图连续学习
        print("\n[8] 多意图连续学习")
        multi_learn = [
            {"type": "learn_response", "intent": "translation", "description": "翻译",
             "keywords": ["翻译", "译一下", "英文", "中文翻译"],
             "patterns": ["翻译.*", "译.*一下"], "tool": "translator", "device": "any",
             "examples": ["翻译一下这段话"]},
            {"type": "learn_response", "intent": "math_calc", "description": "数学计算",
             "keywords": ["算一下", "计算", "数学题", "等于多少"],
             "patterns": ["算.*一下", "计算.*", ".*等于.*"], "tool": "calculator",
             "device": "any", "examples": ["帮我算一下这个数学题"]},
            {"type": "learn_response", "intent": "joke_tell", "description": "讲笑话",
             "keywords": ["笑话", "讲个笑话", "逗我笑", "搞笑"],
             "patterns": ["讲.*笑话", "来.*笑话"], "tool": "entertainment",
             "device": "any", "examples": ["给我讲个笑话"]},
        ]
        for resp in multi_learn:
            success, msg = se_nlu.apply_learn_response(resp)
            check("学习 '{}' 成功".format(resp["intent"]), success, msg)
        for text, expected in [("翻译一下这段话", "translation"),
                                ("帮我算一下这个数学题", "math_calc"),
                                ("给我讲个笑话", "joke_tell")]:
            result = se_nlu.parse(text)
            check("多意图: '{}' -> {}".format(text, expected),
                  result["intent"] == expected, "got: {}".format(result["intent"]))

        # [9] 无效回复处理
        print("\n[9] 无效回复处理")
        for resp in [{}, {"type": "wrong"},
                      {"type": "learn_response", "intent": "test"},
                      {"type": "learn_response", "intent": "test", "keywords": []}]:
            success, msg = se_nlu.apply_learn_response(resp)
            check("无效回复被拒绝: {}".format(str(resp)[:40]), not success)

        # [10] 重复学习（更新）
        print("\n[10] 重复学习（更新已有 learned 意图）")
        update_resp = {
            "type": "learn_response", "intent": "food_order",
            "description": "订外卖/点餐（更新版）",
            "keywords": ["外卖", "订餐", "点餐", "送餐", "饿了", "吃什么", "美团", "饿了么"],
            "patterns": ["订.*外卖", "点.*餐", "饿了", "美团.*外卖"],
            "tool": "food_order", "device": "phone",
            "examples": ["帮我订个外卖", "点个餐", "饿了想吃东西", "用美团订外卖"],
        }
        success, msg = se_nlu.apply_learn_response(update_resp)
        check("重复学习成功（更新）", success, msg)
        result = se_nlu.parse("用美团订外卖")
        check("更新后: '用美团订外卖' -> food_order",
              result["intent"] == "food_order", "got: {}".format(result["intent"]))

        # [11] 日志记录验证
        print("\n[11] 日志记录验证")
        history = se_nlu.get_learning_history()
        check("学习历史非空", len(history) > 0)
        event_types = [h["event_type"] for h in history]
        check("包含 unknown_captured", "unknown_captured" in event_types)
        check("包含 intent_learned", "intent_learned" in event_types)
        stats = se_nlu.get_learning_stats()
        check("learned_intents 非空", len(stats.get("learned_intents", [])) > 0)
        check("total_intents_learned > 0",
              stats.get("logger_stats", {}).get("total_intents_learned", 0) > 0)
        print("  学习统计: {}".format(json.dumps(stats, ensure_ascii=False, indent=4)))

        # [12] 回滚测试
        print("\n[12] 回滚测试")
        success, msg = se_nlu.rollback_intent("food_order")
        check("回滚 food_order 成功", success, msg)
        result = se_nlu.parse("帮我订个外卖")
        check("回滚后: '帮我订个外卖' -> unknown",
              result["intent"] == "unknown", "got: {}".format(result["intent"]))
        result2 = se_nlu.parse("翻译一下这段话")
        check("回滚后其他意图不受影响",
              result2["intent"] == "translation", "got: {}".format(result2["intent"]))

        # [13] 已学习意图列表
        print("\n[13] 已学习意图列表")
        learned = se_nlu.config_updater.list_learned_intents()
        check("含 translation", "translation" in learned)
        check("含 math_calc", "math_calc" in learned)
        check("含 joke_tell", "joke_tell" in learned)
        check("不含 food_order（已回滚）", "food_order" not in learned)
        print("  已学习意图: {}".format(list(learned.keys())))

        # [14] 空输入处理
        print("\n[14] 空输入处理")
        result = se_nlu.parse("")
        check("空输入 -> unknown", result["intent"] == "unknown")
        check("空输入无 learn_request", result.get("learn_request") is None)
        result2 = se_nlu.parse("   ")
        check("纯空格 -> unknown", result2["intent"] == "unknown")
        check("纯空格无 learn_request", result2.get("learn_request") is None)

        # Summary
        print("\n" + "=" * 70)
        print("Results: {}/{} passed, {} failed".format(passed, total, failed))
        if failed == 0:
            print("ALL TESTS PASSED -- 自我进化架构验证通过！")
        else:
            print("{} tests FAILED".format(failed))
        print("=" * 70)
        return failed == 0

    finally:
        restore_config()
        print("\n[清理] 原始 nlu_config.json 已恢复")


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
