# 智能调用引擎（Smart Invocation Engine）

> 多设备协作场景下的智能任务调度技能，自动将任务分配到最优设备执行。

## 简介

智能调用引擎（SIE）是为小米 AI 助手（MiClaw）设计的多设备协作调度技能。它能分析任务特征、匹配设备能力、评估负载状态，自动做出最优路由决策。

**当前版本**: v3.3.0

### 核心能力

- 🧠 **NLU 配置驱动**：意图识别完全由 `nlu_config.json` 外部配置驱动，支持 25+ 个意图
- 🤖 **AI 语义理解**：关键词快速通道 + AI 语义理解 fallback，双层匹配架构
- 🔄 **自我进化**：未知意图自动捕获 → 请教学习 → 配置更新，NLU 持续进化
- 📝 **全链路日志（SieLogger）**：记录完整调用链路，支持四级日志、按任务 ID 追踪
- 🔀 **智能调用指示器**：每次调用决策产生可见反馈
- ⚠️ **崩溃风险检测**：电脑端实时监控，高风险操作自动拆分并通知手机端
- 🔗 **双链路通信**：device_chat 主链路 + 网络心跳副链路
- 🔄 **自动设备注册**：新设备登录后自动发现、探测能力、接入引擎
- 🎤 **语音通知中继**：任务完成后自动选择语音设备播报
- 🔌 **MCP 服务集成**：接入第三方 MCP 服务，扩展能力边界

### v3.3.0 架构变更

- **AI 语义理解**：NLU 从纯关键词匹配升级为双层匹配架构（关键词快速通道 + AI fallback）
- **自我进化架构**：SelfEvolvingNLU + LearnProtocol，NLU 能够持续学习和扩展
- **新增 5 个意图**：timer_set, tts_speak, translate, app_manage, ai_write
- **MCP 集成**：支持接入第三方 MCP 服务

## 架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    智能调用引擎 (SIE v3.3)                                │
├─────────┬──────────┬──────────┬──────────┬──────────┬──────────────────┤
│ 任务分析 │ 路由决策  │ 负载均衡  │ 故障转移  │ 崩溃检测  │ NLU 解析         │
│ Profiler│ Rules    │ Balancer │ Failover │ CrashDet │ (JSON+AI双层)   │
├─────────┴──────────┴──────────┴──────────┴──────────┴──────────────────┤
│ 🔄 自我进化 │ 🤖 AI语义理解 │ 🔌 MCP集成 │ 🔀 指示器 │ 📝 SieLogger    │
├─────────────┴───────────────┴────────────┴──────────┴──────────────────┤
│ 🔗 双链路通信 │ 🔄 自动设备注册 │ 🎤 语音通知中继                        │
├──────────────┴────────────────┴────────────────────────────────────────┤
│                    设备能力矩阵 + 路由日志                               │
└─────────────────────────────────────────────────────────────────────────┘
         │                                                    │
    ┌────▼────┐                                        ┌──────▼──────┐
    │  电脑端  │◄──── 主链路 ──────────────────────────►│   手机端     │
    │ (主节点) │◄──── 副链路 ──────────────────────────►│  (协作节点)  │
    └─────────┘                                        └─────────────┘
```

## 核心模块

| 模块 | 文件 | 说明 |
|------|------|------|
| 任务分析器 | [task-profiler.md](references/task-profiler.md) | 解析任务，提取类型、工具、复杂度、紧急度 |
| 设备能力矩阵 | [device-capability.md](references/device-capability.md) | 各设备能力画像与评分标准 |
| 路由规则引擎 | [routing-rules.md](references/routing-rules.md) | 硬规则 + 软规则 + 崩溃风险拦截 |
| 负载均衡器 | [load-balancer.md](references/load-balancer.md) | 心跳检测、任务队列、负载分配 |
| 故障转移 | [failover-migration.md](references/failover-migration.md) | 三级迁移策略 + 副链路恢复 |
| 智能调用指示器 | [invocation-indicator.md](references/invocation-indicator.md) | 调用决策的可见反馈 |
| 崩溃风险检测 | [crash-detector.md](references/crash-detector.md) | PC端崩溃检测 + 手机端分步通知 |
| 双链路通信 | [dual-link.md](references/dual-link.md) | 主副链路保活与紧急通知 |
| 自动设备注册 | [auto-device-registration.md](references/auto-device-registration.md) | 新设备自动发现与接入 |
| 语音通知中继 | [voice-notification-relay.md](references/voice-notification-relay.md) | 任务完成后语音播报 |
| 自然语言理解 | [natural-language-understanding.md](references/natural-language-understanding.md) | 意图识别、实体提取、模糊匹配 |
| 全链路日志 | [sie-logger.md](references/sie-logger.md) | 四级日志、任务追踪、文件持久化 |
| 自我进化 | [self-evolution.md](references/self-evolution.md) | LearnProtocol、自动配置更新 |

## NLU 配置

v3.3.0 起，NLU 采用双层匹配架构：

```
用户输入
  │
  ├─ 关键词快速通道（nlu_config.json）
  │   ├─ 正则模式匹配（置信度 0.95）
  │   ├─ 关键词匹配（置信度 0.9）
  │   └─ 模糊匹配（阈值 0.6）
  │
  └─ AI 语义理解 fallback（NLUClassifier）
      └─ 大模型意图分类（25+ 个意图）
```

### 支持的意图（25+ 个）

| 意图 | 说明 | 目标设备 |
|------|------|----------|
| `message_send` | 发送短信 | phone |
| `sms_read` | 查看短信 | phone |
| `call_make` | 拨打电话 | phone |
| `calendar_create` | 创建日程 | phone |
| `calendar_query` | 查询日程 | phone |
| `alarm_set` | 设置闹钟 | phone |
| `weather_query` | 查询天气 | any |
| `todo_manage` | 待办管理 | phone |
| `note_manage` | 笔记管理 | phone |
| `contact_manage` | 联系人管理 | phone |
| `media_play` | 媒体控制 | phone |
| `device_control` | 设备控制 | phone |
| `home_control` | 智能家居 | phone |
| `photo_manage` | 照片管理 | phone |
| `location_query` | 位置查询 | any |
| `notification_send` | 发送通知 | phone |
| `code_execute` | 代码编写 | pc |
| `search_info` | 网页搜索 | any |
| `office_work` | 办公文档 | pc |
| `booking` | 预订服务 | any |
| `file_read` | 读取文件 | phone |
| `file_write` | 写入文件 | phone |
| `timer_set` | 定时器/倒计时 | phone |
| `tts_speak` | 语音播报 | phone |
| `translate` | 翻译文本 | any |
| `app_manage` | 应用管理 | phone |
| `ai_write` | AI 内容生成 | any |

### 匹配策略

1. **正则模式匹配**（最高优先级，置信度 0.95）
2. **关键词匹配**（置信度最高 0.9）
3. **模糊匹配**（SequenceMatcher，容错 0.6 阈值）
4. **AI 语义理解 fallback**（大模型意图分类）
5. **未知意图回退**（引导用户重新描述 / 自我进化）

## 自我进化

v3.3.0 引入自我进化架构，NLU 能够持续学习：

```
用户输入 → NLU 解析 → 未知意图？ → 捕获 → 生成 learn_request → 发送给大爱
                                                                    ↓
验证学习效果 ← 重新加载 NLU ← 自动更新配置 ← 收到 learn_response
```

## 快速开始

### 路由单个任务

```
请将以下任务路由到最合适的设备：
任务描述：生成一份包含图表的 Excel 报告
```

### 自然语言输入

```
帮我发条短信给妈妈
```

引擎会通过 NLU 解析意图（message_send）、提取实体、匹配工具（sms），然后路由到手机端执行。

### 批量路由

```
请将以下 5 个任务分配到最优设备组合：
1. 生成 PDF 文档
2. 处理视频文件
3. 运行数据分析脚本
4. 设计前端页面
5. 查询数据库
```

### 查看链路状态

```
查看当前设备间的通信链路状态
```

### 查看已注册设备

```
查看当前所有已注册设备的能力和状态
```

## 路由决策流程

```
任务输入 → 关键词快速通道 → AI 语义理解 fallback → 自动设备注册 → 任务分析 → 设备能力匹配 → 负载评估 → 故障检查 → 崩溃风险评估 → 路由决策 → 指示器输出 → 任务分发 → 语音通知
```

### NLU 解析（v3.3.0 双层匹配）

用户输入自然语言后，NLU 模块采用双层匹配：
1. **关键词快速通道**：从 `nlu_config.json` 加载意图配置进行匹配
2. **AI 语义理解 fallback**：快速通道无法匹配时，调用大模型进行意图分类

### 硬规则优先

当任务涉及以下工具时，直接路由到对应设备类型，跳过打分：
- **手机端**：sms, call, camera, location, alarm, media, screenshot
- **电脑端**：code, ide, office

### 路由简化（v3.2.0+）

SIE 只做调度决策，不自己执行任务：
- 跨设备任务统一路由到 `device_coord`
- 单设备任务直接路由到目标设备

### 崩溃风险拦截

当 Crash Detector 判定目标设备存在崩溃风险时：
1. 自动将任务拆分为更小的子任务
2. 通过副链路通知手机端
3. 手机端接收后分步调度执行

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `capability_weight` | 0.5 | 能力匹配权重 |
| `load_weight` | 0.3 | 负载均衡权重 |
| `health_weight` | 0.2 | 可达性权重（基于心跳延迟） |
| `max_retries` | 3 | 故障转移最大重试次数 |
| `max_migrations` | 6 | 总迁移次数上限 |
| `crash_risk_threshold` | 0.7 | 崩溃风险阈值（超过则触发拆分） |
| `dual_link_enabled` | true | 是否启用双链路通信 |
| `indicator_enabled` | true | 是否启用智能调用指示器 |
| `auto_discovery_enabled` | true | 是否启用自动设备发现 |
| `voice_relay_enabled` | true | 是否启用语音通知中继 |
| `nlu_enabled` | true | 是否启用自然语言理解 |
| `nlu_ai_fallback_enabled` | true | 是否启用 AI 语义理解 fallback |
| `self_evolve_enabled` | true | 是否启用自我进化架构 |
| `logger_enabled` | true | 是否启用全链路日志 |

## 验证

```bash
# NLU 识别率快速验证
python sie_quick_test.py

# 完整引擎验证
python verify_engine.py

# 自我进化测试
python sie_evolve_test.py
```

### 测试结果（v3.3.0）

| 测试套件 | 通过/总数 | 通过率 | 说明 |
|---------|----------|--------|------|
| sie_evolve_test | 107/107 | 100% | 自我进化 14 场景验证 |
| sie_quick_test | 153/153 | 100% | NLU 识别率验证 |
| verify_engine | 262/285 | 91.9% | 完整引擎验证 |

## 文件结构

```
smart-task-router/
├── skill.md                    # 主文档（技能说明）
├── README.md                   # 本文件
├── CHANGELOG.md                # 版本更新记录
├── DESIGN.md                   # 设计原则文档
├── nlu_config.json             # NLU 意图配置
├── sie_self_evolve.py          # 自我进化模块
├── verify_engine.py            # 完整引擎测试脚本
├── sie_quick_test.py           # NLU 快速验证脚本
├── sie_evolve_test.py          # 自我进化测试脚本
├── integrate_v320.py           # v3.2.0 集成脚本
└── references/
    ├── task-profiler.md        # 任务分析器
    ├── device-capability.md    # 设备能力矩阵
    ├── routing-rules.md        # 路由规则引擎
    ├── load-balancer.md        # 负载均衡器
    ├── failover-migration.md   # 故障转移机制
    ├── invocation-indicator.md # 智能调用指示器
    ├── crash-detector.md       # 崩溃风险检测
    ├── dual-link.md            # 双链路通信
    ├── auto-device-registration.md  # 自动设备注册
    ├── voice-notification-relay.md  # 语音通知中继
    ├── natural-language-understanding.md  # 自然语言理解
    ├── sie-logger.md           # 全链路日志
    └── self-evolution.md       # 自我进化架构
```

## 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)

## 许可

MIT License
