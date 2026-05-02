# 路由规则引擎（Routing Rules）

## 概述

路由规则引擎是整个系统的核心决策层，决定每个任务（或子任务）应该交给哪台设备执行。采用"硬规则兜底 + 软规则打分"的双层架构。

## 硬规则（Hard Rules）

硬规则优先级最高，不可被软规则覆盖。命中硬规则时直接路由，跳过打分。

### 设备绑定规则

| 规则ID | 触发条件 | 路由目标 | 原因 |
|--------|----------|----------|------|
| H-001 | tools_required 包含 sms | phone | 短信接口仅手机端可用 |
| H-002 | tools_required 包含 call | phone | 通话接口仅手机端可用 |
| H-003 | tools_required 包含 camera | phone | 相机接口仅手机端可用 |
| H-004 | tools_required 包含 location | phone | GPS仅手机端可用 |
| H-005 | tools_required 包含 alarm | phone | 闹钟仅手机端可用 |
| H-006 | tools_required 包含 media | phone | 媒体控制仅手机端可用 |
| H-007 | tools_required 包含 screenshot | phone | 截屏仅手机端可用 |
| H-008 | tools_required 包含 ide | pc | IDE仅电脑端可用 |
| H-009 | tools_required 包含 office | pc | 办公套件仅电脑端可用 |

### 不可迁移规则

| 规则ID | 条件 | 说明 |
|--------|------|------|
| H-010 | 任务涉及支付/退款 | 不自动路由，提醒用户手动操作 |
| H-011 | 任务涉及删除不可恢复数据 | 不自动路由，提醒用户确认 |
| H-012 | 所有设备 offline | 终止路由，通知用户设备全部离线 |

## 软规则（Soft Rules）

当没有硬规则命中时，对每个候选设备进行打分。

### 评分公式

route_score = capability_match × 0.5 + load_factor × 0.3 + proximity × 0.2

各因子计算：

1. capability_match（能力匹配度）= Σ(capability_scores[t] for t in tools_required) / len(tools_required)
2. load_factor（负载因子）：idle→1.0, busy→0.3, offline→0.0
3. proximity（可达性）：online且心跳延迟<2s→1.0, <5s→0.8, >=5s→0.5, offline→0.0

### 决策逻辑

```python
MIN_ROUTE_SCORE = 0.2  # 可配置参数

def route(task_profile, devices):
    candidates = [d for d in devices if d["online"]]
    if not candidates:
        return {"status": "all_offline"}
    # 硬规则优先
    for rule in HARD_RULES:
        if rule.matches(task_profile):
            target = find_device(rule.target_type, candidates)
            if target:
                return {"target": target, "method": "hard_rule", "reason": f"硬规则: {rule.id}"}
    # 软规则打分
    scores = []
    for device in candidates:
        score = compute_score(task_profile, device)
        scores.append((device, score))
    scores.sort(key=lambda x: x[1], reverse=True)
    best_device, best_score = scores[0]
    if best_score < MIN_ROUTE_SCORE:
        return {"status": "no_suitable_device", "candidates": scores}
    return {"target": best_device, "method": "soft_rule", "score": best_score, "all_scores": scores}
```

## 协作规则（Collaboration Rules）

当 TaskProfile 的 splittable=true 时，执行协作路由：

### 拆分策略

1. 按环境约束拆分：phone-only 的子任务 → 手机，pc-only 的 → 电脑
2. 按工具拆分：不同工具集的子任务独立路由
3. 按依赖关系排序：无依赖的子任务可并行，有依赖的串行

### 子任务合并

如果多个子任务都路由到同一设备，可以合并为一个批量任务减少调度开销。

## 路由决策日志

```json
{
  "log_id": "ROUTE-{YYYYMMDD}-{序号}",
  "task_id": "T-xxx",
  "timestamp": "ISO8601",
  "input": {"tools_required": ["sms", "file"], "complexity": "medium", "environment": "any"},
  "decision": [
    {"sub_task_id": "ST-1", "target_device": "phone-01", "method": "hard_rule", "rule_id": "H-001", "reason": "sms→phone", "score": null},
    {"sub_task_id": "ST-2", "target_device": "pc-01", "method": "soft_rule", "rule_id": null, "reason": "file能力pc更强(score=0.88)", "score": 0.88}
  ]
}
```

## 路由约束

- 每个设备同时处理的任务数不超过 max_concurrent（默认3）
- 同一任务的子任务尽量少跨设备（减少协调开销）
- 路由决策延迟不超过 500ms（避免用户等待过久）
- 路由日志保留最近 100 条，超过自动清理旧记录
