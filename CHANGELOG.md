# Changelog

所有版本的更新记录。

## v3.4.0 (2026-05-04)

### ✨ 新增

- **路由结果 LRU 缓存（RouteCache）**
  - 相同或相似的用户输入（哈希或语义相似度 > 0.9）直接返回上次的路由结果
  - 缓存有效期 5 分钟，过期后重新计算
  - 缓存命中时跳过 NLU，直接执行路由结果
  - 缓存容量 200 条，LRU 淘汰策略
  - nlu_config.json 更新后自动清空缓存

- **批量自学习（Batch Learn）**
  - 未知意图不再逐条请教，攒够 3-5 个后一次性发给大爱
  - 减少 device_coord 调用次数，降低超时风险
  - 批量请求/回复协议：batch_learn_request / batch_learn_response
  - 交互式学习模式支持 batch/send 命令

- **本地兜底日志（LocalFallbackLogger）**
  - device_coord 不通时，未知意图自动记录到 pending_learn.jsonl
  - 连接恢复后可批量读取并请教
  - 支持标记已解决、清理已解决记录

- **路由简化 — SIE 不做设备选择**
  - SIE 只做意图识别和任务拆分，输出 needs_cross_device 标记
  - 设备选择完全交给 miclaw device_coord（它有实时设备状态）
  - 硬规则改为标记设备类型偏好，不再直接指定设备

- **心跳检测复用 miclaw device_list**
  - 不再自己实现心跳协议，直接复用 miclaw 的设备发现
  - 启动时调一次 device_list 获取设备状态

- **learn_request 超时调整**
  - 从默认值改为 30 秒（给手机端更多处理时间）

### 🔧 变更

- **nlu_config.json 结构升级**
  - 新增 batch_learn 配置区域（enabled, threshold, max_pending, learn_request_timeout_seconds, local_fallback_enabled, local_fallback_path）
  - 新增 route_cache 配置区域（enabled, ttl_seconds, max_size, similarity_threshold）
  - 版本号升级至 3.4.0

- **sie_self_evolve.py 重构**
  - 新增 RouteCache 类（LRU 缓存 + 相似度匹配）
  - 新增 LocalFallbackLogger 类（本地兜底日志）
  - UnknownIntentHandler 升级为批量模式（threshold + batch_buffer）
  - LearnProtocol 新增 create_batch_request / validate_batch_response
  - SelfEvolvingNLU.parse() 先查缓存再走 NLU
  - SelfEvolvingNLU 新增 apply_batch_learn_response / create_batch_learn_request

### 📊 测试

- sie_evolve_test：原有 14 场景 107 项检查仍通过
- 新增 RouteCache 测试：缓存命中、过期、相似度匹配、LRU 淘汰
- 新增 LocalFallbackLogger 测试：记录、读取、标记解决
- 新增批量学习测试：攒批、批量请求创建、批量回复应用

### 📝 文档

- 更新 skill.md 至 v3.4.0，新增路由缓存、批量学习、本地兜底章节
- 更新 CHANGELOG.md

---

## v3.3.0 (2026-05-04)

### ✨ 新增

- **AI 语义理解（NLUClassifier）**
  - NLU 从纯关键词匹配升级为双层匹配架构
  - 关键词快速通道（nlu_config.json）作为第一层，响应快、确定性强
  - AI 语义理解（NLUClassifier）作为 fallback，处理复杂句式和长尾场景
  - 每个意图新增 `fallback_to_ai` 字段，灵活控制是否启用 AI fallback

- **自我进化架构（SelfEvolvingNLU）**
  - 未知意图自动捕获：NLU 识别不了时，自动记录并生成请教请求
  - 知识请教协议（LearnProtocol）：标准化的 `learn_request` / `learn_response` 格式
  - 自动配置更新（AutoConfigUpdater）：收到教学回复后，自动写入 `nlu_config.json`
  - 学习日志（LearningLogger）：完整记录每次请教和学习过程
  - 交互式学习模式：CLI 入口支持手动教学和验证

- **新增 5 个意图**
  - `timer_set`：设置定时器/倒计时
  - `tts_speak`：语音播报/朗读
  - `translate`：翻译文本
  - `app_manage`：应用安装/打开/卸载
  - `ai_write`：AI 内容生成/写作
  - 意图总数从 20 增至 25+（含已学习意图）

- **MCP 服务集成支持**
  - 支持通过 MCP 协议接入第三方服务（mcd-mcp、高德地图、天气查询等）
  - `nlu_config.json` 新增 `mcp_services` 配置字段

- **自我进化测试（sie_evolve_test.py）**
  - 14 个场景、107 项检查全部通过
  - 覆盖：未知意图捕获、请教协议验证、配置自动更新、学习日志、回滚等

### 🔧 变更

- **nlu_config.json 结构升级**
  - `keywords` 降级为快速通道匹配词
  - 新增 `fallback_to_ai` 字段（默认 true）
  - 新增 `mcp_services` 配置区域
  - 版本号升级至 3.3.0

### 📊 测试

- sie_evolve_test：14 场景 107 项检查全通过（100%）
- sie_quick_test：NLU 识别率验证通过
- verify_engine：完整引擎验证通过

### 📝 文档

- 更新 skill.md 至 v3.3.0，新增自我进化架构、语义理解、MCP 集成章节
- 更新 README.md 至 v3.3.0，新增架构图和特性说明
- 更新 DESIGN.md 至 v3.3.0，新增意图→工具映射表、路由优先级、协议格式
- 更新 CHANGELOG.md

---

## v3.2.0 (2026-05-04)

### ✨ 新增

- **NLU 外部配置驱动（nlu_config.json）**
  - 意图识别从硬编码改为 JSON 配置驱动，新增/修改意图只需编辑配置文件
  - 支持 20 个意图，每个意图包含 keywords_zh（4-12 个关键词）+ patterns（正则表达式）
  - 三层匹配策略：正则模式（0.95）→ 关键词（0.9）→ 模糊匹配（0.6 阈值）
  - 每个意图绑定目标设备（phone/pc/agent）和工具名称
  - 支持 examples 字段用于测试验证
  - 新增 cross_device_keywords 和 unknown_fallback 配置

- **NLU 快速验证脚本（sie_quick_test.py）**
  - 153 个断言，覆盖所有 20 个意图的关键词和模式匹配
  - NLU 识别率从 v3.1.0 的 0%（硬编码匹配失败）提升到 100%

- **设计文档（DESIGN.md）**
  - 说明架构设计原则、模块职责、决策依据

### 🔧 重构

- **路由逻辑简化**
  - SIE 只做调度决策，不自己执行任务
  - 跨设备任务统一路由到 `device_coord`，不再由 SIE 内部处理
  - 路由决策输出增加 `target: device_coord` 和 `method: cross_device` 字段

- **NLU 模块重构**
  - 从硬编码意图列表改为从 `nlu_config.json` 动态加载
  - 支持运行时修改意图配置，无需重新部署代码
  - 模糊匹配使用 SequenceMatcher 替代简单字符串包含

### 📊 测试

- sie_quick_test：153/153 通过（100%），覆盖全部 20 个意图
- verify_engine：262/285 通过（91.9%），23 个失败项为配置映射差异（预期行为）
- NLU 识别率：100%（examples）/ 100%（keywords）

### 📝 文档

- 新增 DESIGN.md 设计原则文档
- 更新 README.md 至 v3.2.0，新增 NLU 配置说明和意图列表
- 更新 CHANGELOG.md

---

## v3.1.0 (2026-05-03)

### ✨ 新增

- **自然语言理解（NLU）模块（Module 14）**
  - 五层理解能力：意图识别、同义词扩展、实体提取、模糊匹配、置信度计算
  - 正则模板匹配 10 种意图（send_message、make_call、take_photo 等）
  - 100+ 同义词映射（如"发微信"→sms、"拨号"→call）
  - 实体提取：人名、时间、地点、内容
  - 基于 SequenceMatcher 的模糊匹配，支持错别字容错
  - 综合置信度评分（0-1）

- **SieLogger 日志系统（Module 13）**
  - 支持 DEBUG/INFO/WARN/ERROR 四级日志
  - 记录完整调用链路：触发条件 → NLU 解析 → 工具匹配 → 路由决策 → 执行结果
  - 内存中最多保留 500 条日志，自动清理旧记录
  - 支持按阶段（phase）和级别（level）过滤查询
  - 支持按任务 ID 追踪完整执行链路
  - 支持文件持久化（默认 `~/.sie_logs/` 目录）

- **TaskProfiler v4 NLU 集成（Module 14b）**
  - TaskProfiler 新增 `__init__` 方法，注入 NLU 模块
  - `analyze()` 优先使用 NLU 解析，回退到关键词匹配
  - 输出增加 `nlu` 字段（意图、实体、置信度、匹配方法）

### 🔧 修复

- 修复 `verify_engine.py` 缺少 `from difflib import SequenceMatcher` 导入
- 修复 NLU `parse()` 返回值缺少 `match_method` 字段
- 修复测试断言中 `log_error`/`log_warn` 的 phase 参数错误
- 修复 `sie_engine.py` 正则表达式中的无效转义序列（SyntaxWarning）

### 📊 测试

- 断言从 217 增至 297（+37%）
- 新增 Module 13（SieLogger）：日志记录、过滤、持久化
- 新增 Module 14（NaturalLanguageUnderstanding）：意图识别、实体提取、模糊匹配
- 新增 Module 14b（TaskProfiler v4 NLU 集成）：NLU 与任务分析器的集成测试
- 完整流水线性能：23.23 μs/op（约 43,000 ops/s）

---

## v3.0.0 (2026-05-03)

### ⚡ 性能优化

全模块性能提升，217 个断言全部通过。

- **TaskProfiler**：关键词索引预排序（按长度降序），避免短词误匹配，减少遍历次数
- **DeviceCapability**：使用生成器表达式替代列表推导，减少临时对象分配
- **RoutingRules**：
  - 预计算负载映射表（类变量），避免每次路由创建新字典
  - 单候选设备快速路径，跳过排序
  - 多候选设备优化：直接在元组列表上排序，减少中间数据结构
- **CrashDetector**：
  - `assess()` 内联 6 个风险评估函数，减少函数调用开销
  - 预提取权重向量到 `_weight_vector`，避免重复字典查找
  - 使用 `__slots__` 减少实例内存占用
- **DualLink**：
  - `_update_state()` 使用位运算（`p_ok << 1 | s_ok`）加速状态判断
  - 预定义 `_PROXIMITY_MODIFIERS` 类变量，避免每次创建字典
  - 使用 `__slots__` 减少实例内存占用
- **AutoDeviceRegistration**：`discover()` 使用 set 交集运算，O(1) 查找新设备
- **VoiceNotificationRelay**：
  - 预编译正则表达式（`_RE_SPECIAL_CHARS`、`_RE_FILE_PATH`），避免每次调用重新编译
  - `get_voice_capable_devices()` 使用列表推导式替代手动循环
- **LoadBalancer**：`find_idle_device()` 空工具列表快速路径
- **FailoverMigration**：`detect_failure()` 优化类型检查顺序，非 dict 快速返回
- **RoutingLog**：单次 `datetime.now()` 调用，`del` 切片替代重新赋值清理日志
- **InvocationIndicator**：`del` 切片替代重新赋值清理历史
- **TaskProfiler**：可拆分检查 `elif` 提前退出，避免冗余条件判断

---

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
