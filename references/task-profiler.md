# 任务画像器（Task Profiler）

## 概述

任务画像器是路由引擎的第一步，负责分析用户任务并生成结构化的 TaskProfile。它回答三个问题：
1. 这个任务需要什么能力？
2. 它必须在哪类设备上跑？
3. 它能不能拆？

## 关键词 → 工具映射表

| 工具类型 | 关键词（中/英） | 设备约束 |
|----------|-----------------|----------|
| sms | 短信/消息/text message/sms | phone-only |
| call | 打电话/来电/通话/call/phone | phone-only |
| camera | 拍照/相机/拍照发给/camera/photo | phone-only |
| location | 定位/在哪/位置/地址/位置信息/location/GPS | phone-only |
| calendar | 日历/日程/会议/提醒/calendar/event | any |
| alarm | 闹钟/定时提醒/alarm | phone-only |
| media | 播放/暂停/音乐/音量/media/music | phone-only |
| notification | 通知/推送/notification | phone-only |
| code | 写代码/运行/脚本/code/script/python | pc-only |
| ide | IDE/编辑器/开发环境/VSCode/IDE | pc-only |
| file | 文件/保存/写入/导出/file/save/write | any |
| browser | 浏览器/网页/打开网站/web/browse | any |
| office | PPT/Word/Excel/文档/presentation/spreadsheet | pc-only |
| text | 长文/文章/报告/总结/writing/article | any |

## 复杂度评估规则

### Light（轻量，score=1）
- 单次工具调用即可完成
- 关键词模式："查一下X"、"几点了"、"帮我设个闹钟"

### Medium（中等，score=2）
- 2~4 步工具调用链
- 关键词模式："先查X再做Y"、"搜索X然后整理"
- 包含隐含的多步骤逻辑（如"发短信告诉我妈…"→先查联系人→再发短信）

### Heavy（重度，score=3）
- 5 步以上工具调用
- 大量文件处理/文本生成
- 关键词模式："完整报告"、"全部整理"、"批量处理"

## 环境约束判定

IF 任务涉及 sms/call/camera/location/alarm/media/notification AND 不涉及 code/ide/office → phone-only
IF 任务涉及 code/ide/office AND 不涉及 sms/call/camera/location/alarm/media/notification → pc-only
IF 同时涉及两端工具 → any（可拆分）
其他情况 → any

## 可拆分性判定

满足以下任一条件 → splittable=true：
1. 任务中出现"然后"、"接着"、"再"等连接词，且前后涉及不同设备
2. TaskProfile 中 tools_required 跨越 phone-only 和 pc-only
3. 任务包含多个独立的动词短语（如"查X + 写Y + 发Z"）

## 紧急度判定

- 用户明确说"马上"、"立刻"、"赶紧"、"急" → urgent
- 任务涉及 alarm/闹钟 → urgent
- 任务涉及 call/打电话 → urgent（时效性）
- 其他 → normal

## TaskProfile 输出规范

```json
{
  "task_id": "T-{YYYYMMDD}-{序号}",
  "original_text": "用户原始输入",
  "tools_required": ["tool1", "tool2"],
  "complexity": "light|medium|heavy",
  "environment": "phone-only|pc-only|any",
  "splittable": false,
  "urgency": "urgent|normal",
  "estimated_duration_seconds": 30,
  "sub_tasks": []
}
```

当 splittable=true 时，sub_tasks 数组非空，每个子任务格式：
```json
{"id": "ST-{序号}", "text": "子任务描述", "tools": ["tool1"], "environment": "phone-only|pc-only|any", "depends_on": []}
```
