# 智能调用引擎（Smart Invocation Engine）

根据任务类型、设备能力、负载状态，自动将任务分配到最优设备执行。当检测到执行风险时，智能拆分任务并通知协作设备分步处理。

**版本**: 2.0.0
**前置条件**: 至少2台设备在线（通过 device_chat 协议注册）

## 概述

智能调用引擎（SIE）是多设备协作场景下的任务调度技能。它在 v1.x 路由引擎的基础上，新增三大核心能力：

1. **智能调用指示器**：每次智能调用决策时，生成可见的执行指示，让用户实时感知引擎的工作状态
2. **崩溃风险检测**：电脑端实时监控执行环境，当检测到可能导致崩溃的操作时，自动通知手机端将任务拆分为更小的步骤分步执行
3. **双链路通信**：在 device_chat 主链路之外，新增网络心跳副链路，确保设备间通信始终可用

## 核心能力

1. **任务分析（Task Profiling）**：解析任务描述，提取任务类型、所需工具、资源需求、优先级等特征
2. **设备能力匹配（Device Capability Matching）**：维护各设备的能力画像，包括硬件配置、已安装工具、网络状态等
3. **路由决策（Routing Decision）**：综合任务特征和设备能力，选择最优执行设备
4. **负载均衡（Load Balancing）**：避免单设备过载，合理分配任务到多设备
5. **故障转移（Failover & Migration）**：设备离线或执行失败时，自动迁移到备选设备
6. **智能调用指示器（Invocation Indicator）**：每次调用决策产生可见反馈，让用户知道引擎在工作
7. **崩溃风险检测（Crash Detector）**：监控执行环境，高风险操作自动拆分并通知协作设备
8. **双链路通信（Dual Link）**：主链路（device_chat）+ 副链路（网络心跳），确保通信可靠

## 使用方式

### 路由单个任务

```
请将以下任务路由到最合适的设备：
任务描述：生成一份包含图表的 Excel 报告
```

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

## 路由决策流程

```
任务输入 → 任务分析 → 设备能力匹配 → 负载评估 → 故障检查 → 崩溃风险评估 → 路由决策 → 指示器输出 → 任务分发
```

### 详细步骤

1. **任务分析**：调用 Task Profiler 提取任务特征向量
2. **能力匹配**：将任务特征与各设备能力画像进行匹配，计算匹配分数
3. **负载评估**：查询各设备当前负载，计算可用容量
4. **故障检查**：确认目标设备在线且健康（双链路任一可用即可）
5. **崩溃风险评估**：对目标设备执行 Crash Detector 风险扫描
6. **综合评分**：`score = α × capability_match + β × load_factor + γ × proximity`
   - `α = 0.5`（能力匹配权重）
   - `β = 0.3`（负载均衡权重）
   - `γ = 0.2`（可达性权重，基于心跳延迟分级：<2s→1.0, <5s→0.8, ≥5s→0.5）
7. **路由决策**：选择综合评分最高的设备
8. **指示器输出**：生成 Invocation Indicator，展示决策结果
9. **任务分发**：通过主链路（device_chat）分发任务

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
| `migration_timeout_ms` | 5000 | 任务迁移超时时间 |
| `heartbeat_interval` | 30s | 心跳检测间隔 |
| `offline_threshold` | 2 | 连续心跳失败次数触发离线 |
| `crash_risk_threshold` | 0.7 | 崩溃风险阈值（0-1，超过则触发拆分） |
| `dual_link_enabled` | true | 是否启用双链路通信 |
| `indicator_enabled` | true | 是否启用智能调用指示器 |
| `network_heartbeat_interval` | 15s | 副链路网络心跳间隔 |
| `network_heartbeat_timeout` | 5s | 副链路心跳超时 |

## 参考文档

- [任务分析器](references/task-profiler.md) — 任务特征提取与分类
- [设备能力矩阵](references/device-capability.md) — 设备能力画像定义与评分标准
- [路由规则](references/routing-rules.md) — 路由决策规则集
- [负载均衡策略](references/load-balancer.md) — 多设备负载分配算法
- [故障转移与迁移](references/failover-migration.md) — 设备故障处理机制
- [智能调用指示器](references/invocation-indicator.md) — 调用决策的可见反馈
- [崩溃风险检测](references/crash-detector.md) — PC端崩溃检测与手机端分步通知
- [双链路通信](references/dual-link.md) — 主副链路通信机制

## 验证

使用 `verify_engine.py` 进行路由逻辑验证（95+个断言，覆盖全部10个模块）：

```bash
python verify_engine.py
```

该脚本会运行一系列测试用例，验证路由决策的正确性、崩溃检测的可靠性和双链路通信的稳定性。

## Changelog

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
