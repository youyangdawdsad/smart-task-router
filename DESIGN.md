# SIE 设计原则文档

> 智能调用引擎（Smart Invocation Engine）的架构设计原则和决策依据。

## 版本

当前版本：v3.3.0

## 核心设计原则

### 1. 配置驱动，代码不动

NLU 意图识别完全由 `nlu_config.json` 外部配置驱动。新增、修改、删除意图只需编辑 JSON 文件，无需修改 Python 代码。

**为什么这样做：**
- 意图和关键词是高频变化的业务逻辑，不应该和引擎代码耦合
- 非开发人员也能通过编辑 JSON 扩展意图
- 运行时可热加载配置，无需重启

### 2. SIE 只做调度，不自己执行

SIE 的职责是"决定谁来做"，而不是"自己去做"。所有任务最终都交给目标设备的 Agent 执行。

**为什么这样做：**
- SIE 运行在协调层，不应该有执行能力
- 避免职责混乱：调度器不应该同时是执行器
- 跨设备任务统一交给 `device_coord`，简化路由逻辑

### 3. 硬规则优先，软规则兜底

当任务涉及特定设备能力（如短信、电话、代码编写）时，直接路由到对应设备，跳过打分流程。只有在没有硬规则匹配时，才走综合评分。

**为什么这样做：**
- 硬规则是确定性的，不会出错
- 打分是概率性的，可能有偏差
- 硬规则优先可以保证关键任务的路由准确性

### 4. 双层匹配，逐级降级

NLU 匹配策略采用双层架构，按优先级逐级降级：

```
用户输入
  │
  ├─ 第一层：关键词快速通道（nlu_config.json）
  │   ├─ 正则模式匹配（最高优先级，置信度 0.95）
  │   ├─ 关键词匹配（置信度最高 0.9）
  │   └─ 模糊匹配（SequenceMatcher，阈值 0.6）
  │
  └─ 第二层：AI 语义理解 fallback（NLUClassifier）
      └─ 大模型意图分类（25+ 个意图）
```

**为什么这样做：**
- 关键词快速通道响应快（<1ms）、确定性强、无需网络，覆盖 80%+ 的常见表达
- AI 语义理解处理复杂句式、口语化表达、歧义消解，覆盖长尾场景
- `fallback_to_ai` 字段让每个意图灵活控制是否启用 AI fallback

### 5. 自我进化，持续学习

NLU 不是静态的。当遇到无法识别的意图时，SIE 会自动捕获、请教、学习、更新配置。

**为什么这样做：**
- 用户表达方式千变万化，不可能预先穷举所有关键词
- 自我进化让 NLU 能够从实际使用中持续改进
- 标准化的 LearnProtocol 确保请教和学习过程可追溯

### 6. 测试即文档

每个意图在 `nlu_config.json` 中都包含 `examples` 字段，`sie_quick_test.py` 自动验证这些示例的匹配结果。测试通过率就是 NLU 识别率。

**为什么这样做：**
- examples 既是测试用例，也是意图的使用说明
- 修改配置后立即可以验证影响范围
- 100% 通过率 = 100% 识别率，简单直观

## 意图→工具映射表

| 意图 | 描述 | 目标设备 | 工具 | fallback_to_ai |
|------|------|----------|------|----------------|
| `message_send` | 发送短信 | phone | sms | true |
| `sms_read` | 查看短信 | phone | read_sms | true |
| `call_make` | 拨打电话 | phone | call | true |
| `calendar_create` | 创建日程 | phone | calendar | true |
| `calendar_query` | 查询日程 | phone | calendar | true |
| `alarm_set` | 设置闹钟 | phone | alarm | true |
| `weather_query` | 查询天气 | any | weather | true |
| `todo_manage` | 待办管理 | phone | todo | true |
| `note_manage` | 笔记管理 | phone | note | true |
| `contact_manage` | 联系人管理 | phone | contacts | true |
| `media_play` | 媒体控制 | phone | media | true |
| `device_control` | 设备控制 | phone | miot_control_device | true |
| `home_control` | 智能家居 | phone | miot_control_device | true |
| `photo_manage` | 照片管理 | phone | photo | true |
| `location_query` | 位置查询 | any | location | true |
| `notification_send` | 发送通知 | phone | notification | true |
| `code_execute` | 代码编写 | pc | code | true |
| `search_info` | 网页搜索 | any | search | true |
| `office_work` | 办公文档 | pc | office | true |
| `booking` | 预订服务 | any | tongcheng | true |
| `file_read` | 读取文件 | phone | file | true |
| `file_write` | 写入文件 | phone | file | true |
| `timer_set` | 定时器/倒计时 | phone | timer | true |
| `tts_speak` | 语音播报 | phone | set_tts_enabled | true |
| `translate` | 翻译文本 | any | web_search | true |
| `app_manage` | 应用管理 | phone | agent_osbot_os_helper | true |
| `ai_write` | AI 内容生成 | any | agent_osbot_content_assistant | true |

## 路由优先级

路由决策按以下优先级执行：

```
1. 硬规则（设备能力强制匹配）
   ↓ 无匹配
2. 关键词快速通道（nlu_config.json 正则 + 关键词 + 模糊）
   ↓ confidence < 0.3
3. AI 语义理解 fallback（NLUClassifier 大模型分类）
   ↓ 仍无法识别
4. 自我进化（捕获未知意图 → 生成 learn_request）
   ↓
5. 引导用户重新描述
```

### 硬规则列表

| 工具 | 强制路由到 |
|------|-----------|
| sms, call, camera, location, alarm, media, screenshot | phone |
| code, ide, office | pc |

### 综合评分公式

```
score = α × capability_match + β × load_factor + γ × proximity
```

- `α = 0.5`（能力匹配权重）
- `β = 0.3`（负载均衡权重）
- `γ = 0.2`（可达性权重，基于心跳延迟分级）

## 协议格式

### LearnProtocol — 知识请教协议

**请求格式**（SIE → 大爱）：

```json
{
  "type": "learn_request",
  "request_id": "LR-20260504-001",
  "input": "用户说的话",
  "context": "当时的上下文",
  "question": "这个意图应该映射到什么工具？关键词有哪些？",
  "timestamp": "2026-05-04T00:14:00"
}
```

**回复格式**（大爱 → SIE）：

```json
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
```

### 路由决策输出格式

```json
{
  "task_id": "task-xxx",
  "intent": "message_send",
  "confidence": 0.92,
  "match_method": "keyword",
  "target_device": "phone",
  "tool": "sms",
  "score": 0.85,
  "target": "device_coord",
  "method": "cross_device"
}
```

## 模块职责

| 模块 | 职责 | 不做什么 |
|------|------|----------|
| NLU | 意图识别、置信度计算 | 不做任务执行 |
| NLUClassifier | AI 语义理解 fallback | 不做关键词匹配 |
| SelfEvolvingNLU | 未知意图捕获、学习、配置更新 | 不做路由决策 |
| LearnProtocol | 标准化请教协议格式 | 不做实际通信 |
| TaskProfiler | 任务特征提取 | 不做路由决策 |
| RoutingRules | 路由决策 | 不做任务执行 |
| LoadBalancer | 负载评估 | 不做任务分配 |
| CrashDetector | 崩溃风险评估 | 不做任务拆分执行 |
| device_coord | 跨设备任务协调 | 不做意图识别 |

## 配置文件结构

`nlu_config.json` 的顶层结构：

```json
{
  "version": "3.3.0",
  "description": "SIE NLU 配置 — 意图识别关键词表",
  "intents": {
    "<intent_name>": {
      "description": "意图描述",
      "keywords": ["关键词1", "关键词2"],
      "patterns": ["正则1", "正则2"],
      "device": "phone|pc|any",
      "tool": "工具名称",
      "examples": ["示例1", "示例2"],
      "fallback_to_ai": true
    }
  },
  "cross_device_keywords": ["跨设备关键词"],
  "unknown_fallback": {
    "action": "反问用户",
    "template": "回退模板"
  },
  "mcp_services": {
    "<service_name>": {
      "description": "服务描述",
      "intents": ["关联意图"]
    }
  }
}
```

### 字段说明

| 字段 | 必填 | 说明 |
|------|------|------|
| `description` | 是 | 意图的中文描述 |
| `keywords` | 是 | 中文关键词列表，用于快速通道匹配 |
| `patterns` | 是 | 正则表达式列表，用于模式匹配 |
| `device` | 是 | 目标设备类型：phone / pc / any |
| `tool` | 是 | 对应的工具名称 |
| `examples` | 否 | 测试示例，用于 sie_quick_test.py 验证 |
| `fallback_to_ai` | 否 | 是否启用 AI 语义理解 fallback（默认 true） |

## 版本演进

| 版本 | 关键变更 | 设计决策 |
|------|----------|----------|
| v1.0 | 五大核心模块 | 硬规则 + 软规则双层架构 |
| v2.0 | 指示器 + 崩溃检测 + 双链路 | 可观测性 + 安全性 |
| v3.0 | 全模块性能优化 | 微观优化，零功能变更 |
| v3.1 | NLU + SieLogger | 自然语言理解 + 全链路日志 |
| v3.2 | NLU 配置驱动 + 路由简化 | 配置与代码分离，职责清晰 |
| v3.3 | AI 语义理解 + 自我进化 + MCP | 双层匹配 + 持续学习 + 能力扩展 |
