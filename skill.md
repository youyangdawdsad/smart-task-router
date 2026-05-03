# 智能调用引擎（Smart Invocation Engine）

根据任务类型、设备能力、负载状态，自动将任务分配到最优设备执行。当检测到执行风险时，智能拆分任务并通知协作设备分步处理。

**版本**: 3.3.1
**前置条件**: 至少2台设备在线（通过 device_chat 协议注册，或自动发现）

## 概述

智能调用引擎（SIE）是多设备协作场景下的任务调度技能。它在 v1.x 路由引擎的基础上，新增九大核心能力：

1. **NLU 配置驱动**：意图识别完全由 `nlu_config.json` 外部配置驱动，支持 27 个意图，每个意图 4-12 个关键词 + 正则 patterns，新增/修改意图只需编辑配置文件
2. **AI 语义理解（NLUClassifier）**：NLU 从关键词匹配升级到 AI 语义理解，关键词匹配作为快速通道，AI 语义理解作为 fallback，大幅提升识别准确率
3. **自我进化架构（SelfEvolvingNLU）**：未知意图自动捕获 → 批量缓存 → 一次性请教 → 自动更新配置，实现 NLU 的持续进化
4. **全链路日志（SieLogger）**：记录完整调用链路（触发→NLU→匹配→路由→执行），支持四级日志、按任务 ID 追踪、文件持久化
5. **智能调用指示器**：每次智能调用决策时，生成可见的执行指示，让用户实时感知引擎的工作状态
6. **崩溃风险检测**：电脑端实时监控执行环境，当检测到可能导致崩溃的操作时，自动通知手机端将任务拆分为更小的步骤分步执行
7. **双链路通信**：在 device_chat 主链路之外，新增网络心跳副链路，确保设备间通信始终可用
8. **自动设备注册**：新设备登录账号后自动发现、探测能力、接入引擎，无需手动配置
9. **MCP 服务集成**：支持接入第三方 MCP 服务（如 mcd-mcp、高德地图、天气查询等），扩展引擎能力边界
10. **路由结果缓存（LRU Cache）**：相同或相似的用户输入直接返回上次的路由结果，跳过 NLU 重新计算，缓存有效期 5 分钟
11. **批量自学习 + 本地兜底**：未知意图攒够 3-5 个后一次性请教，device_coord 不通时记录到本地日志，连接恢复后批量请教

## 核心能力

1. **自然语言理解（NLU）**：基于 `nlu_config.json` 配置驱动的意图识别，支持 27 个意图、正则模式匹配、关键词匹配、模糊匹配
2. **AI 语义理解（NLUClassifier）**：关键词快速通道无法匹配时，fallback 到 AI 语义理解，通过大模型进行意图分类
3. **自我进化架构（SelfEvolvingNLU）**：未知意图批量捕获、知识请教协议（LearnProtocol）、自动配置更新、本地兜底日志
4. **全链路日志（SieLogger）**：记录每次调用的触发条件、匹配结果、执行过程和最终输出
5. **任务分析（Task Profiling）**：解析任务描述，提取任务类型、所需工具、资源需求、优先级等特征
6. **设备能力匹配（Device Capability Matching）**：维护各设备的能力画像，包括硬件配置、已安装工具、网络状态等
7. **路由决策（Routing Decision）**：综合任务特征和设备能力，输出意图→工具映射，设备选择完全交给 miclaw device_coord
8. **负载均衡（Load Balancing）**：避免单设备过载，合理分配任务到多设备
9. **故障转移（Failover & Migration）**：设备离线或执行失败时，自动迁移到备选设备
10. **智能调用指示器（Invocation Indicator）**：每次调用决策产生可见反馈，让用户知道引擎在工作
11. **崩溃风险检测（Crash Detector）**：监控执行环境，高风险操作自动拆分并通知协作设备
12. **双链路通信（Dual Link）**：主链路（device_chat）+ 副链路（复用 miclaw 设备发现），确保通信可靠
13. **自动设备注册（Auto Device Registration）**：新设备自动发现、能力探测、动态注册
14. **MCP 服务集成**：通过 MCP 协议接入第三方服务，扩展能力边界
15. **路由结果缓存（LRU Cache）**：相同/相似输入跳过 NLU，直接返回缓存的路由结果（5 分钟有效期）
16. **批量自学习 + 本地兜底**：未知意图攒批后一次性请教，device_coord 不通时本地记录，恢复后批量请教

## 使用方式

### 路由单个任务

```
请将以下任务路由到最合适的设备：
任务描述：生成一份包含图表的 Excel 报告
```

### 自然语言输入

```
帮我发条短信给妈妈
```

引擎会通过 NLU 解析意图（message_send）、提取实体（person: 妈妈）、匹配工具（sms），然后路由到手机端执行。

### 自我进化

当用户输入无法被现有意图识别时，SIE 会自动：
1. 捕获未知输入
2. 生成 `learn_request` 请教请求
3. 发送给大爱（手机端）获取教学回复
4. 收到 `learn_response` 后自动更新 `nlu_config.json`
5. 再次解析验证学习效果

### 批量路由

```
请将以下 5 个任务分配到最优设备组合：
1. 生成 PDF 文档
2. 处理视频文件
3. 运行数据分析脚本
4. 设计前端页面
5. 查询数据库
```

### 查看路由状态

```
查看当前所有设备的负载状态和任务队列
```

### 查看双链路状态

```
查看当前设备间的通信链路状态
```

### 查看已注册设备

```
查看当前所有已注册设备的能力和状态
```

## 路由决策流程

```
任务输入 → LRU 缓存检查 → 关键词快速通道 → AI 语义理解 fallback → 自动设备注册 → 任务分析 → 意图→工具映射 → 是否需要跨设备 → device_coord（miclaw 自动选设备）→ 指示器输出 → 任务分发 → 语音通知
```

### 详细步骤

1. **LRU 缓存检查**：对用户输入计算哈希，检查路由缓存（5 分钟有效期）
   - 缓存命中（哈希相同或语义相似度 > 0.9）→ 跳过 NLU，直接返回缓存的路由结果
   - 缓存未命中 → 继续后续流程
2. **关键词快速通道**：基于 `nlu_config.json` 配置驱动的快速匹配
   - 正则模式匹配（最高优先级，置信度 0.95）
   - 关键词匹配（置信度最高 0.9）
   - 模糊匹配：SequenceMatcher 相似度计算（阈值 0.6）
   - 置信度计算：综合评分 0-1
   - 支持 27 个意图，每个意图 4-12 个关键词 + 正则 patterns
3. **AI 语义理解 fallback**：当关键词快速通道无法匹配（confidence < 0.3）时
   - NLUClassifier 调用大模型进行意图分类
   - 从 27 个意图中选择最佳匹配
   - 返回意图名称、置信度、提取的实体
4. **自动设备注册**：检查是否有新设备上线，自动探测能力并注册
5. **任务分析**：调用 Task Profiler 提取任务特征向量（优先使用 NLU 解析结果，回退到关键词匹配）
6. **意图→工具映射**：根据 NLU 结果确定所需工具和是否需要跨设备
7. **设备选择**：**SIE 不做设备选择**，只输出 `needs_cross_device: true/false`
   - 如果需要跨设备 → 交给 miclaw device_coord（它有实时设备状态）
   - 如果本机可执行 → 直接执行
8. **指示器输出**：生成 Invocation Indicator，展示决策结果
9. **任务分发**：通过主链路（device_chat）分发任务
10. **语音通知**：任务完成后，选择最佳语音设备播报结果

### 硬规则优先

当任务涉及以下工具时，直接标记目标设备类型，跳过打分：
- **手机端**：sms, call, camera, location, alarm, media, screenshot
- **电脑端**：code, ide, office

> **v3.3.1 变更**：硬规则不再直接指定设备，而是标记设备类型偏好，最终设备选择仍由 miclaw device_coord 决定

### 崩溃风险拦截

当 Crash Detector 判定目标设备存在崩溃风险时：
1. 自动将任务拆分为更小的子任务
2. 通过 device_chat 通知手机端
3. 手机端接收后分步调度执行

### 自动设备注册

新设备登录账号后：
1. 设备发现器检测到新设备上线
2. 能力探测器自动识别设备类型和能力
3. 注册管理器将设备添加到能力矩阵
4. 新设备立即可参与路由决策

### 语音通知中继

任务完成后：
1. 选择器评估所有有语音能力的设备
2. 根据语音能力、设备状态、用户接近度综合评分
3. 选择最佳播报设备
4. 通过 TTS / 通知推送 / 语音消息播报结果

## 自我进化架构

SIE v3.3.1 优化自我进化架构，从逐条请教改为批量模式，增加本地兜底机制。

### 核心组件

| 组件 | 职责 |
|------|------|
| `SelfEvolvingNLU` | 核心入口，包装现有 NLU，添加进化能力 |
| `LearnProtocol` | 标准化的知识请教协议（learn_request / learn_response） |
| `UnknownIntentHandler` | 未知意图批量捕获与管理（攒够 3-5 个后一次性请教） |
| `AutoConfigUpdater` | 自动将新学到的意图写入 nlu_config.json |
| `LearningLogger` | 学习过程日志记录 |
| `LocalFallbackLogger` | device_coord 不通时的本地兜底日志 |
| `RouteCache` | LRU 路由结果缓存（5 分钟有效期） |

### 批量请教协议格式

**批量请求格式**（SIE → 大爱）：
```json
{
  "type": "batch_learn_request",
  "request_id": "BLR-20260504-001",
  "items": [
    {
      "input": "用户说的话1",
      "context": "当时的上下文",
      "capture_count": 3
    },
    {
      "input": "用户说的话2",
      "context": "",
      "capture_count": 1
    }
  ],
  "question": "这些意图应该映射到什么工具？关键词有哪些？",
  "timestamp": "2026-05-04T00:14:00"
}
```

**批量回复格式**（大爱 → SIE）：
```json
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
```

### 进化流程（v3.3.1 批量模式）

```
用户输入 → NLU 解析 → 未知意图？ → 捕获并缓存到本地
                                        ↓
                              攒够 3-5 个？ → 是 → 生成 batch_learn_request → 发送给大爱
                                        ↓ 否                                    ↓
                              继续等待下一个未知意图        验证学习效果 ← 重新加载 NLU ← 自动更新配置 ← 收到 batch_learn_response

device_coord 不通？ → 记录到本地日志（.sie_logs/pending_learn.jsonl）→ 连接恢复后批量请教
```

## 路由结果缓存（v3.3.1 新增）

SIE v3.3.1 引入 LRU 缓存，避免相同输入重复走 NLU + 路由打分。

### 缓存策略

- **缓存键**：用户输入的哈希值（MD5）
- **相似度匹配**：语义相似度 > 0.9 的输入视为相同（SequenceMatcher）
- **有效期**：5 分钟，过期后重新计算
- **缓存容量**：最多 200 条路由结果
- **缓存命中时**：跳过 NLU，直接返回上次的路由结果

### 缓存失效

- 超过 5 分钟自动失效
- nlu_config.json 更新后清空缓存（配置变更可能导致路由变化）
- 手动调用 `clear_cache()` 清空

## 性能优化（v3.3.1 新增）

v3.3.1 对 SIE 进行了全面的性能优化，涵盖批量学习、LRU 缓存、路由简化和心跳复用四个方面。

### 批量学习（Batch Learn）

- 未知意图不再逐条请教，攒够阈值（默认 3 个）后一次性发给大爱
- 减少 device_coord 调用次数，降低超时风险
- 支持本地兜底：device_coord 不通时记录到 `pending_learn.jsonl`，连接恢复后批量请教
- 配置项：`batch_learn.threshold`（触发阈值）、`batch_learn.learn_request_timeout_seconds`（超时时间）

### LRU 路由缓存（RouteCache）

- 相同或相似的用户输入（哈希或语义相似度 > 0.9）直接返回上次的路由结果
- 缓存有效期 5 分钟，过期后重新计算
- 缓存容量 200 条，LRU 淘汰策略
- 缓存命中时跳过 NLU，路由耗时从 ~1ms 降至 <0.01ms

### 路由简化

- SIE 只做意图识别和任务拆分，输出 `needs_cross_device` 标记
- 设备选择完全交给 miclaw device_coord（它有实时设备状态）
- 硬规则改为标记设备类型偏好，不再直接指定设备
- 去掉设备选择层，减少路由决策复杂度

### 心跳复用

- 不再自己实现心跳协议，直接复用 miclaw 的设备发现（`device_list`）
- 启动时调一次 `device_list` 获取设备状态
- 减少网络开销和代码复杂度

### 性能基准

| 指标 | 目标 | 实测 |
|------|------|------|
| NLU 单次识别耗时 | < 50ms | ~0.01ms（中位数） |
| 缓存命中路由耗时 | < 10ms | <0.01ms（中位数） |
| 批量学习处理时间 | < 500ms | ~6ms（3 个未知意图） |

## 语义理解

v3.3.1 将 NLU 从纯关键词匹配升级为 AI 语义理解。

### 双层匹配架构

```
用户输入
  │
  ├─ 关键词快速通道（nlu_config.json）
  │   ├─ 正则模式匹配（置信度 0.95）
  │   ├─ 关键词匹配（置信度 0.9）
  │   └─ 模糊匹配（阈值 0.6）
  │
  └─ AI 语义理解 fallback（NLUClassifier）
      └─ 大模型意图分类（27 个意图）
```

### 为什么需要双层匹配

- **关键词快速通道**：响应快（<1ms）、确定性强、无需网络，覆盖 80%+ 的常见表达
- **AI 语义理解**：处理复杂句式、口语化表达、歧义消解，覆盖长尾场景
- **fallback_to_ai**：每个意图配置是否启用 AI fallback，灵活控制

## MCP 集成

SIE v3.3.0 支持通过 MCP（Model Context Protocol）接入第三方服务。

### 已集成的 MCP 服务

| 服务 | 说明 | 用途 |
|------|------|------|
| mcd-mcp | 小米内容分发 | 影视、短视频、小说搜索 |
| 高德地图 | 地图服务 | POI 搜索、路线规划、天气 |
| 天气查询 | 气象数据 | 实时天气、预报 |
| 同程旅行 | 旅行服务 | 机票、火车票、酒店预订 |

### MCP 配置

MCP 服务通过 `nlu_config.json` 中的 `mcp_services` 字段配置：

```json
{
  "mcp_services": {
    "amap": {
      "description": "高德地图服务",
      "intents": ["location_query", "weather_query"]
    }
  }
}
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `capability_weight` | 0.5 | 能力匹配权重 |
| `load_weight` | 0.3 | 负载均衡权重 |
| `health_weight` | 0.2 | 可达性权重（基于心跳延迟） |
| `max_retries` | 3 | 故障转移最大重试次数 |
| `max_migrations` | 6 | 总迁移次数上限 |
| `migration_timeout_ms` | 5000 | 任务迁移超时时间 |
| `heartbeat_interval` | 30s | 心跳检测间隔（复用 miclaw device_list） |
| `offline_threshold` | 2 | 连续心跳失败次数触发离线 |
| `crash_risk_threshold` | 0.7 | 崩溃风险阈值（0-1，超过则触发拆分） |
| `dual_link_enabled` | true | 是否启用双链路通信 |
| `indicator_enabled` | true | 是否启用智能调用指示器 |
| `auto_discovery_enabled` | true | 是否启用自动设备发现 |
| `discovery_interval` | 60s | 设备发现检查间隔 |
| `probe_timeout` | 10s | 能力探测超时 |
| `capability_update_interval` | 300s | 能力矩阵定期更新间隔 |
| `voice_relay_enabled` | true | 是否启用语音通知中继 |
| `auto_select_voice_device` | true | 是否自动选择播报设备 |
| `voice_dedup_window_ms` | 300000 | 播报去重时间窗口（5分钟） |
| `voice_max_content_length` | 200 | TTS 播报最大内容长度 |
| `nlu_enabled` | true | 是否启用自然语言理解 |
| `nlu_ai_fallback_enabled` | true | 是否启用 AI 语义理解 fallback |
| `self_evolve_enabled` | true | 是否启用自我进化架构 |
| `logger_enabled` | true | 是否启用全链路日志 |
| `logger_max_entries` | 500 | 日志最大保留条数 |
| `logger_persist_dir` | ~/.sie_logs/ | 日志持久化目录 |
| `route_cache_enabled` | true | 是否启用路由结果 LRU 缓存 |
| `route_cache_ttl_seconds` | 300 | 路由缓存有效期（秒，默认 5 分钟） |
| `route_cache_max_size` | 200 | 路由缓存最大条数 |
| `route_cache_similarity_threshold` | 0.9 | 语义相似度阈值（超过视为相同输入） |
| `batch_learn_enabled` | true | 是否启用批量自学习 |
| `batch_learn_threshold` | 3 | 攒够多少个未知意图后一次性请教 |
| `batch_learn_max_pending` | 10 | 最大缓存未知意图数（超过丢弃最旧） |
| `learn_request_timeout_seconds` | 30 | 请教请求超时时间（秒） |
| `local_fallback_enabled` | true | device_coord 不通时是否记录本地兜底日志 |
| `local_fallback_path` | ~/.sie_logs/pending_learn.jsonl | 本地兜底日志路径 |

## 参考文档

- [任务分析器](references/task-profiler.md) — 任务特征提取与分类
- [设备能力矩阵](references/device-capability.md) — 设备能力画像定义与评分标准
- [路由规则](references/routing-rules.md) — 路由决策规则集
- [负载均衡策略](references/load-balancer.md) — 多设备负载分配算法
- [故障转移与迁移](references/failover-migration.md) — 设备故障处理机制
- [智能调用指示器](references/invocation-indicator.md) — 调用决策的可见反馈
- [崩溃风险检测](references/crash-detector.md) — PC端崩溃检测与手机端分步通知
- [双链路通信](references/dual-link.md) — 主副链路通信机制
- [自动设备注册](references/auto-device-registration.md) — 新设备自动发现与接入
- [语音通知中继](references/voice-notification-relay.md) — 任务完成后语音播报
- [自然语言理解](references/natural-language-understanding.md) — 意图识别、实体提取、模糊匹配
- [全链路日志](references/sie-logger.md) — 四级日志、任务追踪、文件持久化
- [自我进化架构](references/self-evolution.md) — LearnProtocol、自动配置更新

## 验证

使用 `verify_engine.py` 进行路由逻辑验证：

```bash
# NLU 识别率快速验证
python sie_quick_test.py

# 完整引擎验证
python verify_engine.py

# 自我进化测试
python sie_evolve_test.py
```

## Changelog

### v3.3.1 (2026-05-04)
- feat: 路由结果 LRU 缓存 — 相同/相似输入跳过 NLU，5 分钟有效期，最多 200 条
- feat: 批量自学习 — 未知意图攒够 3-5 个后一次性请教，减少 device_coord 调用次数
- feat: 本地兜底日志 — device_coord 不通时记录到 pending_learn.jsonl，连接恢复后批量请教
- feat: 路由简化 — SIE 不做设备选择，只做意图识别和任务拆分，设备选择交给 miclaw device_coord
- feat: 心跳检测复用 miclaw device_list — 不再自己实现心跳协议
- feat: learn_request 超时从默认值改为 30 秒
- refactor: nlu_config.json 新增 batch_learn 和 route_cache 配置项
- docs: 更新 skill.md 至 v3.3.1

### v3.3.0 (2026-05-04)
- feat: NLU 从关键词匹配升级为 AI 语义理解（NLUClassifier）
- feat: 自我进化架构（SelfEvolvingNLU + LearnProtocol）
- feat: 新增 5 个意图（timer_set, tts_speak, translate, app_manage, ai_write）
- feat: nlu_config.json 结构升级，keywords 降级为快速通道，新增 fallback_to_ai
- feat: MCP 服务集成支持
- docs: 新增 DESIGN.md 设计原则文档
- test: sie_evolve_test.py 14 场景 107 项检查全通过

### v3.2.0 (2026-05-04)
- 新增：NLU 外部配置驱动（nlu_config.json）— 20 个意图，每个 4-12 个关键词 + 正则 patterns
- 新增：NLU 快速验证脚本（sie_quick_test.py）— 153 个断言，NLU 识别率 100%
- 新增：设计文档（DESIGN.md）— 架构设计原则和决策依据
- 重构：路由逻辑简化 — SIE 只做调度，跨设备任务统一交给 device_coord
- 重构：NLU 模块从硬编码改为 JSON 配置驱动
- 测试：sie_quick_test 153/153（100%），verify_engine 262/285（91.9%）
- 文档：更新 README.md、CHANGELOG.md、skill.md

### v3.1.0 (2026-05-03)
- 新增：自然语言理解（NLU）模块 — 五层理解能力：意图识别、同义词扩展、实体提取、模糊匹配、置信度计算
- 新增：SieLogger 全链路日志系统 — 四级日志、按任务 ID 追踪、文件持久化
- 新增：TaskProfiler v4 NLU 集成 — analyze() 优先使用 NLU 解析，回退到关键词匹配
- 修复：verify_engine.py 缺少 SequenceMatcher 导入
- 修复：NLU parse() 返回值缺少 match_method 字段
- 修复：测试断言中 log_error/log_warn 的 phase 参数错误
- 修复：sie_engine.py 正则表达式中的无效转义序列（SyntaxWarning）
- 测试：断言从 217 增至 297（+37%），新增 Module 13（SieLogger）、Module 14（NLU）、Module 14b（NLU 集成）
- 性能：完整流水线 23.23 μs/op（约 43,000 ops/s）

### v3.0.0 (2026-05-03)
- 性能优化：全模块性能提升，217 个断言全部通过
- 优化：TaskProfiler 关键词索引预排序，避免短词误匹配，减少遍历次数
- 优化：DeviceCapability 使用生成器表达式替代列表推导，减少临时对象分配
- 优化：RoutingRules 预计算负载映射表，单候选设备快速路径，避免不必要的排序
- 优化：CrashDetector 内联风险评估函数，预提取权重向量，使用 `__slots__` 减少内存占用
- 优化：DualLink 使用位运算加速状态判断，预定义 proximity 修正系数表，使用 `__slots__`
- 优化：AutoDeviceRegistration 使用 set 交集运算加速设备发现
- 优化：VoiceNotificationRelay 预编译正则表达式，使用列表推导式替代手动循环
- 优化：LoadBalancer 空工具列表快速路径
- 优化：FailoverMigration 优化类型检查顺序
- 优化：RoutingLog 单次 `datetime.now()` 调用，使用 `del` 替代重新赋值清理日志
- 优化：InvocationIndicator 使用 `del` 替代重新赋值清理历史
- 优化：TaskProfiler 可拆分检查提前退出
- 文档：更新版本号至 v3.0.0

### v2.1.0 (2026-05-03)
- 新增：自动设备注册（Auto Device Registration）— 新设备登录后自动发现、探测能力、接入引擎
- 新增：语音通知中继（Voice Notification Relay）— 任务完成后自动选择语音设备播报结果
- 新增：设备类型自动分类（phone/pc/tablet/speaker/display）
- 新增：语音设备综合评分（语音能力 × 设备状态 × 用户接近度 × 播报质量）
- 新增：播报去重策略（相同任务ID / 时间窗口 / 内容去重）
- 新增：播报内容自动优化（去特殊符号、数字转文字、截断过长内容）
- 优化：路由决策流程增加自动设备注册步骤
- 优化：路由决策流程增加语音通知步骤
- 测试：新增 Module 11（AutoDeviceRegistration）、Module 12（VoiceNotificationRelay），断言增至 200+
- 文档：新增 auto-device-registration.md、voice-notification-relay.md

### v2.0.0 (2026-05-03)
- 更名：Smart Task Router → 智能调用引擎（Smart Invocation Engine, SIE）
- 新增：智能调用指示器（Invocation Indicator）— 每次路由决策产生可见反馈
- 新增：崩溃风险检测（Crash Detector）— PC端监控 + 手机端分步通知
- 新增：双链路通信（Dual Link）— device_chat主链路 + 网络心跳副链路
- 新增：双链路心跳保活机制，PC启动时自动建立网络连接
- 新增：崩溃风险阈值配置，超过阈值自动拆分任务
- 优化：故障检查支持双链路任一可用即可
- 优化：路由决策流程增加崩溃风险评估步骤
- 测试：新增 Module 8（InvocationIndicator）、Module 9（CrashDetector）、Module 10（DualLink），断言从 73 增至 95+
- 文档：新增 README.md、CHANGELOG.md

### v1.2.0 (2026-05-02)
- 新增：RoutingLog 路由决策日志模块，记录每次路由决策的完整信息（自动清理旧记录）
- 修复：软规则增加 MIN_ROUTE_SCORE 阈值（0.2），低分设备不再被路由
- 修复：删除重复文档 device-capabilities.md，统一为 device-capability.md
- 修复：routing-rules.md 伪代码与实际代码对齐（score 阈值、返回格式）
- 测试：新增 Module 6（RoutingLog）和 Module 7（Edge Cases），断言从 55 增至 73
- 测试：覆盖空工具列表、多硬规则冲突、score 阈值拦截、高风险操作检测等边界场景

### v1.1.0 (2026-05-02)
- 修复：proximity 评分从二值(online/offline)改为按心跳延迟分级
- 修复：FailoverMigration 添加 L1/L2 独立计数器，真正限制迁移次数
- 修复：TaskProfiler 输出增加 task_id 和 estimated_duration_seconds
- 修复：搜索关键词加入关键词映射表
- 修复：verify_router.py 添加 main 入口和 55 个断言测试
- 合并：device-capabilities.md 和 device-capability.md 为统一文档
- 新增：硬规则不可迁移保护（支付/删除等高风险操作）

### v1.0.0 (初始版本)
- 五大核心模块：TaskProfiler, DeviceCapability, RoutingRules, LoadBalancer, FailoverMigration
- 硬规则 + 软规则双层路由架构
- 三级故障转移策略
