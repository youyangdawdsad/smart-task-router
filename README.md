# 智能调用引擎（Smart Invocation Engine）

> 多设备协作场景下的智能任务调度技能，自动将任务分配到最优设备执行。

## 简介

智能调用引擎（SIE）是为小米 AI 助手（MiClaw）设计的多设备协作调度技能。它能分析任务特征、匹配设备能力、评估负载状态，自动做出最优路由决策。

**当前版本**: v3.1.0

### 核心能力

- 🧠 **自然语言理解（NLU）**：五层理解能力，支持意图识别、同义词扩展、实体提取、模糊匹配、置信度计算
- 📝 **全链路日志（SieLogger）**：记录完整调用链路，支持四级日志、按任务 ID 追踪、文件持久化
- 🔀 **智能调用指示器**：每次调用决策产生可见反馈，让你知道引擎在做什么
- ⚠️ **崩溃风险检测**：电脑端实时监控执行环境，高风险操作自动拆分并通知手机端分步执行
- 🔗 **双链路通信**：device_chat 主链路 + 网络心跳副链路，确保设备间通信始终可靠
- 🔄 **自动设备注册**：新设备登录账号后自动发现、探测能力、接入引擎，无需手动配置
- 🎤 **语音通知中继**：电脑端完成工作后，自动选择有语音能力的设备播报结果

## 架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                    智能调用引擎 (SIE v3.1)                            │
├─────────┬──────────┬──────────┬──────────┬──────────┬──────────────┤
│ 任务分析 │ 路由决策  │ 负载均衡  │ 故障转移  │ 崩溃检测  │ NLU 解析     │
│ Profiler│ Rules    │ Balancer │ Failover │ CrashDet │ NLU          │
├─────────┴──────────┴──────────┴──────────┴──────────┴──────────────┤
│ 🔀 指示器 │ 🔗 双链路 │ 🔄 自动注册 │ 🎤 语音中继 │ 📝 SieLogger  │
├──────────┴──────────┴────────────┴────────────┴───────────────────┤
│                    设备能力矩阵 + 路由日志                           │
└─────────────────────────────────────────────────────────────────────┘
         │                                              │
    ┌────▼────┐                                  ┌──────▼──────┐
    │  电脑端  │◄──── 主链路 ────────────────────►│   手机端     │
    │ (主节点) │◄──── 副链路 ────────────────────►│  (协作节点)  │
    └─────────┘                                  └─────────────┘
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

引擎会通过 NLU 解析意图（send_message）、提取实体（person: 妈妈）、匹配工具（sms），然后路由到手机端执行。

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
任务输入 → NLU 解析 → 自动设备注册 → 任务分析 → 设备能力匹配 → 负载评估 → 故障检查 → 崩溃风险评估 → 路由决策 → 指示器输出 → 任务分发 → 语音通知
```

### NLU 解析

用户输入自然语言后，NLU 模块进行五层理解：
1. **意图识别**：正则模板匹配 10 种意图
2. **同义词扩展**：100+ 同义词映射
3. **实体提取**：人名、时间、地点、内容
4. **模糊匹配**：SequenceMatcher 相似度计算，支持错别字容错
5. **置信度计算**：综合评分 0-1

### 硬规则优先

当任务涉及以下工具时，直接路由到对应设备类型，跳过打分：
- **手机端**：sms, call, camera, location, alarm, media, screenshot
- **电脑端**：code, ide, office

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
| `logger_enabled` | true | 是否启用全链路日志 |

## 性能基准

v3.1.0 全模块性能优化后的基准测试数据：

| 测试场景 | 耗时 | 吞吐量 |
|---------|------|--------|
| 完整流水线 | 23.23 μs/op | 43,000 ops/s |
| NLU 解析 | ~10 μs/op | 100K ops/s |
| 路由决策（硬规则） | 0.15 μs/op | 6.86M ops/s |
| 设备能力评分 | 0.53 μs/op | 1.89M ops/s |
| 崩溃风险评估 | 3.10 μs/op | 323K ops/s |
| 任务分析 | 1.58 μs/op | 634K ops/s |
| 负载均衡 | 1.10 μs/op | 909K ops/s |

## 验证

```bash
python verify_engine.py
```

297 个断言，覆盖全部 14 个模块：

| 模块 | 测试数 | 说明 |
|------|--------|------|
| TaskProfiler | 14 | 任务分析、复杂度、紧急度、可拆分性 |
| DeviceCapability | 5 | 能力覆盖度、评分计算 |
| RoutingRules | 13 | 硬规则、软规则、proximity、边界 |
| LoadBalancer | 8 | 心跳检测、队列管理 |
| FailoverMigration | 15 | 故障检测、三级迁移、高风险保护 |
| RoutingLog | 5 | 日志记录、溢出清理 |
| Edge Cases | 13 | 空工具、低分拦截、多规则冲突 |
| InvocationIndicator | 23 | 5种指示器类型、历史管理、溢出、禁用 |
| CrashDetector | 32 | 6种风险因子、综合评估、任务拆分 |
| DualLink | 35 | 建立/确认、心跳、超时、状态转换、紧急通知 |
| AutoDeviceRegistration | 12 | 设备发现、能力探测、动态注册 |
| VoiceNotificationRelay | 15 | 语音设备选择、播报去重、内容优化 |
| SieLogger | 20 | 日志记录、过滤、持久化、任务追踪 |
| NaturalLanguageUnderstanding | 25 | 意图识别、实体提取、模糊匹配、置信度 |
| TaskProfiler v4 NLU 集成 | 15 | NLU 与任务分析器的集成测试 |

## 文件结构

```
smart-task-router/
├── SKILL.md                    # 主文档（技能说明）
├── README.md                   # 本文件
├── CHANGELOG.md                # 版本更新记录
├── verify_engine.py            # 测试验证脚本
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
    └── sie-logger.md           # 全链路日志
```

## 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)

## 许可

MIT License
