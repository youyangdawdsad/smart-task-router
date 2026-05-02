# 负载均衡器（Load Balancer）

## 概述

负载均衡器负责监控所有设备的在线状态和负载情况，确保任务被合理分配，避免单设备过载。当目标设备忙时，自动将任务调度到次优设备。

## 心跳检测机制

### 心跳协议

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 心跳间隔 | 30秒 | 每30秒向所有设备发送心跳 |
| 心跳超时 | 10秒 | 单次心跳等待响应的超时时间 |
| 离线判定 | 连续2次超时 | 连续2次心跳无响应标记为 offline |
| 恢复判定 | 1次成功心跳 | offline 后收到1次成功心跳恢复为 online |

### 心跳检测流程

每隔 30秒:
    for device in all_devices:
        response = send_heartbeat(device, timeout=10s)
        if response.success:
            device.consecutive_failures = 0
            device.load_status = compute_load(response)
            device.last_heartbeat = now()
            if device.status == OFFLINE:
                device.status = IDLE
                log("设备恢复在线: {device.id}")
        else:
            device.consecutive_failures += 1
            if device.consecutive_failures >= 2:
                device.status = OFFLINE
                device.load_status = "offline"
                log("设备离线: {device.id}, 触发failover")
                trigger_failover(device)

### 心跳响应信息

设备心跳响应包含：
- cpu_load：CPU 使用率 (0~1)
- memory_usage：内存使用率 (0~1)
- current_tasks：当前正在处理的任务数
- response_time_ms：响应延迟（毫秒）

## 任务队列管理

### 队列结构

task_queue:
  - urgent_queue: [任务列表，FIFO，优先出队]
  - normal_queue: [任务列表，FIFO]

### 调度流程

on_task_arrive(task):
    if task.urgency == "urgent":
        target = find_idle_device(task)
        if target: dispatch(task, target)
        else: # 紧急任务抢占最空闲设备
            target = find_least_busy(task)
            preempt_dispatch(task, target)
    else:
        target = find_idle_device(task)
        if target: dispatch(task, target)
        else: enqueue(task, wait_timeout=60s)

on_timeout(task):
    target = find_any_available(task)
    if target: dispatch(task, target)
    else: notify_user("所有设备忙碌，请稍后重试")

### 设备选择策略

find_idle_device：选择 load_status=idle 且 capability_match 最高的设备
find_least_busy：所有设备都 busy 时，选择 current_tasks 最少的设备
find_any_available：放宽标准，只要 online 就算可用

### 队列限制

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 队列最大长度 | 10 | 超过后拒绝新任务 |
| 等待超时 | 60秒 | normal 任务最大等待时间 |
| 紧急任务抢占 | 允许 | urgent 可抢占 busy 设备 |

## 负载均衡策略

### 轮询（Round Robin）— 备选
当多台设备能力相近时，按轮询方式分配任务，防止单设备长期过载。

### 最小连接（Least Connections）— 默认
优先选择当前任务数最少的设备。

### 加权分配（Weighted）— 可选
按设备能力评分加权分配：weight = capability_score × (1 - load_ratio)
load_ratio = current_tasks / max_concurrent

## 设备负载重算

每次任务完成/失败后重新计算设备负载：
- device.current_tasks == 0 → "idle"
- device.current_tasks < max_concurrent → "busy" (但还能接)
- device.current_tasks >= max_concurrent → "busy" (满载)

## 负载均衡日志

```json
{
  "log_id": "LB-{YYYYMMDD}-{序号}",
  "action": "dispatch|preempt|enqueue|timeout|failover",
  "task_id": "T-xxx",
  "target_device": "phone-01",
  "queue_depth": 2,
  "device_load": "idle",
  "reason": "idle设备可用",
  "timestamp": "ISO8601"
}
```

## 边界

- 不因负载均衡改变任务内容，只改变执行设备
- 负载信息不跨会话持久化（重启后重新采集）
- 心跳检测本身不消耗用户可见资源（后台静默运行）
