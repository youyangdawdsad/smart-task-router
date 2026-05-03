# 智能调用引擎（Smart Invocation Engine）

> 多设备协作场景下的智能任务调度技能，自动将任务分配到最优设备执行。

## 简介

智能调用引擎（SIE）是为小米 AI 助手（MiClaw）设计的多设备协作调度技能。它能分析任务特征、匹配设备能力、评估负载状态，自动做出最优路由决策。

v2.0 在 v1.x 路由引擎基础上，新增三大核心能力：

- 🔀 **智能调用指示器**：每次调用决策产生可见反馈，让你知道引擎在做什么
- ⚠️ **崩溃风险检测**：电脑端实时监控执行环境，高风险操作自动拆分并通知手机端分步执行
- 🔗 **双链路通信**：device_chat 主链路 + 网络心跳副链路，确保设备间通信始终可靠

## 架构

```
┌─────────────────────────────────────────────────┐
│              智能调用引擎 (SIE v2.0)              │
├─────────┬──────────┬──────────┬─────────────────┤
│ 任务分析 │ 路由决策  │ 负载均衡  │ 故障转移        │
│ Profiler│ Rules    │ Balancer │ Failover        │
├─────────┴──────────┴──────────┴─────────────────┤
│ 🔀 智能调用指示器 │ ⚠️ 崩溃风险检测 │ 🔗 双链路通信  │
├──────────────────┴───────────────┴──────────────┤
│              设备能力矩阵 + 路由日志               │
└─────────────────────────────────────────────────┘
         │                          │
    ┌────▼────┐              ┌──────▼──────┐
    │  电脑端  │◄── 主链路 ──►│   手机端     │
    │ (主节点) │◄── 副链路 ──►│  (协作节点)  │
    └─────────┘              └─────────────┘
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

## 快速开始

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

### 查看链路状态

```
查看当前设备间的通信链路状态
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `capability_weight` | 0.5 | 能力匹配权重 |
| `load_weight` | 0.3 | 负载均衡权重 |
| `health_weight` | 0.2 | 可达性权重 |
| `max_retries` | 3 | 故障转移最大重试次数 |
| `max_migrations` | 6 | 总迁移次数上限 |
| `crash_risk_threshold` | 0.7 | 崩溃风险阈值（超过则拆分） |
| `dual_link_enabled` | true | 是否启用双链路通信 |
| `indicator_enabled` | true | 是否启用智能调用指示器 |
| `network_heartbeat_interval` | 15s | 副链路心跳间隔 |

## 验证

```bash
python verify_engine.py
```

163 个断言，覆盖全部 10 个模块：

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

## 文件结构

```
smart-invocation-engine/
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
    └── dual-link.md            # 双链路通信
```

## 版本历史

详见 [CHANGELOG.md](CHANGELOG.md)

## 许可

MIT License
