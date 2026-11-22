# 热点驱动宣传创作工作台实施计划

> **面向 AI 开发者：** 实施本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务顺序逐项执行。所有步骤使用复选框跟踪。  
> **重要限制：** 本计划只包含实施指令，不包含任何实现代码。执行者必须先写或修改测试，再进行实现，并通过指定验证后才能进入下一步。

**目标：** 在保留现有 FastAPI、Jinja2/HTMX、SQLite 和自定义 Agent Runner 的基础上，将当前结构化 Mock Demo 补齐为可接真实模型、可安全处理素材、具备严格人机门禁、可恢复运行并适合 GitHub 开源与面试展示的单 Agent 产品。

**架构：** 继续采用 Python 模块化单体。Web 页面、JSON API、Agent 编排、后台任务、数据库和本地文件存储位于同一仓库和单一 Uvicorn 进程中；Agent 通过确定性 Planner、白名单 Tool Registry、Pydantic 契约、数据库持久化步骤和人工中断实现状态图语义，不引入 LangGraph、React、Celery 或 Redis。

**技术栈：** Python 3.12、FastAPI、Uvicorn、Jinja2、HTMX、Vanilla JavaScript、Pydantic 2、SQLAlchemy 2、Alembic、SQLite、HTTPX、python-docx、pypdf、Pillow、pytest、Playwright、Ruff。

**规格：** `memory-bank/design-document.md`

**技术决策：** `memory-bank/tech-stack.md`

## 全局约束

- 写任何代码前必须完整阅读 `memory-bank/architecture.md` 和 `memory-bank/design-document.md`。
- 每完成一个重大功能或里程碑，必须更新 `memory-bank/architecture.md` 和 `memory-bank/progress.md`，并运行对应文档一致性测试。
- 所有虚拟环境、缓存、数据库、上传、导出、浏览器数据和测试产物必须位于 `D:\aipm\demo` 内。
- 保留现有 Python 模块化单体，不引入 Next.js、React、LangGraph、多 Agent、Celery、Redis、RabbitMQ、Kafka、PostgreSQL 或 Kubernetes。
- 默认 `MockAIProvider` 必须始终可离线运行；真实 Provider 失败时不得静默回退为 Mock。
- 活动事实与参考案例必须在数据库、模型输入和界面展示三个层面隔离。
- 正常且有来源的事实允许自动确认；冲突、低置信度、身份推断、无来源引语、隐私风险和关键缺失必须暂停并询问用户。
- Agent 每次中断必须一次提交当前项目快照中全部已知阻塞问题；未收到完整有效回答前不得继续执行相关流程。
- 至少存在项目名称、两条符合类型要求的已确认事实、一个有效参考案例和一张有效方法卡，才能生成策略。
- 三个策略必须至少在叙事主角、开头方式和文章结构中的两个维度存在差异；生成后必须等待用户主动选择。
- 未成年人敏感信息、无来源人物身份或引语、仍与事实卡冲突的确定性陈述不得仅靠确认放行导出。
- 所有模型输入输出均使用 Pydantic 契约；结构错误最多修复一次，网络临时错误最多重试一次。
- 路径读写和删除前必须解析绝对路径并验证其位于项目允许目录内。
- 所有数据库结构变化必须通过 Alembic migration 完成。
- 每个任务完成后只提交该任务涉及的文件；提交前必须通过任务级测试。

## 当前基线

- 仓库已有 FastAPI 页面与 API、Jinja2/HTMX UI、SQLAlchemy/SQLite、Alembic、素材解析、事实卡、案例拆解、策略、稿件、质检、导出和自定义 Agent Runner。
- 仓库已有 Mock Provider、故障注入、Agent 调用上限、暂停恢复、输入指纹、启动恢复、单元测试、集成测试和 Playwright 测试。
- 真实 OpenAI-compatible Provider 尚未实现，当前选择该 Provider 会拒绝启动。
- 图片解析仍返回 Demo 描述，链接读取、安全抓取、真实视觉能力和人工说明降级尚未完成。
- 策略目前会自动选中推荐项，与“必须由用户主动选择”的已确认设计不一致。
- 当前 Planner 允许无案例继续，事实最低集合规则也与已确认设计不一致。
- 段落级改写、事实锁定、撤销最近一次 Agent 改写和完整导出附录尚未实现。
- `memory-bank` 已存在，`design-document.md`、`tech-stack.md` 和 `implementation.md` 已完成需求定稿；`architecture.md` 与 `progress.md` 仍为空，必须在实施任务 1 初始化。
- 当前执行 `scripts/test.ps1` 会在测试收集阶段因 Python 运行时解析工作目录失败而退出；必须先修复测试基线。

## 文件职责图

| 区域 | 主要文件 | 职责 |
| --- | --- | --- |
| 运行环境 | `scripts/runtime-env.ps1`、`scripts/setup.ps1`、`scripts/test.ps1`、`pyproject.toml`、requirements 文件 | Python 选择、D 盘运行目录、依赖与测试入口 |
| 配置 | `workbench/settings.py`、`.env.example` | Provider、模型、超时、路径和安全限制 |
| Agent | `workbench/agent/runner.py`、`planner.py`、`snapshot.py`、`schemas.py`、`tools/` | 状态判断、工具调用、中断、恢复和步骤记录 |
| 模型 | `workbench/ai/provider.py`、`factory.py`、`schemas/`、新增真实 Provider 与 HTTP transport | 结构化模型契约和供应商适配 |
| 素材 | `workbench/materials/parsers.py`、`service.py`、`limits.py`、`workbench/jobs/runner.py` | 文件校验、解析、分块、图片降级和后台任务 |
| 事实 | `workbench/facts/extractor.py`、`service.py`、`eligibility.py` | 去重、来源、状态转换、自动确认和冲突处理 |
| 案例 | `workbench/references/service.py`、新增安全抓取器、references API 与页面 | 文本、截图、链接录入，拆解和删除失效 |
| 策略 | `workbench/strategies/service.py`、`difference.py`、策略 API 与页面 | 三策略生成、差异校验和人工选择 |
| 稿件 | `workbench/drafts/service.py`、schemas、API、编辑器模板与脚本 | 单个推荐标题、大纲、Markdown 正文、改写、锁定和单步撤销 |
| 质检导出 | `workbench/quality/`、`workbench/exports/`、quality/export API 与页面 | 风险分类、问题处置、Markdown 和纯文本 |
| 持久化 | `workbench/db/models.py`、`session.py`、`alembic/versions/` | 数据模型、SQLite 连接和迁移 |
| 验证 | `tests/unit/`、`tests/integration/`、`tests/e2e/` | 行为、契约、恢复、安全和用户流程 |

## 重点审查风险

1. **恶意或异常外部链接：** 内网地址、重定向到私网、超大响应和非 HTML 内容必须被拒绝；由任务 15 的安全抓取测试覆盖。
2. **素材或事实被用户修改时后台结果过期：** 旧结果必须丢弃并重新规划；由任务 18、22 和 26 的幂等、revision 与恢复测试覆盖。
3. **模型返回合法 JSON 但引用不存在的事实 ID：** Provider 结果必须在持久化前被业务校验拒绝；由任务 9、10 和 25 的契约与业务校验测试覆盖。
4. **高风险问题被错误标记为已接受并导出：** 不可确认问题必须保持硬阻塞；由任务 29 和 32 的质检与导出测试覆盖。
5. **重启或刷新发生在 WAITING_USER、PROCESSING 或保存中：** 页面和 Agent 必须从数据库恢复到一致状态；由任务 16、22、27 和 35 的恢复测试覆盖。

---

## 里程碑一 运行基线与架构记忆

### 任务 1：初始化架构记忆与进度记录

**文件：**

- 读取：`memory-bank/design-document.md`
- 修改：`memory-bank/architecture.md`
- 修改：`memory-bank/progress.md`
- 新建：`tests/unit/test_memory_bank_contract.py`
- 修改：`CLAUDE.md`
- 修改：`AGENTS.md`

**产出：** 可供所有后续 AI 开发者强制阅读的产品基线、当前架构说明和实施进度基线。

- [x] **步骤 1：** 将 `memory-bank/design-document.md`、`memory-bank/tech-stack.md` 和 `memory-bank/implementation.md` 设为实施期间的权威文档；在空的 `memory-bank/architecture.md` 中记录当前模块边界、运行命令、数据流、Agent 决策流和已知缺口，在空的 `memory-bank/progress.md` 中建立里程碑状态、最近验证和下一任务记录；两个仓库说明文件必须引用当前无 `@` 前缀的真实路径。**验证测试：** 新增 `test_memory_bank_contract.py`，验证五个 memory-bank 文件存在、三个权威文档非空、架构与进度文件完成初始化，并验证 `CLAUDE.md` 与 `AGENTS.md` 以三个当前路径规则结尾；运行 `scripts/test.ps1 tests/unit/test_memory_bank_contract.py -q`，实际结果 `4 passed in 0.04s`。

### 任务 2：修复可重复的 Python 与测试入口

**文件：**

- 修改：`scripts/runtime-env.ps1`
- 修改：`scripts/setup.ps1`
- 修改：`scripts/test.ps1`
- 修改：`scripts/e2e.ps1`
- 修改：`pyproject.toml`
- 修改：`tests/unit/test_runtime_paths.py`

**产出：** 在 `D:\aipm\demo` 中可重复创建和调用 Python 3.11 或 3.12 虚拟环境，测试不再借用错误的 Conda 标准库。

- [x] **步骤 2：** 让 setup 脚本显式验证基础解释器版本和路径，拒绝不受支持或无法访问工作区的解释器；测试脚本必须确认虚拟环境解释器与其标准库来自同一环境，并继续把临时目录、字节码和缓存定向到 `.runtime`。**验证测试：** 扩展 `test_runtime_paths.py` 覆盖解释器一致性、所有运行目录位于 `D:\aipm\demo`、不受支持版本被拒绝；先运行该单测，再运行 `scripts/test.ps1 -q`，预期测试完成收集且不再出现工作目录 `PermissionError`。

### 任务 3：锁定依赖与安装契约

**文件：**

- 修改：`pyproject.toml`
- 修改：`requirements.txt`
- 修改：`requirements-dev.txt`
- 新建：`requirements.lock.txt`
- 修改：`scripts/setup.ps1`
- 新建：`tests/unit/test_dependency_contract.py`

**产出：** 与 `memory-bank/tech-stack.md` 一致且可复现的运行依赖和开发依赖。

- [x] **步骤 3：** 将 Python 支持范围收敛到 3.11 至 3.12，补充运行时 HTTPX 与开发时 Ruff，生成锁定依赖文件，并让 setup 只从锁定文件安装；不得引入设计外框架。**验证测试：** 新增依赖契约测试，验证必需包存在、禁止包不存在、运行依赖没有仅放在开发依赖中、锁定文件与声明文件一致；运行 `scripts/test.ps1 tests/unit/test_dependency_contract.py -q`，并在空的临时虚拟环境运行 setup，预期安装成功且所有缓存仍在项目 `.runtime`。

### 任务 4：加固 SQLite 单实例连接

**文件：**

- 修改：`workbench/db/session.py`
- 修改：`tests/integration/test_projects_repository.py`
- 新建：`tests/integration/test_sqlite_runtime.py`

**产出：** 启用外键、WAL 和 5000 毫秒 busy timeout 的单实例 SQLite 连接。

- [x] **步骤 4：** 在每个数据库连接上统一应用外键、WAL 和 busy timeout，并保持 Session 生命周期短且可预测；不得在网络模型调用期间保持写事务。**验证测试：** 新增 SQLite 运行测试，查询三个 PRAGMA 的实际值，并模拟一个短暂写锁验证第二个写入不会立即以 database locked 失败；运行 `scripts/test.ps1 tests/integration/test_sqlite_runtime.py tests/integration/test_projects_repository.py -q`，预期全部通过。

### 任务 5：更新第一阶段架构记忆

**文件：**

- 修改：`memory-bank/architecture.md`
- 修改：`memory-bank/progress.md`
- 修改：`tests/unit/test_memory_bank_contract.py`

**产出：** 记录已验证的 Python、依赖、SQLite 和运行目录事实。

- [x] **步骤 5：** 在架构文档中更新实际解释器范围、安装链路、SQLite PRAGMA、单 worker 约束和当前测试基线，不记录尚未实现的目标能力。**验证测试：** 扩展 memory-bank 契约测试，验证架构文档包含当前迁移版本、测试入口和 SQLite 配置；运行 `scripts/test.ps1 tests/unit/test_memory_bank_contract.py -q`，预期通过。

## 里程碑二 真实模型 Provider

### 任务 6：定义真实 Provider 配置与错误模型

**文件：**

- 修改：`workbench/settings.py`
- 修改：`.env.example`
- 新建：`workbench/ai/errors.py`
- 新建：`tests/unit/ai/test_provider_settings.py`

**产出：** 可验证的模型地址、文本模型、可选视觉模型、API Key、超时和重试配置。

- [x] **步骤 6：** 增加真实 Provider 必需配置和四类超时，使用 SecretStr 保存密钥，并定义认证、限流、网络、结构和内容错误的稳定错误码；选择 Mock 时不得要求密钥，选择真实 Provider 时缺失必填项必须启动失败。**验证测试：** 新增设置测试覆盖 Mock 无密钥、真实 Provider 完整配置、缺失 base URL、缺失模型和密钥脱敏；运行 `scripts/test.ps1 tests/unit/ai/test_provider_settings.py -q`，预期全部通过。

### 任务 7：实现受控 HTTP transport

**文件：**

- 新建：`workbench/ai/http_transport.py`
- 修改：`workbench/settings.py`
- 新建：`tests/unit/ai/test_http_transport.py`

**产出：** 供模型 Provider 复用的 HTTPX 客户端、超时、连接限制、一次临时错误重试和错误映射。

- [x] **步骤 7：** 实现共享 transport，分别设置 connect、read、write 和 pool timeout；只对网络错误、429 和 5xx 重试一次，认证和请求错误不重试；任何日志和异常都必须移除 Authorization 值。**验证测试：** 使用本地假 HTTP transport 覆盖成功、超时、429 后成功、连续 5xx、401 和密钥脱敏；运行 `scripts/test.ps1 tests/unit/ai/test_http_transport.py -q`，预期请求次数和错误码均符合规则。

### 任务 8：实现案例拆解的真实模型调用

**文件：**

- 新建：`workbench/ai/openai_compatible_provider.py`
- 修改：`workbench/ai/provider.py`
- 修改：`workbench/ai/schemas/reference.py`
- 新建：`tests/unit/ai/test_openai_reference_analysis.py`

**产出：** 可将用户案例转换为结构化钩子、情绪、结构、图片作用、迁移方法和禁用表达的真实 Provider 方法。

- [x] **步骤 8：** 实现案例拆解请求和 Pydantic 校验，确保活动事实不会作为该方法输入，保留 source ID，并在结构失败时只执行一次格式修复。**验证测试：** 使用假服务验证正常结构、缺字段、错误 source ID、第一次结构错误后修复成功和第二次仍失败；运行 `scripts/test.ps1 tests/unit/ai/test_openai_reference_analysis.py -q`，预期全部通过且请求体不包含活动事实字段。

### 任务 9：实现策略生成的真实模型调用

**文件：**

- 修改：`workbench/ai/openai_compatible_provider.py`
- 修改：`workbench/ai/schemas/strategy.py`
- 新建：`tests/unit/ai/test_openai_strategy_generation.py`

**产出：** 恰好三个策略的结构化输出，并保留合法事实 ID 与方法摘要。

- [x] **步骤 9：** 实现策略生成请求，拒绝不足三个、重复策略、未知事实 ID 和无方法来源的返回；只把已确认事实摘要和方法卡传给模型，不传参考原文。**验证测试：** 覆盖三个有效策略、策略数量错误、事实 ID 越权、两个以上差异维度不足和请求体泄漏参考原文；运行 `scripts/test.ps1 tests/unit/ai/test_openai_strategy_generation.py -q`，预期全部通过。

### 任务 10：实现推荐标题 大纲 正文和质检调用

**文件：**

- 修改：`workbench/ai/openai_compatible_provider.py`
- 修改：`workbench/ai/schemas/draft.py`
- 修改：`workbench/ai/schemas/quality.py`
- 新建：`tests/unit/ai/test_openai_content_generation.py`
- 新建：`tests/unit/ai/test_openai_quality_check.py`

**产出：** 一个推荐标题、一份大纲、正文、事实引用和质检问题的真实结构化输出；标题和大纲生成后可直接编辑，不增加暂停门禁。

- [x] **步骤 10：** 实现标题大纲、正文和质检三个调用，标题响应必须恰好包含一个推荐标题，正文引用只能使用输入事实 ID，质检只能返回允许的问题类型和风险等级，任何未知 ID 或内部推理字段都必须被拒绝。**验证测试：** 使用假服务分别覆盖正常生成、标题缺失或返回多个、引用未知事实、质检类型非法、结构修复一次和第二次失败，并验证生成标题和大纲后 Agent 不进入 WAITING_USER；运行两个新测试文件，预期全部通过。

### 任务 11：接通 Provider 工厂与启动验证

**文件：**

- 修改：`workbench/ai/factory.py`
- 修改：`workbench/main.py`
- 修改：`tests/unit/ai/test_provider_factory.py`
- 新建：`tests/integration/ai/test_openai_provider_contract.py`

**产出：** Mock 和真实 Provider 均可通过同一工厂创建，错误配置明确失败，不静默降级。

- [x] **步骤 11：** 在工厂中构造真实 Provider，并在应用启动时验证配置；保留 Mock 为默认值；真实 Provider 的契约测试必须使用本地假 HTTP 服务，不访问公网。**验证测试：** 运行 factory 单测和 Provider 集成契约，验证两种 Provider、未知 Provider、真实配置缺失、全部 Provider 方法和密钥不泄漏；执行 `scripts/test.ps1 tests/unit/ai tests/integration/ai -q`，预期全部通过。

### 任务 12：更新真实 Provider 架构记忆

**文件：**

- 修改：`memory-bank/architecture.md`
- 修改：`memory-bank/progress.md`
- 修改：`tests/unit/test_memory_bank_contract.py`

**产出：** 记录 Provider 边界、错误模型、重试策略、结构化输出和禁止访问的资源。

- [x] **步骤 12：** 只记录已通过测试的真实 Provider 能力、配置字段、超时、错误码和 Mock 保底路径。**验证测试：** 扩展 memory-bank 测试，验证文档包含 Provider 接口、Mock 默认、真实 Provider 不静默降级和一次重试规则；运行对应测试，预期通过。

## 里程碑三 素材和案例输入

### 任务 13：保留 DOCX 与 PDF 来源定位

**文件：**

- 修改：`workbench/materials/parsers.py`
- 修改：`workbench/jobs/runner.py`
- 修改：`workbench/agent/tools/materials.py`
- 修改：`workbench/ai/schemas/material.py`
- 新建：`tests/unit/materials/test_structured_parsers.py`
- 修改：`tests/integration/api/test_materials_api.py`

**产出：** 每个文档产生多个可定位 SourceChunk，而不是把整份文件压成一个段落。

- [x] **步骤 13：** 让 DOCX 按非空段落和表格行分块，让 PDF 按页和文本块分块；解析结果统一包含摘要、分类、状态和来源定位，Agent 工具与后台 Job 必须调用同一个解析服务。**验证测试：** 使用包含段落、表格和多页 PDF 的固定夹具，验证 chunk 数量、page 或 paragraph 定位、空页处理、重复解析不重复插入；运行素材解析单测和材料 API 集成测试，预期全部通过。

### 任务 14：实现图片能力适配器和人工降级

**文件：**

- 新建：`workbench/materials/image_understanding.py`
- 修改：`workbench/materials/parsers.py`
- 修改：`workbench/ai/provider.py`
- 修改：`workbench/ai/openai_compatible_provider.py`
- 修改：`workbench/settings.py`
- 新建：`tests/unit/materials/test_image_understanding.py`

**产出：** 视觉模型优先的图片处理和明确的人工场景说明降级，首版不依赖本地 OCR。

- [x] **步骤 14：** 将图片校验、视觉模型读取和人工说明降级分层；有视觉模型时优先读取图片文字与场景，未配置或调用失败时必须返回 NEEDS_REVIEW 并要求人工说明，而不是 Demo 假描述；视觉推断不得自动产生人物身份或默认确认的关键事实。**验证测试：** 覆盖合法图片、损坏图片、超大像素、无视觉模型、视觉成功、视觉超时、识别结果低置信度、人工说明恢复和返回人物身份推断；运行图片测试，预期错误和降级状态符合设计，基础依赖中不包含重型 OCR。

### 任务 15：实现安全的参考链接读取

**文件：**

- 新建：`workbench/references/fetcher.py`
- 修改：`workbench/settings.py`
- 新建：`tests/unit/references/test_safe_fetcher.py`

**产出：** 仅允许公开 HTTP 或 HTTPS 静态页面的受限读取器。

- [x] **步骤 15：** 在请求前和每次重定向后解析地址并拒绝 loopback、私网、link-local、保留地址和非 HTTP 协议；限制重定向、响应大小、内容类型和总耗时；不得携带 Cookie 或执行 JavaScript。**验证测试：** 使用本地假 DNS 和 HTTP transport 覆盖公网成功、localhost、IPv6 loopback、私网域名、公开地址重定向到私网、超大响应、非 HTML 和超时；运行安全抓取测试，预期仅公开静态页面成功。

### 任务 16：完成文本 链接和截图三种案例录入

**文件：**

- 修改：`workbench/db/models.py`
- 新建：下一个 Alembic migration
- 修改：`workbench/references/service.py`
- 修改：`workbench/api/references.py`
- 修改：`workbench/web/inspiration_routes.py`
- 修改：`workbench/templates/inspiration/reference_window.html`
- 修改：`tests/integration/references/test_isolation.py`
- 新建：`tests/integration/references/test_reference_inputs.py`

**产出：** 文本、公开链接和截图均可转换为 ReferenceCase，读取失败时保留输入并引导降级。

- [x] **步骤 16：** 为案例保存输入类型、源 URL、可选本地原文路径和读取状态；链接读取成功后持久化受限正文，截图复用图片适配器；删除案例时删除其本地原文并使分析和方法结果失效。**验证测试：** 覆盖三种输入、链接失败后保留 URL、截图待确认、删除原文、跨项目不可访问和参考原文永不进入事实表；运行 migration、reference 集成测试和隔离测试，预期全部通过。

### 任务 17：更新素材与案例架构记忆

**文件：**

- 修改：`memory-bank/architecture.md`
- 修改：`memory-bank/progress.md`
- 修改：`tests/unit/test_memory_bank_contract.py`

**产出：** 记录解析器、来源定位、图片降级、安全抓取和案例删除生命周期。

- [x] **步骤 17：** 更新数据流和安全边界，并标明图片视觉推断不能直接成为默认确认事实。**验证测试：** 扩展文档契约测试，验证架构文档列出三种案例输入、SSRF 边界、SourceChunk 定位和图片事实规则；运行测试，预期通过。

## 里程碑四 事实门禁与人工中断

### 任务 18：让事实抽取可重复且可去重

**文件：**

- 修改：`workbench/db/models.py`
- 新建：下一个 Alembic migration
- 修改：`workbench/facts/extractor.py`
- 修改：`workbench/facts/service.py`
- 新建：`tests/integration/facts/test_idempotent_extraction.py`

**产出：** 相同来源重复执行不会产生重复事实，多个来源可汇总到同一事实卡。

- [x] **步骤 18：** 增加规范化值或稳定指纹，按项目、事实类型和规范化内容合并候选事实，并保留所有来源关系；重新解析单个素材时只替换该素材贡献的关系。**验证测试：** 覆盖相同素材重复抽取、两个素材支持同一事实、删除一个来源后仍有其他来源、删除最后来源后失效；运行新的集成测试和现有来源删除测试，预期全部通过。

### 任务 19：对齐事实自动确认规则

**文件：**

- 修改：`workbench/facts/service.py`
- 修改：`workbench/agent/planner.py`
- 修改：`workbench/agent/snapshot.py`
- 修改：`tests/unit/facts/test_state_machine.py`
- 修改：`tests/unit/agent/test_planner.py`

**产出：** 正常有来源事实默认通过，异常事实统一进入人工确认。

- [x] **步骤 19：** 将自动确认规则固定为有来源、无冲突、置信度至少 0.7、非身份推断；引语必须来自采访或发言材料；图片视觉推断、PERSON、ROLE 和低置信度事实保持待确认。**验证测试：** 参数化覆盖每个通过条件和阻塞条件，验证 Planner 只有在异常实际阻塞后续时才暂停；运行事实状态机和 Planner 单测，预期全部通过。

### 任务 20：对齐策略前最低事实集合

**文件：**

- 修改：`workbench/agent/planner.py`
- 修改：`workbench/agent/snapshot.py`
- 修改：`workbench/strategies/service.py`
- 修改：`workbench/agent/tools/strategies.py`
- 修改：`tests/unit/agent/test_planner.py`
- 修改：`tests/integration/strategies/test_generation.py`

**产出：** 项目名称、两条符合类型要求的已确认事实、一个有效案例和至少一张由 Agent 自动推荐或用户保留的有效方法卡构成唯一策略生成门禁；方法卡不增加人工确认步骤。

- [x] **步骤 20：** 移除当前三条或四条事实的不一致判断，统一要求至少一条活动或环节事实和一条人物、地点、观点、引语、数字或结果等具体事实，同时强制至少一个有效案例和一张有效方法卡；案例拆解成功时由 Agent 自动推荐方法卡，用户可调整但无需确认。**验证测试：** 覆盖零、一、两条同类、两条互补、事实有冲突、无案例、案例无有效方法卡、Agent 自动推荐方法卡和完整有效集合；运行 Planner 与策略集成测试，预期只有满足统一门禁的项目可以生成策略，且不会为方法卡额外进入 WAITING_USER。

### 任务 21：一次提交全部结构化阻塞问题

**文件：**

- 修改：`workbench/agent/schemas.py`
- 修改：`workbench/agent/planner.py`
- 修改：`workbench/agent/runner.py`
- 修改：`workbench/templates/agent/question_form.html`
- 修改：`tests/unit/agent/test_schemas.py`
- 修改：`tests/unit/agent/test_planner.py`
- 修改：`tests/e2e/test_agent_flow.py`

**产出：** 一个中断携带当前项目快照中能够检测到的全部阻塞问题，并在 UI 中逐项回答；回答前 Agent 不继续执行，也不把已知问题拆到后续轮次。

- [x] **步骤 21：** 将单问题载荷扩展为问题列表，每项包含稳定 ID、原因、受影响事实和回答类型；Planner 在一次规划中汇总并稳定排序全部已知阻塞问题，Runner 将完整载荷持久化，页面必须展示每个问题与来源。**验证测试：** 覆盖零问题非法、一个问题、四个不同来源的问题全部保留、重复问题合并、稳定排序、刷新后载荷一致和表单逐项校验；运行 schema、Planner 和 Agent E2E，预期全部通过且同一项目快照不会因人为截断产生第二轮已知问题。

### 任务 22：应用用户回答后再恢复 Agent

**文件：**

- 修改：`workbench/api/agent_runs.py`
- 修改：`workbench/materials/service.py`
- 修改：`workbench/facts/service.py`
- 修改：`workbench/references/service.py`
- 修改：`workbench/agent/repository.py`
- 修改：`tests/integration/api/test_agent_runs_api.py`
- 修改：`tests/integration/agent/test_agent_recovery.py`

**产出：** 回答会实际更新素材说明、案例输入、事实或项目决策，验证成功后才清除 WAITING_USER 并重新排队。

- [x] **步骤 22：** 为素材替换或补充、图片文字说明、案例正文或截图说明、模型结构结果人工修订、冲突选择、事实修订、一般补充说明和拒绝事实分别处理回答；只有问题组中的全部必答项验证成功后才能清除 WAITING_USER；拒绝缺项、问题 ID 不匹配和过期 revision，保存用户消息和业务变更后再恢复。**验证测试：** 覆盖多类型问题同批回答、部分回答保持等待、错误问题 ID、项目已被修改、素材补充、图片说明、案例补充、结构结果人工修订、冲突解决、补充后仍不足和重启后再次回答；运行 Agent API 与恢复集成测试，预期状态、素材、案例和事实更新一致。

### 任务 23：更新事实与中断架构记忆

**文件：**

- 修改：`memory-bank/architecture.md`
- 修改：`memory-bank/progress.md`
- 修改：`tests/unit/test_memory_bank_contract.py`

**产出：** 记录事实指纹、自动确认、最低事实集合、问题列表和回答恢复协议。

- [x] **步骤 23：** 更新当前实现的状态转换表和中断恢复顺序，明确任何回答都先持久化业务变更再恢复 Agent。**验证测试：** 扩展文档契约测试，验证上述规则和当前 migration 版本已记录；运行测试，预期通过。

## 里程碑五 策略与稿件编辑

### 任务 24：强制用户主动选择策略

**文件：**

- 修改：`workbench/strategies/service.py`
- 修改：`workbench/agent/tools/strategies.py`
- 修改：`workbench/agent/planner.py`
- 修改：`workbench/templates/strategy/page.html`
- 修改：`workbench/api/strategies.py`
- 修改：`tests/integration/strategies/test_generation.py`
- 修改：`tests/e2e/test_demo_flow.py`

**产出：** 生成策略后只记录推荐项，不自动设置 selected；Agent 等待用户选择后再生成正文。

- [x] **步骤 24：** 将推荐策略 ID 与用户 selected 状态分离，移除无案例继续分支，用户选择时保存语气、篇幅和重点事实设置并提高项目 revision。**验证测试：** 覆盖生成后三项均未选中、推荐项可见、未选择时 Planner 等待、用户选择后继续、重新选择使旧稿过期；运行策略集成与 Demo E2E，预期全部通过。

### 任务 25：强化策略差异与事实引用校验

**文件：**

- 修改：`workbench/strategies/difference.py`
- 修改：`workbench/strategies/service.py`
- 修改：`tests/unit/strategies/test_difference.py`
- 修改：`tests/integration/strategies/test_generation.py`

**产出：** 三策略至少在叙事主角、开头和结构中的两个维度不同，且所有事实 ID 与方法来源有效。

- [x] **步骤 25：** 为策略 Schema 增加叙事主角或等价字段，差异校验按三个维度计数，持久化前验证事实属于当前项目且已确认、方法来自已选案例。**验证测试：** 覆盖三个有效策略、只改名称、只改开头、未知事实、跨项目事实、未选案例方法和两个维度确实不同；运行差异单测与策略集成测试，预期全部通过。

### 任务 26：实现段落级改写与事实锁定

**文件：**

- 修改：`workbench/db/models.py`
- 新建：下一个 Alembic migration
- 修改：`workbench/ai/provider.py`
- 修改：两个 Provider 实现
- 修改：`workbench/drafts/service.py`
- 修改：`workbench/drafts/schemas.py`
- 修改：`workbench/api/drafts.py`
- 修改：`workbench/templates/editor/journal_editor.html`
- 修改：`workbench/static/js/editor.js`
- 新建：`tests/integration/drafts/test_paragraph_rewrite.py`

**产出：** 只改写用户选中的段落，锁定事实或段落不能被模型改变。

- [x] **步骤 26：** 保存段落或事实锁定记录，改写请求只发送选中段落、改写目标和允许引用的事实；应用前比较锁定内容与事实引用，发现变化时拒绝写入并保留原稿。**验证测试：** 覆盖单段改写、其他段落不变、锁定事实保持、模型改变数字或引语被拒绝、过期 revision 被拒绝和失败后原稿不变；运行新集成测试和编辑器自动保存 E2E，预期全部通过。

### 任务 27：实现最近一次 Agent 改写撤销

**文件：**

- 修改：`workbench/drafts/service.py`
- 修改：`workbench/api/drafts.py`
- 修改：`workbench/templates/editor/statusbar.html`
- 修改：`workbench/static/js/editor.js`
- 新建或修改：`tests/integration/drafts/test_undo.py`

**产出：** 只保留最近一次 Agent 局部改写前的快照，并能执行一次撤销；不提供版本列表或任意历史恢复。

- [x] **步骤 27：** 在应用一次成功的 Agent 局部改写前保存可覆盖的单个撤销快照；下一次 Agent 改写以当时的最新稿覆盖该快照；用户在改写后手工编辑标题、大纲或正文时立即使快照失效并禁用撤销；有效撤销恢复正文与事实引用并使质检状态过期，页面不展示历史列表。**验证测试：** 覆盖无快照时禁用撤销、改写后可撤销、改写后人工编辑使撤销失效且人工内容保留、连续改写只保留最近快照、引用同步、质检过期、跨项目不可撤销以及重启后仍可撤销；运行撤销集成测试，预期全部通过。

### 任务 28：更新策略与稿件架构记忆

**文件：**

- 修改：`memory-bank/architecture.md`
- 修改：`memory-bank/progress.md`
- 修改：`tests/unit/test_memory_bank_contract.py`

**产出：** 记录人工策略门禁、策略差异、段落改写、锁定和单步撤销生命周期。

- [x] **步骤 28：** 更新流程图和数据模型，明确推荐不等于选择、只保留最近一次 Agent 改写快照且撤销后质检过期。**验证测试：** 扩展 memory-bank 契约测试，验证人工策略选择、策略差异、局部改写、事实锁定和单步撤销五项规则与当前 migration 版本；运行测试，预期通过。

## 里程碑六 质检与导出

### 任务 29：区分可确认与不可确认的质检问题

**文件：**

- 修改：`workbench/quality/scanner.py`
- 修改：`workbench/quality/service.py`
- 修改：`workbench/api/quality.py`
- 修改：`workbench/db/models.py`
- 新建：下一个 Alembic migration
- 修改：`tests/unit/quality/test_scanner.py`
- 修改：`tests/integration/quality/test_check_failure.py`

**产出：** 问题记录明确 resolution policy，API 不允许把硬阻塞问题直接标为 ACCEPTED。

- [x] **步骤 29：** 将未成年人隐私、联系方式、精确住址、无来源人物身份、无来源引语和事实冲突标为不可仅确认；相似表达、一般语气和非关键低风险项允许用户确认，并记录确认说明。**验证测试：** 覆盖每类风险、硬问题接受请求返回冲突、软问题可接受、修改正文后问题失效和检查服务失败不显示通过；运行质检单元与集成测试，预期全部通过。

### 任务 30：改进相似表达检测

**文件：**

- 修改：`workbench/quality/similarity.py`
- 修改：`workbench/quality/scanner.py`
- 修改：`tests/unit/quality/test_scanner.py`
- 新建：`tests/unit/quality/test_similarity.py`

**产出：** 在不宣称法律结论的前提下识别连续过近表达，并减少短公共短语误报。

- [x] **步骤 30：** 规范化空白和标点，按最小连续长度或稳定片段规则检测参考原文；忽略过短公共表达，只返回风险片段位置和重写建议。**验证测试：** 覆盖完全复制、仅标点变化、短公共短语、结构相似但文字不同、多个案例和中文长句；运行相似度测试和 scanner 测试，预期风险等级和片段定位稳定。

### 任务 31：完成 Markdown 与纯文本导出

**文件：**

- 修改：`workbench/exports/markdown.py`
- 修改：`workbench/exports/plain_text.py`
- 修改：`workbench/api/exports.py`
- 修改：`workbench/templates/quality/export_preview.html`
- 修改：`tests/integration/exports/test_markdown.py`
- 新建：`tests/integration/exports/test_plain_text.py`

**产出：** 单个 Markdown 文件包含正文、创作说明和待确认清单；纯文本默认只包含正文并可选择附加说明。

- [x] **步骤 31：** 导出前重新查询当前稿件和问题状态，过滤内部 block 标记、提示词、参考原文和系统字段；文件名必须安全且目标位于 exports 根目录。**验证测试：** 覆盖正常 Markdown、纯文本、选择附录、未确认清单、中文文件名、路径穿越、内部标记泄漏和参考原文泄漏；运行两个导出集成测试，预期全部通过且输出只位于测试临时目录。

### 任务 32：实施最终导出硬门禁

**文件：**

- 修改：`workbench/exports/markdown.py`
- 修改：`workbench/api/exports.py`
- 修改：`tests/integration/exports/test_markdown.py`
- 修改：`tests/e2e/test_demo_flow.py`

**产出：** 只有检查完成且所有不可确认问题已解决时才允许导出。

- [x] **步骤 32：** 把检查未完成、检查失败、事实冲突、隐私硬风险和无来源身份或引语设为不可绕过；软问题只有在记录用户确认后可放行。**验证测试：** 为每种阻塞状态建立导出用例，并在 E2E 中验证修复硬问题、确认软问题后按钮才可用；运行导出集成与 Demo E2E，预期全部通过。

### 任务 33：更新质检与导出架构记忆

**文件：**

- 修改：`memory-bank/architecture.md`
- 修改：`memory-bank/progress.md`
- 修改：`tests/unit/test_memory_bank_contract.py`

**产出：** 记录问题分类、处置状态、导出组成和硬门禁。

- [x] **步骤 33：** 更新质检状态机和导出数据流，只记录已实现并通过测试的规则。**验证测试：** 扩展文档契约测试，验证硬风险清单、软风险确认、Markdown 附录和纯文本默认行为；运行测试，预期通过。

## 里程碑七 UI 可观测性与开源交付

### 任务 34：对齐七个工作区导航与前置条件

**文件：**

- 修改：`workbench/templates/components/dock.html`
- 修改：`workbench/web/project_navigation.py`
- 修改：各工作区页面模板
- 修改：`workbench/static/css/app.css`
- 修改：`tests/unit/web/test_project_navigation.py`
- 修改：`tests/unit/web/test_retro_shell.py`
- 修改：`tests/e2e/test_responsive.py`

**产出：** 我的桌面、活动文件、事实确认、灵感收藏、编辑提案、推文日志和发布检查七个入口，未满足条件时可查看但主操作禁用并说明原因。

- [x] **步骤 34：** 统一导航状态、完成角标、异常角标和前置条件文案；保持 1440×900 与 1280×800 的固定复古窗口布局，低于 1100 像素显示桌面端提示。**验证测试：** 更新导航单测覆盖七入口与每个门禁，更新响应式 E2E 覆盖两种目标尺寸和窄屏提示；运行相关单测与响应式 E2E，预期全部通过且无核心控件遮挡。

### 任务 35：统一 Agent 进度轮询与刷新恢复

**文件：**

- 修改：`workbench/templates/agent/status_panel.html`
- 修改：`workbench/templates/agent/timeline.html`
- 修改：`workbench/static/js/agent.js`
- 修改：`workbench/api/agent_runs.py`
- 修改：`tests/e2e/test_agent_flow.py`
- 修改：`tests/e2e/test_failure_recovery.py`

**产出：** 1 至 2 秒轮询、终态停止、刷新恢复、WAITING_USER 稳定展示和失败重试。

- [x] **步骤 35：** 让页面只以数据库状态为准，显示当前阶段、工具步骤、耗时、错误码和下一动作；轮询在 COMPLETED、FAILED、PARTIAL、CANCELLED 或 WAITING_USER 时停止，用户操作后再恢复。**验证测试：** 覆盖运行中刷新、等待用户刷新、失败后重试、终态不再请求和应用重启恢复；运行两个 Agent E2E，预期无重复执行和状态倒退。

### 任务 36：完善结构化日志与敏感信息过滤

**文件：**

- 新建：`workbench/logging.py`
- 修改：`workbench/main.py`
- 修改：`workbench/agent/runner.py`
- 修改：真实 Provider transport
- 新建：`tests/unit/test_logging_redaction.py`

**产出：** 包含 request、project、run、step、tool、duration、status 和 error code 的结构化日志，且不包含敏感正文和密钥。

- [x] **步骤 36：** 为请求和 Agent 步骤添加关联标识，集中清洗 Authorization、API Key、完整提示词、案例原文和上传正文；用户可见轨迹继续来自数据库，不暴露服务器日志。**验证测试：** 使用包含假密钥、手机号、参考原文和异常堆栈的日志事件，验证敏感值被替换而必要标识保留；运行日志脱敏单测，预期全部通过。

### 任务 37：完成仓库安全与忽略规则

**文件：**

- 修改：`.gitignore`
- 修改：`.dockerignore`
- 修改：`workbench/storage/local.py`
- 修改：`tests/unit/storage/test_local_storage.py`
- 修改：`tests/unit/test_runtime_paths.py`

**产出：** 运行数据不会进入 Git，所有文件操作都限制在项目目录，删除行为可验证。

- [x] **步骤 37：** 覆盖 `.env`、数据库、上传、导出、缓存、浏览器数据、日志和测试产物；集中执行路径解析和边界校验，拒绝符号链接或解析后越界目标。**验证测试：** 覆盖正常读写、父目录穿越、绝对路径、符号链接越界、项目删除和 Git 忽略清单；运行 storage 与 runtime path 单测，预期全部通过。

### 任务 38：建立 GitHub Actions 最小 CI

**文件：**

- 新建：`.github/workflows/ci.yml`
- 修改：`scripts/test.ps1` 或增加跨平台等价入口
- 修改：`README.md`
- 新建：`tests/unit/test_ci_contract.py`

**产出：** 在无真实密钥条件下，于 Windows、macOS、Linux 验证安装、路径、启动、迁移和单元集成测试，并在 Linux 执行 Ruff、关键 E2E 和密钥扫描的 CI。

- [x] **步骤 38：** 配置 `ubuntu-latest`、`windows-latest`、`macos-latest` 三系统矩阵，使用受支持 Python 版本、锁定依赖缓存、Mock Provider 和各系统临时数据目录运行安装、启动、迁移及单元集成测试；只在 Ubuntu 作业运行 Ruff、无头 Playwright 关键 E2E 和密钥扫描；真实模型测试默认跳过，README 明确本地与 CI 命令。**验证测试：** 新增 CI 契约测试检查三系统 runner、跨平台临时路径、迁移、lint、测试、E2E 和密钥扫描均存在且不包含真实密钥或写死 D 盘路径；本地运行该测试和 CI 使用的全部可本地执行命令，预期通过。

### 任务 39：完成开源文档和示例数据

**文件：**

- 修改：`README.md`
- 修改：`.env.example`
- 新建或修改：`data/samples/` 下脱敏样例
- 修改：`docs/demo-script.md`
- 修改：`docs/acceptance-record.md`
- 新建：`tests/integration/test_sample_data.py`

**产出：** 克隆仓库后无需密钥可载入示例任务，有密钥可切换真实 Provider，README 说明限制、安全和演示流程。

- [x] **步骤 39：** 补充最短启动路径、架构图、Agent 能力说明、Provider 配置、数据目录、隐私声明、已知限制和六至八分钟面试脚本；样例必须含人为时间冲突、低置信度输入和过近表达。**验证测试：** 新增样例数据集成测试，验证样例可载入、冲突会暂停、参考内容不进入事实库、最终可导出；运行该测试，预期完整 Mock 流程通过。

### 任务 40：执行最终验收并更新架构记忆

**文件：**

- 修改：`memory-bank/architecture.md`
- 修改：`memory-bank/progress.md`
- 修改：`docs/acceptance-record.md`
- 修改：`tests/e2e/test_demo_flow.py`
- 修改：`tests/e2e/test_agent_flow.py`

**产出：** 设计文档中的产品、Agent、UI、隐私和开源要求均有测试证据。

- [x] **步骤 40：** 使用固定脱敏样例执行创建项目、上传素材、事实自动通过、冲突中断、回答恢复、案例拆解、三策略人工选择、正文生成、局部改写、事实锁定、质检和导出；将实际通过的架构和限制写入 memory-bank，不记录未完成能力。**验证测试：** 依次运行 `scripts/test.ps1 -q` 和 `scripts/e2e.ps1 -q`，预期零失败；随后运行一次 Mock 面试演示并把命令、测试数量、关键截图位置和已知限制记录到 `docs/acceptance-record.md`。

## 任务完成规则

- 每个任务开始前重新阅读该任务依赖的 memory-bank 章节和前一任务的产出。
- 每个任务只改动列出的文件；发现必须扩大范围时先更新计划并说明原因。
- 每个任务先增加或修改测试，使测试能证明旧行为不满足要求，再实施最小变更使测试通过。
- 任务级测试未通过时不得进入下一任务，不得用跳过、降低断言或删除测试的方式放行。
- 每个里程碑结束时运行该里程碑涉及的所有单元与集成测试，并更新 `memory-bank/architecture.md` 与 `memory-bank/progress.md`。
- 任何涉及 Agent 路由、数据库结构、恢复、页面主流程或导出的变更，都必须运行对应 E2E。
- 提交信息只描述当前任务；不得把多个未独立验证的任务合并为一个提交。

## 实施顺序与并行限制

- 任务 1 至 5 必须顺序执行，其他开发不得绕过运行基线和 memory-bank。
- 任务 6 至 12 必须顺序执行，因为后续 Provider 方法依赖统一 transport 和错误模型。
- 任务 13 与 15 可以在不同分支并行，但任务 16 必须等待二者完成。
- 任务 18 至 23 必须顺序执行，避免事实状态、Planner 和中断协议出现不一致。
- 任务 24 与任务 25 可连续实施；任务 26 和任务 27 依赖人工策略门禁完成。
- 任务 29 至 33 必须顺序执行，导出不得早于问题处置策略完成。
- 任务 34 至 39 可以按文件冲突情况分组实施，但任务 40 必须等待全部任务完成。

## 计划自检结果

- 设计文档中的产品范围、Agent 状态、素材、事实、案例、策略、正文、质检、导出、UI、安全、测试和开源要求均有对应任务。
- 技术栈文档中的 Python 单体、Jinja2/HTMX、自定义 Agent、SQLite、HTTPX、Mock Provider、单 worker、轮询、D 盘和禁止组件均已转化为实施约束。
- 每个编号步骤都包含明确文件、单一主要交付物、验证测试、运行命令和通过条件。
- 计划没有包含任何实现代码，也没有要求执行者重写现有可用系统。
- 五个重点风险均在拥有相关实现的任务中配置了直接测试。
