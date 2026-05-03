# 智能调用指示器（Invocation Indicator）

## 概述

智能调用指示器是用户感知引擎工作状态的核心窗口。每次引擎做出路由决策、执行崩溃检测、或触发故障转移时，都会生成一个结构化的指示器，让用户实时了解"引擎在做什么、为什么这么做、结果是什么"。

## 指示器类型

### 1. 路由决策指示器（Route Decision Indicator）

当引擎完成任务分析并选定目标设备时触发。

```json
{
  "type": "route_decision",
  "indicator_id": "IND-{timestamp}",
  "task_id": "T-xxx",
  "status": "routing",
  "decision": {
    "target_device": "pc-01",
    "method": "hard_rule",
    "reason": "代码执行任务，硬规则匹配 → 电脑端",
    "score": 0.92,
    "confidence": "high"
  },
  "visual": {
    "icon": "🖥️",
    "title": "智能调用 → 电脑端",
    "subtitle": "写代码任务，硬规则匹配",
    "progress": null
  }
}
```

### 2. 崩溃风险指示器（Crash Risk Indicator）

当 Crash Detector 检测到目标设备存在崩溃风险时触发。

```json
{
  "type": "crash_risk",
  "indicator_id": "IND-{timestamp}",
  "task_id": "T-xxx",
  "status": "risk_detected",
  "risk": {
    "device": "pc-01",
    "risk_level": 0.85,
    "risk_factors": ["large_file_processing", "memory_intensive"],
    "action": "split_and_notify",
    "sub_task_count": 3
  },
  "visual": {
    "icon": "⚠️",
    "title": "检测到崩溃风险",
    "subtitle": "已拆分为3个子任务，通知手机端分步执行",
    "progress": null
  }
}
```

### 3. 故障转移指示器（Failover Indicator）

当任务执行失败并触发迁移时触发。

```json
{
  "type": "failover",
  "indicator_id": "IND-{timestamp}",
  "task_id": "T-xxx",
  "status": "migrating",
  "migration": {
    "level": 2,
    "from_device": "pc-01",
    "to_device": "phone-01",
    "reason": "电脑端执行超时，迁移到手机端",
    "retry_count": 1
  },
  "visual": {
    "icon": "🔄",
    "title": "任务迁移",
    "subtitle": "电脑端 → 手机端（Level 2）",
    "progress": null
  }
}
```

### 4. 完成指示器（Completion Indicator）

当任务成功完成时触发。

```json
{
  "type": "completion",
  "indicator_id": "IND-{timestamp}",
  "task_id": "T-xxx",
  "status": "completed",
  "result": {
    "device": "pc-01",
    "duration_seconds": 12,
    "sub_tasks_completed": 3,
    "migrations": 0
  },
  "visual": {
    "icon": "✅",
    "title": "任务完成",
    "subtitle": "由电脑端执行，耗时12秒",
    "progress": 100
  }
}
```

### 5. 链路状态指示器（Link Status Indicator）

当双链路状态变化时触发。

```json
{
  "type": "link_status",
  "indicator_id": "IND-{timestamp}",
  "status": "link_change",
  "links": {
    "primary": {"status": "ok", "latency_ms": 150},
    "secondary": {"status": "ok", "latency_ms": 320}
  },
  "visual": {
    "icon": "🔗",
    "title": "通信链路正常",
    "subtitle": "主链路 150ms | 副链路 320ms",
    "progress": null
  }
}
```

## 指示器生命周期

```
创建 → 更新 → 完成/失败
```

1. **创建**：引擎做出决策时立即创建指示器
2. **更新**：任务执行过程中更新进度（如子任务完成数）
3. **完成/失败**：任务结束时更新最终状态

## 指示器输出规则

### 输出时机

| 事件 | 指示器类型 | 输出方式 |
|------|-----------|----------|
| 路由决策完成 | route_decision | 即时输出 |
| 崩溃风险检测 | crash_risk | 即时输出 + 通知手机端 |
| 故障转移触发 | failover | 即时输出 |
| 子任务完成 | completion（进度） | 进度更新 |
| 全部完成 | completion | 最终输出 |
| 链路状态变化 | link_status | 即时输出 |

### 输出格式

指示器以结构化 JSON 输出，前端/客户端可解析为可视化组件：

- `visual.icon`：状态图标（emoji）
- `visual.title`：主标题（一句话说明）
- `visual.subtitle`：副标题（详细原因）
- `visual.progress`：进度百分比（0-100 或 null）

### 指示器历史

- 保留最近 50 条指示器记录
- 按时间倒序排列
- 支持按 task_id 查询某个任务的所有指示器

## 指示器与用户交互

### 静默模式

当 `indicator_enabled=false` 时，指示器仅记录不输出，用于后台自动化场景。

### 详细模式

当用户要求"查看调用详情"时，输出完整的指示器 JSON，包括评分细节、候选设备列表等。

## 边界

- 指示器不阻塞任务执行（异步输出）
- 指示器不包含敏感信息（如密码、token）
- 指示器历史不跨会话持久化
