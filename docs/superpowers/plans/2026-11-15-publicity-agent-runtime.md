# Publicity Agent Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有固定点击式宣传创作 Demo 重构为可暂停、恢复、追踪和自动完成内容生产的单 Agent 工作台。

**Architecture:** 保留 FastAPI、Jinja/HTMX、SQLAlchemy/SQLite、现有业务 Service 与复古 UI；新增持久化 AgentRun/AgentStep/AgentMessage、ProjectSnapshot、状态策略 Planner、白名单 Tool Registry 和进程内 Runner。Mock Provider 继续承担模型推理模拟，Runtime 的状态读取、工具选择、输入指纹、暂停恢复和错误处理为真实实现。

**Tech Stack:** Python 3.9、FastAPI、Jinja2/HTMX、SQLAlchemy 2、Alembic、SQLite、Pydantic、pytest、Playwright/Edge。

**Spec:** `docs/superpowers/specs/2026-11-15-publicity-agent-runtime-design.md`

## Global Constraints

- 所有源码、依赖、缓存、数据库、上传、导出、日志、截图和测试产物必须位于 `D:\aipm\demo`。
- 只通过 `scripts/setup.ps1`、`scripts/test.ps1`、`scripts/e2e.ps1`、`scripts/dev.ps1` 运行项目命令，不裸跑 pip/pytest/uvicorn。
- 单 Run 最多 12 次工具调用；Provider 结构错误最多自动重试 1 次；正文最多自动修订 1 次。
- Agent 只调用六个注册工具，不能执行 SQL、Shell、任意网络请求或直接操作数据库。
- ReferenceCase 不得进入 FactCard；策略与正文只使用已确认且有来源的活动事实。
- 首版仅交付 Mock Provider、Provider Factory、真实 API 接口契约和接入文档，不发起真实模型网络请求。
- 用户人工修改优先于 Agent 旧结果；Run 日志不得保存素材全文、参考原文、提示词、密钥或隐藏推理。
- 六个现有页面保留为产物工作区；“开始自主创作”是主流程唯一主 CTA。

## Review Focus

- 同一项目重复点击启动：只创建一个活动 Run，第二次返回现有 Run 而不是并发执行。（Task 3 集成测试）
- 工具执行期间用户修改事实/策略/正文：旧结果不能覆盖新 revision，Runner 必须重新规划。（Task 3 集成测试）
- 所有参考资料解析失败：Run 进入等待确认，用户允许后可按通用方法继续且不产生参考事实。（Task 2、4 测试）
- 自动修订后仍有事实类阻断问题：Run 不得完成或导出，必须等待用户或部分完成。（Task 4 测试）
- 服务重启时同时存在 RUNNING、PAUSED、WAITING_USER：只恢复 RUNNING，其他状态保持不变。（Task 3 恢复测试）

---

### Task 1: Agent 数据模型、状态与迁移

**Files:**
- Modify: `workbench/domain/enums.py`
- Modify: `workbench/db/models.py`
- Create: `workbench/agent/__init__.py`
- Create: `workbench/agent/schemas.py`
- Create: `workbench/agent/repository.py`
- Create: `alembic/versions/0003_agent_runtime.py`
- Test: `tests/unit/agent/test_schemas.py`
- Test: `tests/integration/agent/test_repository.py`

**Interfaces:**
- Consumes: `workbench.db.models.Project`, SQLAlchemy `Session`。
- Produces: `AgentRunStatus`, `AgentStepStatus`, `AgentMessageType`; ORM `AgentRun`, `AgentStep`, `AgentMessage`; Pydantic `AgentRunRead`, `AgentStepRead`, `AgentQuestion`, `AgentAnswer`; repository functions `create_run(session, project_id, goal) -> AgentRun`, `get_active_run(session, project_id) -> AgentRun | None`, `append_message(...)`, `list_steps(session, run_id)`。

- [ ] **Step 1: 写失败的状态与 Schema 单测**

  覆盖 `QUEUED/RUNNING/PAUSED/WAITING_USER/COMPLETED/PARTIAL/FAILED/CANCELLED`、结构化问题与回答、`max_tool_calls=12`、`max_revisions=1`。

- [ ] **Step 2: 写失败的 repository 集成测试**

  断言同项目只有一个活动 Run；Step sequence 唯一；Message 不接受隐藏推理类型；项目删除级联删除 Agent 记录。

- [ ] **Step 3: 运行聚焦测试并确认失败**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1 tests/unit/agent/test_schemas.py tests/integration/agent/test_repository.py`

  Expected: FAIL，Agent 模块和表尚不存在。

- [ ] **Step 4: 实现枚举、ORM 与 Pydantic Schema**

  `Project` 新增 `goal: str`、`decisions: dict`、`revision: int`；`Draft` 新增 `revision: int` 与 `quality_status: str`；Agent 表字段严格采用设计文档第 5 节名称。

- [ ] **Step 5: 实现 repository 和 Alembic 迁移**

  活动 Run 唯一性同时由 repository 事务检查和可索引状态约束保证；迁移为现有行提供安全默认值。

- [ ] **Step 6: 运行聚焦测试并确认通过**

  Expected: PASS，迁移 head 为 `0003_agent_runtime`，数据库仍只位于 `storage/` 或测试专用 `.runtime/`。

- [ ] **Step 7: 提交**

  Commit: `feat: add persistent agent runtime model`

### Task 2: ProjectSnapshot、Planner 与工具注册表

**Files:**
- Create: `workbench/agent/snapshot.py`
- Create: `workbench/agent/planner.py`
- Create: `workbench/agent/tools/base.py`
- Create: `workbench/agent/tools/registry.py`
- Create: `workbench/agent/fingerprints.py`
- Test: `tests/unit/agent/test_planner.py`
- Test: `tests/unit/agent/test_registry.py`
- Test: `tests/unit/agent/test_fingerprints.py`

**Interfaces:**
- Consumes: Project、Material、FactCard、ReferenceCase、Strategy、Draft、QualityIssue 和 AgentRun ORM 状态。
- Produces: `build_project_snapshot(session, project_id) -> ProjectSnapshot`; `decide_next(snapshot, run) -> AgentDecision`; `AgentTool` Protocol; `ToolRegistry.register(tool)`, `ToolRegistry.get(name)`; `fingerprint_for(tool_name, payload) -> str`。

- [ ] **Step 1: 写失败的 Planner 决策表测试**

  分别断言待解析资料→`parse_materials`、无事实→`validate_facts`、关键冲突→`ASK_USER`、无参考→询问、已允许无参考→`plan_strategies`、无推荐策略→策略工具、无正文→内容工具、无检查→质检工具、产物完整→`COMPLETE`。

- [ ] **Step 2: 写自动确认与最小事实门槛测试**

  有 SourceChunk、无冲突、非身份猜测且达阈值的事实可进入 eligible 集；精确时间/数字冲突、无来源、参考案例内容不能进入；策略至少需要一个时间/场景事实和三个其他事实。

- [ ] **Step 3: 写 Registry 和指纹测试**

  未注册工具抛 `UnknownAgentToolError`；同语义输入不同 dict 顺序产生相同 SHA-256；事实 revision 或策略覆盖变化必须改变下游指纹。

- [ ] **Step 4: 运行聚焦测试并确认失败**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1 tests/unit/agent/test_planner.py tests/unit/agent/test_registry.py tests/unit/agent/test_fingerprints.py`

- [ ] **Step 5: 实现 Snapshot、Planner、Registry 与稳定指纹**

  Planner 只返回结构化 `AgentDecision(action, tool_name, reason_summary, expected_artifacts, question)`，不得执行工具或保存业务数据。

- [ ] **Step 6: 运行聚焦测试并确认通过**

  Expected: PASS；Planner 在不同项目状态下选择不同动作，不依赖固定页面顺序。

- [ ] **Step 7: 提交**

  Commit: `feat: add state driven agent planner`

### Task 3: Agent Runner、恢复与运行 API

**Files:**
- Create: `workbench/agent/runner.py`
- Create: `workbench/agent/recovery.py`
- Create: `workbench/api/agent_runs.py`
- Modify: `workbench/main.py`
- Modify: `workbench/web/dependencies.py`
- Test: `tests/integration/agent/test_runner.py`
- Test: `tests/integration/agent/test_recovery.py`
- Test: `tests/integration/api/test_agent_runs_api.py`

**Interfaces:**
- Consumes: Task 1 repository、Task 2 Planner/Registry、FastAPI app session factory。
- Produces: `AgentRunner.run(run_id)`, `AgentRunner.request_pause(run_id)`, `AgentRunner.request_cancel(run_id)`, `recover_agent_runs(session) -> list[str]`; REST endpoints from spec section 10。

- [ ] **Step 1: 写失败的 Runner 生命周期测试**

  使用记录型假工具断言 Runner 每轮重建 Snapshot、连续调用至少两个不同工具、达到 12 次进入 PARTIAL、取消在工具边界生效、PAUSED/WAITING_USER 不继续运行。

- [ ] **Step 2: 写并发与 revision 竞争测试**

  同项目重复启动返回已有活动 Run；工具开始后用户增加 revision，旧输出不提交且重新规划；成功的相同指纹 Step 在恢复时跳过。

- [ ] **Step 3: 写恢复测试**

  应用重启仅把 RUNNING 改为 QUEUED 并调度；PAUSED、WAITING_USER 保持；超限 Run 的 retry 创建新预算并复用有效 Step。

- [ ] **Step 4: 写 API 合约测试**

  覆盖启动、查询、步骤列表、回答、暂停、恢复、取消、重试及统一 `{data,error,requestId}`；非法状态转换返回 409。

- [ ] **Step 5: 运行聚焦测试并确认失败**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1 tests/integration/agent tests/integration/api/test_agent_runs_api.py`

- [ ] **Step 6: 实现 Runner、恢复和 API**

  使用现有进程内执行方式，不引入队列依赖；每个工具事务完成后更新 Step；Runner 日志只保存摘要和结果引用。

- [ ] **Step 7: 接入 FastAPI lifespan 与 router**

  启动时恢复遗留 Run；后台任务引用 app 内 session factory 和 registry；异常必须落库为可操作错误码。

- [ ] **Step 8: 运行聚焦测试并确认通过**

  Expected: PASS；不存在并发重复 Run，重启恢复不会重做成功步骤。

- [ ] **Step 9: 提交**

  Commit: `feat: run and recover autonomous agent tasks`

### Task 4: 六工具适配、自动推荐与一次修订

**Files:**
- Create: `workbench/agent/tools/materials.py`
- Create: `workbench/agent/tools/facts.py`
- Create: `workbench/agent/tools/references.py`
- Create: `workbench/agent/tools/strategies.py`
- Create: `workbench/agent/tools/content.py`
- Create: `workbench/agent/tools/quality.py`
- Modify: `workbench/facts/extractor.py`
- Modify: `workbench/facts/service.py`
- Modify: `workbench/strategies/service.py`
- Modify: `workbench/drafts/service.py`
- Modify: `workbench/quality/service.py`
- Modify: `workbench/ai/schemas/strategy.py`
- Modify: `workbench/ai/schemas/draft.py`
- Modify: `workbench/ai/schemas/quality.py`
- Modify: `workbench/ai/mock_provider.py`
- Test: `tests/integration/agent/test_tools.py`
- Test: `tests/integration/agent/test_autonomous_flow.py`

**Interfaces:**
- Consumes: Task 2 `AgentTool`、现有六类 Service、`AIProvider`。
- Produces: 六个具名工具 `parse_materials`, `validate_facts`, `analyze_references`, `plan_strategies`, `generate_content`, `check_quality`; `build_default_registry(...) -> ToolRegistry`。

- [ ] **Step 1: 写失败的工具 Schema 与数据隔离测试**

  每个工具输入输出均由 Pydantic 校验；参考工具不创建 FactCard；策略/正文 Provider 输入不含 ReferenceCase.raw_text；正文引用只指向 eligible facts。

- [ ] **Step 2: 写失败的自动推荐测试**

  三策略差异校验通过后保存 `recommended_id` 并默认选中；生成五个标题并默认采用 Provider 推荐标题；用户覆盖策略优先且使下游 STALE。

- [ ] **Step 3: 写失败的一次自动修订和门禁测试**

  只有可自动修复的表达问题触发 `mode=revision`；最多一次；修订后重新检查；事实冲突、无来源关键事实、失效引用和检查失败均阻止 COMPLETED/导出；非事实高风险可经最终审核确认。

- [ ] **Step 4: 写无参考降级测试**

  无参考或全部失败时先 WAITING_USER；保存 `allow_without_references` 后策略使用通用方法，且不能新增活动事实。

- [ ] **Step 5: 运行聚焦测试并确认失败**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1 tests/integration/agent/test_tools.py tests/integration/agent/test_autonomous_flow.py`

- [ ] **Step 6: 实现六个薄工具适配器**

  工具负责 Schema、Service 调用、摘要和结果引用；业务逻辑继续留在对应 Service，禁止工具直接拼 SQL。

- [ ] **Step 7: 扩展 Mock Provider 和业务 Service**

  Provider Schema 增加推荐 ID、推荐标题、`auto_fixable`；Mock 输出确定、标记 `is_demo=true`；自动确认规则和质量门禁按设计实现。

- [ ] **Step 8: 注册默认工具并运行聚焦测试**

  Expected: PASS；从已准备素材的项目只启动一次 Run 即自动得到策略、标题、大纲、正文和质检结果。

- [ ] **Step 9: 提交**

  Commit: `feat: expose creation services as agent tools`

### Task 5: Agent 工作台 UI 与六页去固定流程化

**Files:**
- Create: `workbench/templates/agent/workspace.html`
- Create: `workbench/templates/agent/status_panel.html`
- Create: `workbench/templates/agent/timeline.html`
- Create: `workbench/templates/agent/question_form.html`
- Create: `workbench/static/css/agent.css`
- Create: `workbench/static/js/agent.js`
- Modify: `workbench/templates/base.html`
- Modify: `workbench/templates/projects/index.html`
- Modify: `workbench/templates/inspiration/page.html`
- Modify: `workbench/templates/strategy/page.html`
- Modify: `workbench/templates/editor/page.html`
- Modify: `workbench/templates/quality/page.html`
- Modify: `workbench/static/js/app.js`
- Modify: `workbench/web/page_routes.py`
- Test: `tests/unit/web/test_agent_workspace.py`
- Test: `tests/e2e/test_agent_flow.py`

**Interfaces:**
- Consumes: Task 3 Agent API、现有页面路由和产品 Service 查询。
- Produces: 项目 Agent 工作区、1.5 秒轮询、暂停/恢复/取消/回答 UI、六阶段时间线及人工覆盖入口。

- [ ] **Step 1: 写失败的工作台渲染测试**

  断言目标/受众/语气/篇幅、唯一粉色“开始自主创作”CTA、当前计划、六阶段状态、工具摘要、Demo 标识、问题表单和失败提示存在；不包含隐藏推理字段。

- [ ] **Step 2: 写失败的页面去固定流程测试**

  灵感页不再用“生成策略”作为主流程按钮；策略页显示 Agent 推荐和可覆盖；编辑页不要求先点标题/大纲按钮；检查页展示自动修订次数和最终审核门禁。

- [ ] **Step 3: 写失败的浏览器主链路测试**

  从首页准备好的无冲突 Demo 只点击一次开始，轮询直至完成，期间不点击六工具按钮；数据库时间线和 UI 工具步骤一致；刷新页面仍显示当前 Run。

- [ ] **Step 4: 运行聚焦测试并确认失败**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1 tests/unit/web/test_agent_workspace.py`

- [ ] **Step 5: 实现工作台模板、CSS 和前端轮询**

  所有 DOM 状态使用 API 返回摘要；问题回答和控制按钮有禁用、错误、键盘焦点和 reduced-motion 行为。

- [ ] **Step 6: 改造六页为产物工作区**

  删除主流程串联按钮及其 `app.js` 处理器；人工重跑/覆盖作为次级动作，并显示会失效的下游产物。

- [ ] **Step 7: 运行单元与 E2E 聚焦测试**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1 tests/e2e/test_agent_flow.py`

  Expected: PASS；1440×900 和 1280×800 可用，页面无横向溢出。

- [ ] **Step 8: 提交**

  Commit: `feat: add autonomous agent workspace`

### Task 6: Provider Factory、API 接入说明与最终验收

**Files:**
- Create: `workbench/ai/factory.py`
- Modify: `workbench/settings.py`
- Modify: `workbench/main.py`
- Modify: `.env.example`
- Modify: `README.md`
- Modify: `docs/demo-script.md`
- Modify: `docs/acceptance-record.md`
- Test: `tests/unit/ai/test_provider_factory.py`
- Modify: `tests/e2e/test_failure_recovery.py`
- Modify: `tests/e2e/test_responsive.py`
- Modify: `tests/e2e/test_demo_flow.py`

**Interfaces:**
- Consumes: `AIProvider`, `MockAIProvider`, Settings。
- Produces: `create_ai_provider(settings) -> AIProvider`; `AI_PROVIDER=mock` 默认配置；真实兼容 API 接入教程和明确的未实现错误。

- [ ] **Step 1: 写失败的 Provider Factory 测试**

  `mock` 返回 MockAIProvider；`openai_compatible` 在本轮返回明确 `ProviderNotInstalledError`；未知值拒绝启动；错误信息不包含 API key。

- [ ] **Step 2: 运行聚焦测试并确认失败**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1 tests/unit/ai/test_provider_factory.py`

- [ ] **Step 3: 实现 Factory 和项目内配置**

  Settings 只从环境读取 provider/base URL/model/key；日志和 repr 屏蔽 key；默认永不访问网络。

- [ ] **Step 4: 编写真实 API 接入教程**

  README 说明兼容 Provider 需实现的五个方法、JSON Schema、超时、一次重试、错误码、密钥配置与最小连通性测试；明确当前版本未内置网络 Provider。

- [ ] **Step 5: 更新 Demo 种子、脚本和端到端验收**

  提供无冲突快速项目和关键事实冲突项目；演示脚本改为一次启动 Agent、冲突确认、最终审核与导出。

- [ ] **Step 6: 运行完整单元/集成测试**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1`

  Expected: 全部 PASS，Alembic 为 head，没有网络请求。

- [ ] **Step 7: 连续运行三次 E2E**

  Run: `powershell -ExecutionPolicy Bypass -File .\scripts\e2e.ps1`（连续三次）

  Expected: 每次全部 PASS；产物只在 `.runtime/`、`storage/`、`exports/`、`test-results/`。

- [ ] **Step 8: 检查工作区边界和文档验收记录**

  确认项目脚本没有 C 盘运行时写入配置；记录测试数量、两种视口、恢复/冲突/超限结果和已知限制。

- [ ] **Step 9: 提交**

  Commit: `docs: complete autonomous agent demo delivery`

## Self-Review Record

- **Spec coverage:** Tasks 1–6 覆盖持久化状态、Planner、六工具、Runner/API、自动推荐、一次修订、工作台、暂停恢复、Provider 边界、D 盘约束和全部验收；没有遗漏设计章节。
- **Step scan:** 每个任务有独立失败测试、最小实现、聚焦验证和提交；没有把实现正文抄进计划。
- **Type consistency:** `ProjectSnapshot → AgentDecision → ToolRegistry → AgentRunner` 接口在 Task 2–4 一致；Provider Factory 只返回现有 `AIProvider`。
- **Review Focus:** 并发启动、revision 竞争、无参考降级、修订后阻断和重启多状态均已绑定具体测试。
- **Proportion:** 六个任务分别形成可独立审查的交付，不拆成无验收价值的脚手架任务。

