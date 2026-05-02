# 设备能力矩阵（Device Capability Matrix）

## 概述

设备能力矩阵定义了每类设备（手机/电脑）的能力清单、能力评分和状态管理规则。路由引擎据此判断哪台设备能执行什么任务。

## 设备类型能力清单

### 手机端（Phone）

| 能力ID | 能力名称 | 工具ID | 默认评分 | 适用平台 | 依赖条件 |
|--------|----------|--------|----------|----------|----------|
| CAP-SMS | 短信收发 | sms | 0.95 | Android/iOS | SIM卡已插入，短信权限已授予 |
| CAP-CALL | 通话管理 | call | 0.90 | Android/iOS | 通话权限已授予 |
| CAP-CAMERA | 相机控制 | camera | 0.95 | Android/iOS | 相机权限已授予，设备有摄像头 |
| CAP-LOCATION | 定位服务 | location | 0.95 | Android/iOS | 定位权限已授予，GPS已开启 |
| CAP-CALENDAR | 日历管理 | calendar | 0.80 | Android/iOS | 日历权限已授予 |
| CAP-ALARM | 闹钟管理 | alarm | 0.90 | Android/iOS | 闹钟权限已授予 |
| CAP-MEDIA | 媒体控制 | media | 0.85 | Android/iOS | 媒体权限已授予 |
| CAP-NOTIFICATION | 通知推送 | notification | 0.80 | Android/iOS | 通知权限已授予 |
| CAP-CONTACT | 联系人查询 | contacts | 0.85 | Android/iOS | 联系人权限已授予 |
| CAP-SEARCH-PHONE | 轻量搜索 | search | 0.60 | Android/iOS | 联网搜索（屏幕小，体验一般） |
| CAP-FILE-PHONE | 简单文件 | file | 0.40 | Android/iOS | 存储权限已授予，大文件差 |
| CAP-SCREENSHOT | 截屏功能 | screenshot | 0.90 | Android/iOS | 截屏权限已授予 |

### 电脑端（PC）

| 能力ID | 能力名称 | 工具ID | 默认评分 | 适用平台 | 依赖条件 |
|--------|----------|--------|----------|----------|----------|
| CAP-CODE | 代码执行 | code | 0.95 | Windows/macOS/Linux | 终端访问权限 |
| CAP-IDE | 开发环境 | ide | 0.95 | Windows/macOS/Linux | IDE已安装（VS Code等） |
| CAP-FILE-PC | 文件管理 | file | 0.90 | Windows/macOS/Linux | 文件系统访问权限 |
| CAP-BROWSER | 浏览器控制 | browser | 0.85 | Windows/macOS/Linux | 浏览器已安装 |
| CAP-TEXT | 大文本处理 | text | 0.85 | Windows/macOS/Linux | — |
| CAP-OFFICE | 办公套件 | office | 0.90 | Windows/macOS/Linux | Office/WPS已安装 |
| CAP-SEARCH-PC | 联网搜索 | search | 0.80 | Windows/macOS/Linux | 搜索引擎（体验优于手机） |
| CAP-NOTIFICATION-PC | 通知推送 | notification | 0.70 | Windows/macOS/Linux | 通知权限已授予 |

## 能力评分标准

### 评分维度

每个能力从三个维度评分（0-1分）：

| 维度 | 权重 | 1.0 | 0.7 | 0.3 |
|------|------|-----|-----|-----|
| 可用性（Availability） | 0.5 | 完全可用 | 部分可用（受限） | 不可用 |
| 性能（Performance） | 0.3 | <1秒响应 | 1-5秒响应 | >5秒响应 |
| 可靠性（Reliability） | 0.2 | >99%成功率 | 90-99%成功率 | <90%成功率 |

### 综合评分计算

```
capability_score = availability × 0.5 + performance × 0.3 + reliability × 0.2
```

### 评分示例

| 设备 | 能力 | 可用性 | 性能 | 可靠性 | 综合评分 |
|------|------|--------|------|--------|----------|
| 手机-01 | sms | 1.0 | 0.7 | 1.0 | 0.89 |
| 手机-01 | camera | 1.0 | 0.7 | 0.7 | 0.82 |
| PC-01 | code | 1.0 | 1.0 | 1.0 | 1.00 |
| PC-01 | office | 1.0 | 0.7 | 0.7 | 0.82 |

## 设备状态管理

### 状态字段

```json
{
  "device_id": "phone-01",
  "device_type": "phone|pc",
  "device_name": "用户可读名称",
  "online": true,
  "load_status": "idle|busy|offline",
  "current_tasks": 0,
  "max_concurrent": 3,
  "last_heartbeat": "2026-05-02T20:08:00+08:00",
  "heartbeat_latency_ms": 150,
  "capabilities": ["sms", "call"],
  "capability_scores": {"sms": 0.95}
}
```

### 状态判定规则

| 状态 | 条件 | 路由行为 |
|------|------|----------|
| idle | online=true, current_tasks < max_concurrent | 正常路由，score×1.0 |
| busy | online=true, current_tasks >= max_concurrent | 进入等待队列，score×0.3 |
| offline | online=false 或心跳超时 | 不可路由，触发 failover |

### 能力覆盖度计算

```
coverage = |{t ∈ tools_required : t ∈ D.capabilities}| / |tools_required|
```

- coverage = 1.0：设备完全覆盖任务需求
- 0 < coverage < 1：部分覆盖，需要协作或迁移
- coverage = 0：设备无法执行该任务

### 能力评分加权

```
device_score = Σ(capability_scores[t] for t in tools_required) / |tools_required|
```

取所有候选设备中 device_score 最高的作为路由目标。

## 能力约束

### 通用约束

1. **权限约束**：所有能力都需要相应的系统权限才能使用
2. **资源约束**：能力执行受设备资源（CPU、内存、存储）限制
3. **并发约束**：同一能力同时执行的任务数有限制（默认3个）
4. **时间约束**：能力执行有超时限制（默认30秒）

### 手机设备特殊约束

| 能力 | 约束 | 注意事项 |
|------|------|----------|
| sms | 需要SIM卡，可能产生费用 | 凌晨发送可能被运营商拦截 |
| call | 需要SIM卡，可能产生费用 | 部分地区有通话限制 |
| camera | 需要相机权限，可能被其他应用占用 | 前后摄像头切换有延迟 |
| location | 需要定位权限，GPS开启时耗电 | 室内定位精度较低 |
| alarm | 需要闹钟权限，可能被系统省电模式影响 | 部分设备有最大闹钟数量限制 |
| media | 需要媒体权限，可能与其他音频应用冲突 | 后台播放可能被系统限制 |
| screenshot | 需要截屏权限，可能被安全策略阻止 | 部分应用禁止截屏 |
| file | 需要存储权限，受沙盒限制 | iOS文件访问更受限 |

### PC设备特殊约束

| 能力 | 约束 | 注意事项 |
|------|------|----------|
| code | 需要终端访问权限，命令执行有风险 | 部分命令需要管理员权限 |
| ide | 需要IDE安装，项目路径需正确 | 不同IDE支持的语言不同 |
| file | 受文件系统权限限制 | 系统目录需要管理员权限 |
| browser | 需要浏览器安装，网页结构可能变化 | 自动化操作可能被反爬机制阻止 |
| office | 需要Office/WPS安装，文件格式兼容性 | 大型文档处理较慢 |

## 设备注册与发现

设备通过心跳机制自动注册到路由引擎：
1. 设备首次响应心跳 → 自动注册，记录 capabilities
2. 心跳正常 → 更新 last_heartbeat，维持 online 状态
3. 心跳超时 → 标记 offline，触发 failover
4. 设备下线前发送 bye 心跳 → 立即标记 offline

## 多设备场景

典型多设备拓扑：
- **1 Phone + 1 PC**：最常见，路由二选一
- **1 Phone + 多 PC**：PC 之间按 load balancing 分配
- **多 Phone + 1 PC**：Phone 之间按能力评分和负载选择

路由引擎不假设固定拓扑，通过 device_list 动态获取设备列表。

## 能力更新机制

1. **定期检测**：每5分钟检测一次设备能力状态
2. **事件触发**：设备状态变化时立即更新能力矩阵
3. **手动刷新**：用户可手动触发能力矩阵更新
4. **版本控制**：能力矩阵变更记录版本号，便于回滚

## 能力查询接口

```json
{
  "query": {
    "device_id": "phone-01",
    "capability": "sms"
  },
  "response": {
    "device_id": "phone-01",
    "capability": "sms",
    "score": 0.89,
    "details": {
      "availability": 1.0,
      "performance": 0.7,
      "reliability": 1.0
    },
    "constraints": ["需要SIM卡", "可能产生费用"],
    "last_updated": "2026-05-02T20:30:00+08:00"
  }
}
```
