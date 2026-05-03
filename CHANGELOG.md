# Changelog

所有版本的更新记录。

## v2.0.0 (2026-05-03)

### 🔄 重大变更

- **更名**：Smart Task Router → 智能调用引擎（Smart Invocation Engine, SIE）
- 测试脚本从 `verify_router.py` 更名为 `verify_engine.py`

### ✨ 新增

- **智能调用指示器（Invocation Indicator）**
  - 每次路由决策产生可见反馈，用户实时感知引擎工作状态
  - 支持 5 种指示器类型：路由决策、崩溃风险、故障转移、任务完成、链路状态
  - 指示器历史管理（最近 50 条），支持按 task_id 查询
  - 可通过 `indicator_enabled` 配置开关

- **崩溃风险检测（Crash Detector）**
  - 6 维风险因子评估：文件大小、内存占用、CPU 负载、并发任务、代码风险、磁盘空间
  - 三级风险等级：低（<0.3）、中（0.3-0.7）、高（≥0.7）
  - 高风险自动拦截：拆分为更小的子任务，通过副链路通知手机端
  - 手机端接管调度，逐步向电脑端分发子任务，降低崩溃风险

- **双链路通信（Dual Link）**
  - 主链路（device_chat）+ 副链路（网络心跳）一主一副架构
  - PC 端启动时自动建立副链路连接
  - 15 秒心跳间隔，3 次超时判定断开
  - 5 种链路状态：FULL、PRIMARY_ONLY、SECONDARY_ONLY、DEGRADED、OFFLINE
  - 副链路支持紧急通知：崩溃风险拆分、设备恢复、状态同步
  - 副链路恢复后自动重新路由 pending 任务

### 🔧 优化

- 路由决策流程增加崩溃风险评估步骤
- 故障检查支持双链路任一可用即可判定设备在线
- proximity 评分考虑双链路状态（仅副链路可用时 ×0.5）
- 路由日志增加 crash_risk 和 indicator 字段

### 📊 测试

- 断言从 73 增至 163（+123%）
- 新增 Module 8（InvocationIndicator）：23 个断言
- 新增 Module 9（CrashDetector）：32 个断言
- 新增 Module 10（DualLink）：35 个断言

### 📝 文档

- 新增 README.md
- 新增 CHANGELOG.md
- 新增 3 个参考文档：invocation-indicator.md、crash-detector.md、dual-link.md
- 更新 routing-rules.md（增加崩溃风险拦截层）
- 更新 failover-migration.md（增加副链路恢复）

---

## v1.2.0 (2026-05-02)

### ✨ 新增

- RoutingLog 路由决策日志模块，记录每次路由决策的完整信息（自动清理旧记录）

### 🔧 修复

- 软规则增加 MIN_ROUTE_SCORE 阈值（0.2），低分设备不再被路由
- 删除重复文档 device-capabilities.md，统一为 device-capability.md
- routing-rules.md 伪代码与实际代码对齐（score 阈值、返回格式）

### 📊 测试

- 新增 Module 6（RoutingLog）和 Module 7（Edge Cases）
- 断言从 55 增至 73
- 覆盖空工具列表、多硬规则冲突、score 阈值拦截、高风险操作检测等边界场景

---

## v1.1.0 (2026-05-02)

### 🔧 修复

- proximity 评分从二值(online/offline)改为按心跳延迟分级
- FailoverMigration 添加 L1/L2 独立计数器，真正限制迁移次数
- TaskProfiler 输出增加 task_id 和 estimated_duration_seconds
- 搜索关键词加入关键词映射表

### 📊 测试

- verify_router.py 添加 main 入口和 55 个断言测试

### 📝 文档

- 合并 device-capabilities.md 和 device-capability.md 为统一文档
- 新增硬规则不可迁移保护（支付/删除等高风险操作）

---

## v1.0.0 (初始版本)

### ✨ 初始发布

- 五大核心模块：TaskProfiler, DeviceCapability, RoutingRules, LoadBalancer, FailoverMigration
- 硬规则 + 软规则双层路由架构
- 三级故障转移策略
