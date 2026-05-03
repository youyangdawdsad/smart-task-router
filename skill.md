# 智能调用引擎（Smart Invocation Engine）

根据任务类型、设备能力、负载状态，自动将任务分配到最优设备执行。当检测到执行风险时，智能拆分任务并通知协作设备分步处理。

**版本**: 3.1.0
**前置条件**: 至少2台设备在线（通过 device_chat 协议注册，或自动发现）

## 概述

智能调用引擎（SIE）是多设备协作场景下的任务调度技能。它在 v1.x 路由引擎的基础上，新增七大核心能力：

1. **自然语言理解（NLU）**：五层理解能力——意图识别、同义词扩展、实体提取、模糊匹配、置信度计算，让引擎真正理解用户的自然语言输入
2. **全链路日志（SieLogger）**：记录完整调用链路（触发→NLU→匹配→路由→执行），支持四级日志、按任务 ID 追踪、文件持久化
3. **智能调用指示器**：每次智能调用决策时，生成可见的执行指示，让用户实时感知引擎的工作状态
4. **崩溃风险检测**：电脑端实时监控执行环境，当检测到可能导致崩溃的操作时，自动通知手机端将任务拆分为更小的步骤分步执行
5. **双链路通信**：在 device_chat 主链路之外，新增网络心跳副链路，确保设备间通信始终可用
6. **自动设备注册**：新设备登录账号后自动发现、探测能力、接入引擎，无需手动配置
7. **语音通知中继**：电脑端完成工作后，自动选择有语音能力的设备播报结果

## 核心能力

1. **自然语言理解（NLU）**：解析用户自然语言输入，提取意图和实体，支持模糊匹配和错别字容错
2. **全链路日志（SieLogger）**：记录每次调用的触发条件、匹配结果、执行过程和最终输出
3. **任务分析（Task Profiling）**：解析任务描述，提取任务类型、所需工具、资源需求、优先级等特征
4. **设备能力匹配（Device Capability Matching）**：维护各设备的能力画像，包括硬件配置、已安装工具、网络状态等
5. **路由决策（Routing Decision）**：综合任务特征和设备能力，选择最优执行设备
6. **负载均衡（Load Balancing）**：避免单设备过载，合理分配任务到多设备
7. **故障转移（Failover & Migration）**：设备离线或执行失败时，自动迁移到备选设备
8. **智能调用指示器（Invocation Indicator）**：每次调用决策产生可见反馈，让用户知道引擎在工作
9. **崩溃风险检测（Crash Detector）**：监控执行环境，高风险操作自动拆分并通知协作设备
10. **双链路通信（Dual Link）**：主链路（device_chat）+ 副链路（网络心跳），确保通信可靠
11. **自动设备注册（Auto Device Registration）**：新设备自动发现、能力探测、动态注册
12. **语音通知中继（Voice Notification Relay）**：任务完成后自动选择语音设备播报结果

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

### 手动触发语音播报

```
播报任务完成结果
```

## 路由决策流程

```
任务输入 → NLU 解析 → 自动设备注册 → 任务分析 → 设备能力匹配 → 负载评估 → 故障检查 → 崩溃风险评估 → 路由决策 → 指示器输出 → 任务分发 → 语音通知
```

### 详细步骤

1. **NLU 解析**：对用户输入进行自然语言理解，提取意图和实体
   - 意图识别：正则模板匹配 10 种意图
   - 同义词扩展：100+ 同义词映射
   - 实体提取：人名、时间、地点、内容
   - 模糊匹配：SequenceMatcher 相似度计算
   - 置信度计算：综合评分 0-1
2. **自动设备注册**：检查是否有新设备上线，自动探测能力并注册
3. **任务分析**：调用 Task Profiler 提取任务特征向量（优先使用 NLU 解析结果，回退到关键词匹配）
4. **能力匹配**：将任务特征与各设备能力画像进行匹配，计算匹配分数
5. **负载评估**：查询各设备当前负载，计算可用容量
6. **故障检查**：确认目标设备在线且健康（双链路任一可用即可）
7. **崩溃风险评估**：对目标设备执行 Crash Detector 风险扫描
8. **综合评分**：`score = α × capability_match + β × load_factor + γ × proximity`
   - `α = 0.5`（能力匹配权重）
   - `β = 0.3`（负载均衡权重）
   - `γ = 0.2`（可达性权重，基于心跳延迟分级：<2s→1.0, <5s→0.8, ≥5s→0.5）
9. **路由决策**：选择综合评分最高的设备
10. **指示器输出**：生成 Invocation Indicator，展示决策结果
11. **任务分发**：通过主链路（device_chat）分发任务
12. **语音通知**：任务完成后，选择最佳语音设备播报结果

### 硬规则优先

当任务涉及以下工具时，直接路由到对应设备类型，跳过打分：
- **手机端**：sms, call, camera, location, alarm, media, screenshot
- **电脑端**：code, ide, office

### 崩溃风险拦截

当 Crash Detector 判定目标设备存在崩溃风险时：
1. 自动将任务拆分为更小的子任务
2. 通过副链路通知手机端
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

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `capability_weight` | 0.5 | 能力匹配权重 |
| `load_weight` | 0.3 | 负载均衡权重 |
| `health_weight` | 0.2 | 可达性权重（基于心跳延迟） |
| `max_retries` | 3 | 故障转移最大重试次数 |
| `max_migrations` | 6 | 总迁移次数上限 |
| `migration_timeout_ms` | 5000 | 任务迁移超时时间 |
| `heartbeat_interval` | 30s | 心跳检测间隔 |
| `offline_threshold` | 2 | 连续心跳失败次数触发离线 |
| `crash_risk_threshold` | 0.7 | 崩溃风险阈值（0-1，超过则触发拆分） |
| `dual_link_enabled` | true | 是否启用双链路通信 |
| `indicator_enabled` | true | 是否启用智能调用指示器 |
| `network_heartbeat_interval` | 15s | 副链路网络心跳间隔 |
| `network_heartbeat_timeout` | 5s | 副链路心跳超时 |
| `auto_discovery_enabled` | true | 是否启用自动设备发现 |
| `discovery_interval` | 60s | 设备发现检查间隔 |
| `probe_timeout` | 10s | 能力探测超时 |
| `capability_update_interval` | 300s | 能力矩阵定期更新间隔 |
| `voice_relay_enabled` | true | 是否启用语音通知中继 |
| `auto_select_voice_device` | true | 是否自动选择播报设备 |
| `voice_dedup_window_ms` | 300000 | 播报去重时间窗口（5分钟） |
| `voice_max_content_length` | 200 | TTS 播报最大内容长度 |
| `nlu_enabled` | true | 是否启用自然语言理解 |
| `logger_enabled` | true | 是否启用全链路日志 |
| `logger_max_entries` | 500 | 日志最大保留条数 |
| `logger_persist_dir` | ~/.sie_logs/ | 日志持久化目录 |

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

## 验证

使用 `verify_engine.py` 进行路由逻辑验证（297个断言，覆盖全部14个模块）：

```bash
python verify_engine.py
```

该脚本会运行一系列测试用例，验证 NLU 解析的准确性、日志系统的完整性、路由决策的正确性、崩溃检测的可靠性、双链路通信的稳定性、自动设备注册的准确性和语音通知中继的完整性。

## Changelog

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
