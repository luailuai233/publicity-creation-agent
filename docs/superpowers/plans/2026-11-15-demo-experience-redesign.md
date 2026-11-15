# Agent Demo 双模式体验改版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 Agent Demo 改造成可一键自主运行、也可逐模块实际演示的清晰双模式产品体验。

**Architecture:** 保留现有 FastAPI、SQLAlchemy、Jinja、原生 JavaScript 和六工具 Agent 核心，在 Project 层补齐可编辑创作简报，在 Web 层新增统一导航展示模型。手动演示动作继续调用已有 API/Service，并以活动 Agent Run 作为单写者锁；两条路线共享数据库状态和失效规则。

**Tech Stack:** Python 3.9、FastAPI、SQLAlchemy、Pydantic、Jinja2、原生 JavaScript/CSS、Pytest、Playwright

**Spec:** `docs/superpowers/specs/2026-11-15-demo-experience-redesign.md`

## Global Constraints

- 所有源码、依赖、缓存、数据库、上传、导出、日志、截图和测试产物必须位于 `D:\aipm\demo`。
- 默认继续使用明确标识的 Mock Provider，不接真实模型网络 API。
- 事实与参考案例保持隔离；事实来源或冲突阻断不得绕过。
- 同一项目同一时间只有一个写入者；活动 Agent 运行期间页面可读但手动写操作锁定。
- 每页最多一个主按钮；无前置数据时提供准备入口，不提供死链接。
- 每个任务使用 TDD，聚焦测试通过后提交一次独立 commit。

## Review Focus

- `length_min > length_max` 或超出 200–10000：Project PATCH 返回可理解的 422，旧设置不被部分写入。（Task 1 API 测试）
- Agent 已 `RUNNING` 时从模块页触发生成/修改：UI 和后端写端点都拒绝竞争写入，页面仍可查看。（Task 2/4 集成测试）
- 项目没有素材、参考、策略或草稿时直接打开任一模块：页面返回 200 并给出正确准备入口。（Task 2/4 页面测试）
- 修改素材/参考/标题后：Project revision 递增，质量状态变为 STALE，人工标题和正文不被后台覆盖。（Task 1/4 集成测试）
- 连续重新生成策略且历史草稿引用旧策略：当前页面只展示新三条，历史稿仍可读取且外键完整。（Task 4 集成测试）

---

### Task 1: 可编辑创作简报与上游失效

**Files:**
- Modify: `workbench/domain/project_schemas.py`
- Modify: `workbench/db/projects.py`
- Modify: `workbench/api/projects.py`
- Modify: `workbench/references/service.py`
- Modify: `workbench/api/references.py`
- Modify: `workbench/materials/service.py`
- Modify: `workbench/api/materials.py`
- Test: `tests/integration/api/test_projects_api.py`
- Test: `tests/integration/test_review_regressions.py`

**Interfaces:**
- Produces: `ProjectPatch(goal: Optional[str], audience: Optional[str], tone: Optional[str], length_min: Optional[int], length_max: Optional[int])`
- Produces: `update_project(session: Session, project_id: str, patch: ProjectPatch) -> Project`
- Produces: `PATCH /api/projects/{project_id}` using the existing `{data,error,requestId}` envelope.
- Produces: upstream material/reference mutations increment `Project.revision` and call existing downstream invalidation.

- [ ] **Step 1: Write failing Project PATCH tests** — assert all four visible settings persist, blank audience/tone and inverted/out-of-range lengths fail atomically, and a successful change increments revision.
- [ ] **Step 2: Run `scripts/test.ps1 tests/integration/api/test_projects_api.py -q`** — expect new tests to fail because PATCH is absent.
- [ ] **Step 3: Implement `ProjectPatch`, `update_project`, and PATCH route** — validate the merged old/new length pair before assigning any field; mark current draft quality stale when the brief changes.
- [ ] **Step 4: Write failing upstream invalidation tests** — create/patch/delete a reference and create/patch/delete material, then assert revision increments and current quality becomes `STALE`.
- [ ] **Step 5: Run `scripts/test.ps1 tests/integration/test_review_regressions.py -q`** — expect the new invalidation cases to fail.
- [ ] **Step 6: Route reference/material mutations through shared revision invalidation** — keep read and analysis-only operations unchanged.
- [ ] **Step 7: Run both focused test files** — expect all PASS.
- [ ] **Step 8: Commit** — `git commit -m "feat: make creation brief editable"`.

### Task 2: 项目感知导航、模块状态与单写者锁

**Files:**
- Create: `workbench/web/project_navigation.py`
- Modify: `workbench/templates/components/dock.html`
- Modify: `workbench/static/css/app.css`
- Modify: `workbench/web/page_routes.py`
- Modify: `workbench/web/material_routes.py`
- Modify: `workbench/web/inspiration_routes.py`
- Modify: `workbench/web/strategy_routes.py`
- Modify: `workbench/web/editor_routes.py`
- Modify: `workbench/web/export_routes.py`
- Modify: `workbench/templates/projects/demo_button.html`
- Modify: `workbench/templates/components/topbar.html`
- Test: `tests/unit/web/test_project_navigation.py`
- Test: `tests/unit/web/test_agent_workspace.py`

**Interfaces:**
- Consumes: `build_project_snapshot(session, project_id) -> ProjectSnapshot`.
- Produces: `build_project_navigation(session: Session, project_id: str, current_path: str) -> ProjectNavigation`.
- `ProjectNavigation` exposes six `items` with `label`, `href`, `status`, `is_active`, plus `manual_writes_locked: bool` and `lock_message: str`.

- [ ] **Step 1: Write failing navigation model tests** — assert six real project URLs, correct active item, status transitions for empty/partial/complete data, and write lock only for `QUEUED/RUNNING`.
- [ ] **Step 2: Run `scripts/test.ps1 tests/unit/web/test_project_navigation.py -q`** — expect import failure.
- [ ] **Step 3: Implement `project_navigation.py`** — derive presentation state from snapshot plus latest active Run; do not use `Project.status`.
- [ ] **Step 4: Write failing rendered-navigation tests** — every module page returns clickable project links, current page is highlighted, direct empty-state visits return 200, and topbar lacks “所有数据保存在 D 盘”.
- [ ] **Step 5: Run the rendered tests** — expect disabled `#` links and old copy to fail.
- [ ] **Step 6: Pass navigation context from all six page routes and render it in `dock.html`** — remove `aria-disabled` and pointer-event disabling; show status badge and lock message.
- [ ] **Step 7: Change Demo reset destination to `/project/{id}/agent` and remove the topbar D-drive text**.
- [ ] **Step 8: Run Task 2 focused tests** — expect all PASS.
- [ ] **Step 9: Commit** — `git commit -m "feat: add project-aware demo navigation"`.

### Task 3: 重构 Agent 首页与状态控制

**Files:**
- Modify: `workbench/templates/agent/workspace.html`
- Modify: `workbench/templates/agent/status_panel.html`
- Modify: `workbench/templates/agent/timeline.html`
- Modify: `workbench/static/css/agent.css`
- Modify: `workbench/static/js/agent.js`
- Modify: `workbench/web/page_routes.py`
- Test: `tests/unit/web/test_agent_workspace.py`
- Test: `tests/integration/api/test_agent_runs_api.py`

**Interfaces:**
- Consumes: Task 1 Project PATCH and Task 2 `ProjectNavigation`.
- Produces: one form containing `goal`, `audience`, `tone`, `length_min`, `length_max`; submit PATCHes the Project, then POSTs `/api/projects/{id}/agent-runs`.
- Produces: status-specific view model for `READY`, active, `WAITING_USER`, terminal success, and terminal failure/partial states.

- [ ] **Step 1: Extend failing workspace tests** — assert editable fields with persisted values; no six static cards; READY has no pause/resume/cancel; dual entrances are visible; active/paused/waiting/completed states expose only valid controls and result links.
- [ ] **Step 2: Run `scripts/test.ps1 tests/unit/web/test_agent_workspace.py -q`** — expect static settings/cards/controls to fail.
- [ ] **Step 3: Rebuild the workspace/status templates and CSS** — replace static plan cards with creation brief, concise state summary, and collapsible run record; keep one primary action.
- [ ] **Step 4: Update `agent.js` submit sequence** — validate length pair client-side, PATCH project, POST run, show field/API errors, and prevent duplicate submission.
- [ ] **Step 5: Add API integration case** — changed goal/settings must be visible to the generated strategy/draft after one start.
- [ ] **Step 6: Run workspace and Agent API tests** — expect all PASS.
- [ ] **Step 7: Commit** — `git commit -m "feat: redesign autonomous agent console"`.

### Task 4: 逐模块可运行演示动作

**Files:**
- Modify: `workbench/static/js/app.js`
- Modify: `workbench/static/js/editor.js`
- Modify: `workbench/templates/materials/page.html`
- Modify: `workbench/templates/facts/conflict_resolver.html`
- Modify: `workbench/templates/inspiration/page.html`
- Modify: `workbench/templates/inspiration/reference_window.html`
- Modify: `workbench/templates/inspiration/analysis_window.html`
- Modify: `workbench/templates/strategy/page.html`
- Modify: `workbench/templates/strategy/settings_dialog.html`
- Modify: `workbench/templates/editor/page.html`
- Modify: `workbench/templates/editor/journal_editor.html`
- Modify: `workbench/templates/quality/page.html`
- Modify: `workbench/api/drafts.py`
- Modify: `workbench/strategies/service.py`
- Test: `tests/integration/api/test_manual_demo_actions.py`
- Test: `tests/unit/web/test_manual_demo_pages.py`

**Interfaces:**
- Consumes: Task 2 `manual_writes_locked` and Task 1 global project settings.
- Produces: `POST /api/projects/{project_id}/drafts/generate-from-selected` combining outline + draft generation as one UI action.
- Produces: each module page has one real primary action, empty/error/loading/completed states, and explicit next-page link.

- [ ] **Step 1: Write failing manual-action API tests** — analyze reference, generate exactly current three strategies, select with inherited settings, generate draft in one request, save title+content, run check, export; assert active Agent returns 409 for mutating actions.
- [ ] **Step 2: Run `scripts/test.ps1 tests/integration/api/test_manual_demo_actions.py -q`** — expect missing combined endpoint, locking, and strategy-current-set behavior to fail.
- [ ] **Step 3: Add a shared active-run write guard and combined draft endpoint** — reuse `create_outline`/`generate_draft`; preserve the outline error and do not destroy an existing draft on failure.
- [ ] **Step 4: Make strategy generation return/display only the current set** — retain referenced historical strategies as non-current records using an explicit current-set marker or generation identifier with an Alembic migration if persistence requires it.
- [ ] **Step 5: Write failing page tests** — explicit conflict choice required; reference analysis renders persisted fields; empty pages provide preparation links; title and content controls are identifiable; locked pages show “Agent 正在运行”.
- [ ] **Step 6: Run `scripts/test.ps1 tests/unit/web/test_manual_demo_pages.py -q`** — expect current hard-coded/empty behavior to fail.
- [ ] **Step 7: Implement page templates and JavaScript actions** — remove automatic first-conflict resolution, render real analyses, inherit project settings, generate drafts with one action, autosave title and body, and expose check/export actions.
- [ ] **Step 8: Run Task 4 focused tests plus migration head check if schema changed** — expect all PASS and one Alembic head.
- [ ] **Step 9: Commit** — `git commit -m "feat: make every demo module runnable"`.

### Task 5: 双路线 E2E、视觉验收与使用说明

**Files:**
- Modify: `tests/e2e/test_agent_flow.py`
- Modify: `tests/e2e/test_demo_flow.py`
- Modify: `tests/e2e/test_responsive.py`
- Modify: `README.md`
- Modify: `docs/acceptance-record.md`

**Interfaces:**
- Consumes: Tasks 1–4 visible controls and routes.
- Produces: browser-proven autonomous route and manual route without direct URL jumps after project entry.

- [ ] **Step 1: Rewrite failing autonomous E2E** — reset Demo lands on Agent; edit all settings; start; follow visible controls to strategy/editor/final review; export Markdown.
- [ ] **Step 2: Add failing manual-route E2E** — choose function demo; explicitly resolve conflict; analyze a reference; generate/select strategy; generate/edit title and body; run check; export.
- [ ] **Step 3: Run both E2E tests** — expect failure until all visible paths are connected.
- [ ] **Step 4: Fix only integration gaps revealed by the two routes** — no direct `page.goto` beyond initial project entry.
- [ ] **Step 5: Extend responsive test at 1280×800 and 1440×900** — assert primary action visible, no horizontal overflow, dock clickable, and brief inputs usable.
- [ ] **Step 6: Update README** — explain that the user loads Demo and chooses “自主创作” or “功能演示”; document each route in six short steps and retain API integration instructions.
- [ ] **Step 7: Run full verification** — `scripts/test.ps1`; expect zero failures, then `alembic heads`; expect one head.
- [ ] **Step 8: Update acceptance record with exact test counts/timings and screenshots stored under the project**.
- [ ] **Step 9: Commit** — `git commit -m "docs: verify dual-mode demo experience"`.

## Self-Review

- **Spec coverage:** Tasks 1–5 cover editable settings, real navigation, homepage simplification, single-writer behavior, all module actions, both routes, topbar copy removal, responsive UI and documentation.
- **Step scan:** Every task has a failing-test step, one bounded implementation unit, focused verification and a commit; optional migration is isolated to the strategy current-set decision.
- **Type consistency:** `ProjectPatch`, `update_project`, `ProjectNavigation` and `manual_writes_locked` are defined once and consumed by later tasks with matching names.
- **Review focus:** All five listed failure modes map to explicit Task 1, 2 or 4 tests.
- **Proportion:** The plan specifies interfaces, assertions and boundaries without transcribing implementation bodies.
