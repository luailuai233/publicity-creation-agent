# 热点驱动宣传创作工作台 Python Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用 Python 构建无需外部 AI API、可在本机完整运行六页创作闭环的复古编辑部 Web Demo，并保证所有项目运行时写入都限制在 `D:\aipm\demo`。

**Architecture:** FastAPI 同时提供服务端渲染页面和内部 JSON API；Jinja2 + HTMX 负责主要交互，少量项目内原生 JavaScript 处理自动保存、轮询、剪贴板和上传进度。SQLAlchemy 2 + SQLite 保存业务状态，Alembic 管理迁移；Python `AIProvider` Protocol 由确定性 Mock 实现提供 Pydantic 校验的结构化结果。

**Tech Stack:** Python 3.11+、FastAPI、Uvicorn、Jinja2、HTMX、SQLAlchemy 2、Alembic、SQLite、Pydantic 2、python-multipart、python-docx、pypdf、Pillow、pytest、pytest-asyncio、HTTPX、Python Playwright。

**Spec:** `docs/superpowers/specs/2026-11-14-publicity-creation-workbench-design.md`

## Global Constraints

- 所有源码、`.venv`、pip 缓存、Python 字节码、临时文件、数据库、上传、导出和测试产物必须位于 `D:\aipm\demo`。
- 只通过 `scripts/setup.ps1`、`scripts/dev.ps1`、`scripts/test.ps1`、`scripts/e2e.ps1` 执行会产生运行时文件的命令。
- `PIP_CACHE_DIR=.runtime/pip-cache`、`PYTHONPYCACHEPREFIX=.runtime/pycache`、`PYTHONUSERBASE=.runtime/python-user`、`TEMP=.runtime/tmp`、`TMP=.runtime/tmp`、`PLAYWRIGHT_BROWSERS_PATH=.runtime/playwright-browsers`，均解析成项目内绝对路径。
- 不使用 Node/npm，不使用 CDN；HTMX 和必要的原生 JavaScript 作为项目静态文件提交。
- 数据库为 `storage/app.db`；上传位于 `storage/projects/<projectId>`；导出位于 `exports/`。
- Markdown 仅由服务端写入 `exports/` 并返回路径，不触发浏览器文件下载。
- 单文件上限 20 MB；每项目最多 30 个文件、总容量 200 MB；图片只接受 PNG、JPG/JPEG、WEBP。
- 首版不调用外部模型；所有 AI 返回必须 `is_demo=True` 并通过 Pydantic Model。
- Material 与 ReferenceCase 分表；策略和正文只能读取 CONFIRMED FactCard；冲突不得自动裁决。
- 六页共享固定桌面外壳；每页最多一个粉色主 CTA；1280×800 下灵感页仍保持三列。
- 所有写 API 使用 Pydantic 校验并统一返回 `{data, error, requestId}`；Job 以 1.5 秒轮询。
- 使用 TDD；每个任务先运行目标测试确认失败，实现后再确认通过并提交。

## Review Focus

- `..`、绝对路径、保留字符和重复文件名不得逃逸 `storage/projects`；Task 4 覆盖。
- 应用重启后遗留 PROCESSING Job 必须变为可重试 FAILED；Task 4 覆盖。
- 删除唯一来源后，事实必须回到 PENDING，并阻止旧策略继续生成；Tasks 5、8 覆盖。
- Mock 输出连续两次 Pydantic 校验失败时必须保留已有结果并显示 NEEDS_REVIEW；Tasks 6–8 覆盖。
- 检查失败或存在未处理 HIGH 问题时不得静默导出；Task 9 覆盖。

---

### Task 1: D 盘运行环境与 FastAPI 骨架

**Files:**
- Create: `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `.gitignore`, `.env.example`
- Create: `scripts/runtime-env.ps1`, `scripts/setup.ps1`, `scripts/dev.ps1`, `scripts/test.ps1`, `scripts/e2e.ps1`
- Create: `workbench/__init__.py`, `workbench/main.py`, `workbench/settings.py`, `workbench/runtime_paths.py`
- Create: `workbench/templates/base.html`, `workbench/templates/home.html`, `workbench/static/css/app.css`, `workbench/static/js/app.js`, `workbench/static/vendor/htmx.min.js`
- Test: `tests/unit/test_runtime_paths.py`, `tests/test_app.py`

**Interfaces:**
- Consumes: none.
- Produces: `RuntimePaths` dataclass; `get_runtime_paths(root: Path | None = None) -> RuntimePaths`; `create_app(settings: Settings | None = None) -> FastAPI`.

- [ ] **Step 1: Write failing runtime-path and health tests**

Assert every computed writable path is an absolute descendant of `D:\aipm\demo`; assert `GET /health` returns `{"status":"ok"}` and `GET /` renders HTML.

- [ ] **Step 2: Create minimal dependency metadata and run the failing tests**

Run `powershell -ExecutionPolicy Bypass -File .\scripts\setup.ps1`, then `powershell -ExecutionPolicy Bypass -File .\scripts\test.ps1 tests/unit/test_runtime_paths.py tests/test_app.py`; expected: FAIL because application modules are missing.

- [ ] **Step 3: Implement runtime environment wrappers**

`runtime-env.ps1` resolves root from `$PSScriptRoot`, creates `.runtime` children, `.venv`, `storage` and `exports`, then exports the required variables only for the child process; do not write machine/user environment settings.

- [ ] **Step 4: Implement FastAPI factory and local static/template setup**

Mount `/static`, configure Jinja2, add `/health` and the placeholder home route, and load vendored HTMX without CDN references.

- [ ] **Step 5: Verify tests and writable paths**

Run the focused tests; expected: PASS. List generated files and confirm they are all below the repo.

- [ ] **Step 6: Commit**

Commit message: `chore: bootstrap D-drive constrained FastAPI app`.

### Task 2: SQLAlchemy 数据模型、迁移与项目仓储

**Files:**
- Create: `alembic.ini`, `alembic/env.py`, `alembic/versions/0001_initial.py`
- Create: `workbench/db/base.py`, `workbench/db/session.py`, `workbench/db/models.py`, `workbench/db/projects.py`, `workbench/domain/enums.py`, `workbench/domain/project_schemas.py`
- Create: `workbench/demo/seed.py`
- Test: `tests/integration/test_projects_repository.py`, `tests/integration/test_domain_isolation.py`
- Modify: `scripts/setup.ps1`

**Interfaces:**
- Consumes: `RuntimePaths`.
- Produces: SQLAlchemy models for all design entities; `create_project`, `list_projects`, `get_project`, `delete_project`; `ProjectCreate`/`ProjectRead` Pydantic models.

- [ ] **Step 1: Write failing repository tests**

Test default audience/tone/length, persistence across sessions, Material/ReferenceCase table separation, unknown ID handling, and safe project cascade deletion.

- [ ] **Step 2: Run focused tests**

Expected: FAIL because database modules are absent.

- [ ] **Step 3: Define enums, ORM models and initial Alembic migration**

Include Project, Material, SourceChunk, FactCard, FactSource, TimelineItem, ReferenceCase, ReferenceAnalysis, Strategy, Draft, DraftCitation, QualityIssue, Job and EventLog with design-specified states and constraints.

- [ ] **Step 4: Implement sessions and project repository**

Use explicit transaction scopes; before deleting a storage directory resolve it and verify it is a descendant of `storage/projects`.

- [ ] **Step 5: Add deterministic sanitized seed entry point**

Create one `is_demo=True` project marker and seed interface; detailed content arrives in Task 10.

- [ ] **Step 6: Apply migration and verify**

Run setup/migration and focused tests; expected: PASS and database only at `storage/app.db`.

- [ ] **Step 7: Commit**

Commit message: `feat: add persistent Python domain model`.

### Task 3: 复古桌面组件与项目首页

**Files:**
- Create: `workbench/web/dependencies.py`, `workbench/web/page_routes.py`, `workbench/api/projects.py`, `workbench/api/responses.py`
- Create: `workbench/templates/components/desktop.html`, `topbar.html`, `dock.html`, `window.html`, `buttons.html`, `taskbar.html`, `dialog.html`
- Create: `workbench/templates/projects/index.html`, `create_form.html`, `recent_projects.html`
- Modify: `workbench/main.py`, `workbench/static/css/app.css`, `workbench/templates/base.html`
- Test: `tests/unit/web/test_retro_shell.py`, `tests/integration/api/test_projects_api.py`

**Interfaces:**
- Consumes: project repository and Pydantic schemas.
- Produces: reusable Jinja macros/partials; `GET/POST /api/projects`; `GET/DELETE /api/projects/{id}`; home page project flows.

- [ ] **Step 1: Write failing shell and API tests**

Assert 52 px topbar, 116 px Dock, 44 px taskbar, visible focus CSS, reduced-motion rule, exactly one pink CTA, project creation defaults, recent ordering and deletion confirmation markup.

- [ ] **Step 2: Run focused tests**

Expected: FAIL for missing routes/templates.

- [ ] **Step 3: Implement shared response contract and project API**

Every API response uses `data`, `error`, `requestId`; validation errors return actionable Chinese messages.

- [ ] **Step 4: Implement server-rendered retro shell and home flow**

Use HTMX for create/delete/refresh fragments; include empty, loading, success and failure fragments; use inline SVG or CSS icons without third-party brand assets.

- [ ] **Step 5: Verify and commit**

Run focused tests; expected: PASS. Commit: `feat: add retro desktop and project home`.

### Task 4: 素材存储、解析与后台 Job

**Files:**
- Create: `workbench/storage/local.py`, `workbench/materials/limits.py`, `workbench/materials/parsers.py`, `workbench/materials/service.py`
- Create: `workbench/jobs/models.py`, `workbench/jobs/repository.py`, `workbench/jobs/runner.py`, `workbench/jobs/recovery.py`
- Create: `workbench/api/materials.py`, `workbench/api/jobs.py`, `workbench/web/material_routes.py`
- Create: `workbench/templates/materials/page.html`, `file_tree.html`, `material_list.html`, `material_preview.html`, `upload_queue.html`, `progress.html`
- Create: `workbench/static/js/materials.js`
- Test: `tests/unit/storage/test_local_storage.py`, `tests/unit/materials/test_limits.py`, `tests/integration/api/test_materials_api.py`, `tests/integration/jobs/test_recovery.py`

**Interfaces:**
- Consumes: project models and runtime paths.
- Produces: `save_material_file(project_id, original_name, stream) -> StoredFile`; `parse_material(material_id) -> ParseResult`; `enqueue_job(JobCreate) -> JobRead`; material CRUD/retry endpoints and job polling endpoint.

- [ ] **Step 1: Write failing file-limit and path-safety tests**

Cover 20 MB boundary, 30-file and 200 MB project boundaries, accepted DOCX/PDF/TXT/PNG/JPG/JPEG/WEBP, rejected extensions/MIME mismatches, `..`/absolute/reserved/duplicate names and safe generated filenames.

- [ ] **Step 2: Write failing Job recovery tests**

Assert files have independent Job states, sibling success survives one failure, and startup converts stale PROCESSING to retryable FAILED.

- [ ] **Step 3: Run focused tests**

Expected: FAIL for missing storage/parsers/jobs.

- [ ] **Step 4: Implement storage and parser adapters**

Read TXT, DOCX and textual PDF locally; use Pillow only to validate image format/dimensions; return editable `is_demo=True` OCR/scene summary without identifying people.

- [ ] **Step 5: Implement in-process Job runner and recovery**

Use FastAPI lifespan to run recovery once and `asyncio.create_task` for Demo tasks; persist every transition and error code.

- [ ] **Step 6: Implement three-column materials page and APIs**

Support upload/paste, per-file progress, category/parsed-text editing, retry/delete and 1.5-second polling; include empty/failure/needs-review states.

- [ ] **Step 7: Verify and commit**

Run focused tests; expected: PASS. Commit: `feat: add resilient Python material ingestion`.

### Task 5: 事实、来源、时间线与冲突

**Files:**
- Create: `workbench/facts/schemas.py`, `workbench/facts/extractor.py`, `workbench/facts/service.py`, `workbench/facts/eligibility.py`
- Create: `workbench/api/facts.py`
- Create: `workbench/templates/facts/fact_note.html`, `source_dialog.html`, `conflict_resolver.html`, `timeline.html`
- Test: `tests/unit/facts/test_state_machine.py`, `tests/integration/facts/test_source_deletion.py`, `tests/integration/api/test_facts_api.py`
- Modify: `workbench/templates/materials/page.html`, `workbench/materials/service.py`

**Interfaces:**
- Consumes: SourceChunks and material-delete transaction.
- Produces: `extract_fact_candidates(project_id)`, `update_fact(fact_id, patch)`, `resolve_conflict(group_id, resolution)`, `get_eligible_facts(project_id) -> list[ConfirmedFact]`.

- [ ] **Step 1: Write failing lifecycle tests**

Test PENDING → CONFIRMED/INVALID, conflict blocking, quote-source requirement, source coordinates, manual resolution, no automatic conflict decision and sole-source deletion reverting to PENDING.

- [ ] **Step 2: Run focused tests**

Expected: FAIL for missing fact modules.

- [ ] **Step 3: Implement conservative deterministic extraction and eligibility**

Extract obvious time/location/person-role/number/quote/event candidates; all user-upload candidates start PENDING; only seeded unambiguous Demo facts may start CONFIRMED.

- [ ] **Step 4: Implement transactional APIs and UI fragments**

Use HTMX for confirm/edit/invalidate/source/conflict operations; disable downstream action while conflicts or missing confirmation remain.

- [ ] **Step 5: Verify and commit**

Expected: PASS. Commit: `feat: add traceable fact verification`.

### Task 6: Pydantic Mock AI 与参考案例拆解

**Files:**
- Create: `workbench/ai/provider.py`, `workbench/ai/mock_provider.py`, `workbench/ai/envelope.py`, `workbench/ai/faults.py`
- Create: `workbench/ai/schemas/material.py`, `reference.py`, `strategy.py`, `draft.py`, `quality.py`
- Create: `workbench/references/service.py`, `workbench/api/references.py`, `workbench/web/inspiration_routes.py`
- Create: `workbench/templates/inspiration/page.html`, `reference_window.html`, `analysis_window.html`, `guidance_window.html`
- Create: `workbench/static/css/inspiration.css`
- Test: `tests/unit/ai/test_mock_provider.py`, `tests/integration/references/test_isolation.py`, `tests/unit/web/test_inspiration_layout.py`

**Interfaces:**
- Consumes: Job runner and ReferenceCase models.
- Produces: `AIProvider` Protocol; `AIEnvelope[T]`; deterministic `MockAIProvider`; reference CRUD/analyze routes.

- [ ] **Step 1: Write failing Provider tests**

Assert deterministic seed, `is_demo=True`, Pydantic validation, one retry after malformed output, NEEDS_REVIEW after two failures, prior result preservation, and no external network call.

- [ ] **Step 2: Write failing data-isolation and layout tests**

Assert reference analysis creates no FactCard; assert 1280 px CSS keeps three columns, three case slots, four mechanism groups, three guidance groups and one pink CTA.

- [ ] **Step 3: Run focused tests**

Expected: FAIL for missing provider/page.

- [ ] **Step 4: Implement Python Protocol, Mock Provider and fault injection**

Provide fixed delay, deterministic seed and per-module `schema_error`/`timeout`; envelope includes schema version, warnings, source/fact IDs, provider metadata and retry count, never chain-of-thought.

- [ ] **Step 5: Implement reference APIs and inspiration page**

Accept pasted text and screenshots; link input stores a label plus user-pasted content and never fetches URLs; mark every result “Demo 模拟结果”.

- [ ] **Step 6: Verify and commit**

Expected: PASS. Commit: `feat: add Python mock AI reference analysis`.

### Task 7: 三套创作策略

**Files:**
- Create: `workbench/strategies/difference.py`, `workbench/strategies/service.py`, `workbench/api/strategies.py`, `workbench/web/strategy_routes.py`
- Create: `workbench/templates/strategy/page.html`, `proposal_window.html`, `settings_dialog.html`
- Create: `workbench/static/css/strategy.css`
- Test: `tests/unit/strategies/test_difference.py`, `tests/integration/strategies/test_generation.py`, `tests/unit/web/test_strategy_page.py`

**Interfaces:**
- Consumes: `get_eligible_facts`, selected ReferenceAnalysis summaries and `AIProvider.generate_strategies`.
- Produces: `validate_strategy_set`, `generate_strategies(project_id)`, `select_strategy(strategy_id, settings)`.

- [ ] **Step 1: Write failing strategy tests**

Assert exactly three strategies, at least two viewpoints/openings/structures, non-identical fact sets, rejection of PENDING/CONFLICT facts, NEEDS_REVIEW for insufficient facts, retry behavior and preservation on failure.

- [ ] **Step 2: Run focused tests**

Expected: FAIL for missing strategy modules.

- [ ] **Step 3: Implement validation, generation and selection service**

Persist 人物故事型、反差成长型、现场纪实型 only after programmatic difference validation; store exact fact IDs and method summaries, never reference raw text.

- [ ] **Step 4: Implement three-window page**

Render equal proposals, pink selected titlebar, complete strategy attributes, settings dialog and a single disabled-until-selected “生成标题与大纲” CTA.

- [ ] **Step 5: Verify and commit**

Expected: PASS. Commit: `feat: add differentiated strategy selection`.

### Task 8: 标题、大纲、正文、引用与自动保存

**Files:**
- Create: `workbench/drafts/service.py`, `workbench/drafts/citations.py`, `workbench/api/drafts.py`, `workbench/web/editor_routes.py`
- Create: `workbench/templates/editor/page.html`, `material_drawer.html`, `journal_editor.html`, `citation_badge.html`, `statusbar.html`
- Create: `workbench/static/css/editor.css`, `workbench/static/js/editor.js`
- Test: `tests/integration/drafts/test_confirmed_only.py`, `tests/integration/drafts/test_versions.py`, `tests/e2e/test_editor_autosave.py`

**Interfaces:**
- Consumes: selected Strategy, current eligible facts and `AIProvider.generate_outline/generate_draft`.
- Produces: `create_outline(project_id)`, `generate_draft(project_id, title, outline)`, `save_draft(draft_id, patch)` and DraftCitation rows.

- [ ] **Step 1: Write failing service tests**

Assert five titles, editable outline, selected-strategy requirement, only current CONFIRMED facts in provider input, stale fact blocking, every key citation resolving to a source, new generation creating a version and failure preserving existing work.

- [ ] **Step 2: Write failing browser autosave test**

Assert no request before 2 seconds, exactly one PATCH after debounce, and updated save time/word/citation counts.

- [ ] **Step 3: Run focused tests**

Expected: FAIL for missing draft/editor modules.

- [ ] **Step 4: Implement draft services and APIs**

Store Markdown and citation block IDs; re-check eligible facts immediately before generation; generate a new version and edit only the current version.

- [ ] **Step 5: Implement three-pane editor**

Use 220–240 px facts drawer, flexible Paper center and 280–300 px suggestions; include title/outline/body tabs, source dialog, Demo label, 2-second autosave and status bar.

- [ ] **Step 6: Verify and commit**

Expected: PASS. Commit: `feat: add sourced Python journal drafting`.

### Task 9: 质量检查与 D 盘安全导出

**Files:**
- Create: `workbench/quality/scanner.py`, `workbench/quality/similarity.py`, `workbench/quality/service.py`
- Create: `workbench/exports/markdown.py`, `workbench/exports/plain_text.py`
- Create: `workbench/api/quality.py`, `workbench/api/exports.py`, `workbench/web/export_routes.py`
- Create: `workbench/templates/quality/page.html`, `scan_progress.html`, `issue_list.html`, `export_preview.html`
- Create: `workbench/static/css/quality.css`, `workbench/static/js/export.js`
- Test: `tests/unit/quality/test_scanner.py`, `tests/integration/quality/test_check_failure.py`, `tests/integration/exports/test_markdown.py`

**Interfaces:**
- Consumes: Draft, DraftCitation, eligible facts, method summaries and `AIProvider.check_quality`.
- Produces: `scan_draft(draft_id)`, `run_quality_check(draft_id)`, `write_markdown_export(draft_id) -> Path`.

- [ ] **Step 1: Write failing scanner tests**

Cover unsourced person/role/time/location/number/quote, conflict, pending items, privacy markers and reference-like expression; assert type, severity and block ID.

- [ ] **Step 2: Write failing export-gate and path tests**

Assert CHECK_INCOMPLETE on failure, explicit confirmation for unresolved HIGH issues, no silent pass, export path strictly below `exports`, and output omits IDs/prompts/provider metadata/reference original text.

- [ ] **Step 3: Run focused tests**

Expected: FAIL for missing quality/export modules.

- [ ] **Step 4: Implement scanner, orchestration and issue updates**

Run deterministic checks first and Mock supplemental checks second; store results per Draft version and expose progress/retry states.

- [ ] **Step 5: Implement three-pane check page and safe export**

Write Markdown server-side to `exports`; show the absolute saved path instead of browser download; copy plain text with project JavaScript; keep one pink CTA.

- [ ] **Step 6: Verify and commit**

Expected: PASS. Commit: `feat: add guarded quality check and D-drive export`.

### Task 10: 完整 Demo、E2E、文档与最终质量门

**Files:**
- Create: `tests/e2e/test_demo_flow.py`, `tests/e2e/test_failure_recovery.py`, `tests/e2e/test_responsive.py`
- Create: `tests/fixtures/materials/event_flow.txt`, `interview.txt`, `speech.txt`, `tests/fixtures/references/case_a.txt`
- Create: `workbench/api/demo.py`, `workbench/templates/projects/demo_button.html`
- Create: `README.md`, `Dockerfile`, `.dockerignore`, `docs/demo-script.md`, `docs/acceptance-record.md`, `docs/product-retrospective.md`
- Modify: `workbench/demo/seed.py`, `workbench/templates/projects/index.html`, `.env.example`, `.gitignore`

**Interfaces:**
- Consumes: complete application.
- Produces: resettable deterministic Demo project, full browser proof, local operating guide and optional single-instance Docker route.

- [ ] **Step 1: Write failing full-flow E2E**

Open/reset Demo, process materials, inspect sources, resolve conflict, analyze three references, generate/select strategy, choose title/outline, edit/autosave draft, inspect citations, run check, handle issues and create Markdown under `exports`.

- [ ] **Step 2: Write failing failure and responsive E2E**

Inject one material failure and one schema failure; assert sibling progress and preserved results. At 1440×900 and 1280×800 assert CTA visibility, no page-level horizontal overflow and three-column inspiration layout.

- [ ] **Step 3: Complete sanitized fixtures and safe Demo reset**

Seed three materials, sourced facts, one time conflict, three references and deterministic downstream results; reset only `is_demo=True` records and validated storage descendants.

- [ ] **Step 4: Write documentation and Docker files**

README documents only wrapper commands, D-drive guarantees/limits, setup/run/test/E2E, Demo reset, fault injection, data deletion, architecture and future real Provider. Docker uses a single instance and mounted `/app/storage`/`/app/exports`.

- [ ] **Step 5: Run the full quality gate**

Run `scripts/test.ps1`, then `scripts/e2e.ps1` three consecutive times; expected: all tests PASS, Alembic is current, traces/screenshots remain under project test-results, and Markdown exports appear only under `exports`.

- [ ] **Step 6: Record acceptance and inspect writes**

Document commands, results, viewport evidence, P1 exclusions and generated artifact paths; verify no project command is configured to write C-drive runtime data.

- [ ] **Step 7: Commit**

Commit message: `docs: complete Python demo delivery`.

## Self-Review Record

- Spec coverage: Tasks 1–10 cover the six pages, data boundaries, Python Mock Provider, failure states, safe export, fixed upload limits, D-drive constraint, tests and all P0 deliverables.
- Step scan: each task identifies concrete interfaces, exact behavior and a focused verification command; tests precede implementation.
- Type consistency: ORM entities feed Pydantic schemas, Provider envelopes, strategy/draft/quality services and page/API routes with stable names.
- Review Focus: all five high-risk conditions have explicit tests in their owning tasks.
- Proportion: the plan fixes decisions and assertions without embedding implementation bodies.
