# Free Render Public Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the local workbench into a publicly deployable, real-input single-user site with visible workflow navigation, real reference ingestion, correct provider provenance, and free Render deployment.

**Architecture:** Keep the existing FastAPI modular monolith, SQLite, local file storage, and single-process Agent Runner. Add a top workflow navigation component, typed reference-ingestion boundaries for text/link/screenshot, and a Docker/Render runtime rooted in ephemeral writable storage. Example data remains optional and separate from real projects.

**Tech Stack:** Python 3.12, FastAPI, Jinja2, vanilla JavaScript/CSS, SQLAlchemy/Alembic/SQLite, HTTPX, Pillow, Docker, Render Blueprint, pytest, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-22-free-render-public-demo-design.md`

## Global Constraints

- Any holder of the public URL may access the site; do not add login or a shared password.
- Keep one Uvicorn worker and one application instance; concurrent visitors share ephemeral data.
- Existing real projects must be creatable without loading example data.
- Real model credentials remain server-side environment variables and must never enter HTML, logs, or Git.
- Activity facts and reference-case content remain isolated in storage and model inputs.
- Keep all development and test artifacts inside `D:\aipm\demo`.
- Do not create Git commits automatically: the checkout already contains user-owned uncommitted implementation work.

## Review Focus

- A strategy-selection wait must route to `/strategy` and must not submit a generic answer payload.
- A screenshot filename or path supplied by a browser must never become an unrestricted server filesystem read.
- Link ingestion must reject private/reserved targets and must not send raw HTML noise to the model.
- Real-provider results must not retain `is_demo=True`; Mock use must remain technically available without page branding.
- Render migration and application processes must point to the same ephemeral SQLite file and use the platform port.

---

### Task 1: Visible Workflow Navigation and Product Copy

**Files:**
- Modify: `workbench/templates/components/topbar.html`
- Create: `workbench/templates/components/workflow_nav.html`
- Modify: project page templates under `workbench/templates/`
- Modify: `workbench/static/css/app.css`
- Modify: `tests/unit/web/test_agent_workspace.py`
- Modify: `tests/unit/web/test_retro_shell.py`
- Modify: `tests/e2e/test_responsive.py`

**Interfaces:**
- Consumes: `ProjectNavigation.items` from `workbench/web/project_navigation.py`.
- Produces: a visible `nav[aria-label="项目工作流"]` with seven links on every project page.

- [ ] **Step 1:** Add failing page tests asserting seven visible workflow links and absence of `LOCAL · MOCK AI`, “本地优先 · 自动保存”, “Demo 模拟结果”, and automatic-save promotional copy.
- [ ] **Step 2:** Run the focused web tests and verify they fail on current markup.
- [ ] **Step 3:** Implement the top workflow navigation, remove the project-page side Dock, and remove implementation/demo branding while retaining the optional “载入示例项目” action.
- [ ] **Step 4:** Run focused web and responsive tests; verify seven links remain visible at 1440×900 and 1280×800 without horizontal overflow.

### Task 2: Correct Strategy-Selection Human Gate

**Files:**
- Modify: `workbench/templates/agent/status_panel.html`
- Modify: `workbench/templates/agent/question_form.html`
- Modify: `workbench/api/agent_runs.py` if payload wording needs alignment
- Modify: `tests/unit/web/test_agent_workspace.py`
- Modify: `tests/e2e/test_agent_flow.py`

**Interfaces:**
- Consumes: `AgentRun.status == "WAITING_USER"` and `waiting_reason == "STRATEGY_SELECTION"`.
- Produces: a direct `/project/{project_id}/strategy` call to action; generic question form remains for actual structured questions only.

- [ ] **Step 1:** Add a failing test that seeds a strategy-selection wait and asserts “前往编辑提案” is present while `data-agent-answer` is absent.
- [ ] **Step 2:** Run the focused test and verify failure against the generic form.
- [ ] **Step 3:** Branch the server-rendered waiting UI by reason and update the next-action wording.
- [ ] **Step 4:** Run focused page/API tests and the Agent E2E through selection and automatic resume.

### Task 3: Real Reference Text, Link, and Screenshot Ingestion

**Files:**
- Modify: `workbench/references/fetcher.py`
- Modify: `workbench/references/service.py`
- Modify: `workbench/api/references.py`
- Modify: `workbench/templates/inspiration/reference_window.html`
- Modify: `workbench/static/js/app.js`
- Modify: `workbench/static/css/inspiration.css`
- Modify: `tests/unit/references/test_safe_fetcher.py`
- Modify: `tests/integration/references/test_reference_inputs.py`
- Modify: `tests/e2e/test_demo_flow.py`

**Interfaces:**
- Produces: `SafeReferenceFetcher.fetch(url: str) -> str` returning normalized readable text rather than raw HTML.
- Produces: multipart `POST /api/projects/{project_id}/references/upload` for a validated image plus optional text/label.
- Preserves: JSON `POST /api/projects/{project_id}/references` for TEXT and LINK input.

- [ ] **Step 1:** Add failing fetcher tests for title/body extraction, script/style removal, whitespace normalization, empty readable text, private targets, redirects, size, and content type.
- [ ] **Step 2:** Run fetcher tests and verify raw HTML behavior fails the readable-text assertions.
- [ ] **Step 3:** Implement a bounded standard-library HTML text extractor inside the safe fetcher.
- [ ] **Step 4:** Add failing API tests for real TEXT/LINK creation, screenshot upload into the project boundary, invalid MIME/oversize rejection, and missing-vision fallback.
- [ ] **Step 5:** Implement screenshot upload through `LocalStorage`, image validation, optional human description, and reference creation without accepting browser-supplied server paths.
- [ ] **Step 6:** Add and implement the three-mode inspiration form, success/error feedback, and refresh behavior.
- [ ] **Step 7:** Run reference unit/integration tests plus a browser flow that adds and analyzes a text reference.

### Task 4: Correct Real-Provider Provenance

**Files:**
- Modify: `workbench/references/service.py`
- Modify: relevant strategy/draft/quality persistence if they hard-code demo provenance
- Modify: `tests/integration/references/test_isolation.py`
- Modify: `tests/unit/ai/test_openai_reference_analysis.py`

**Interfaces:**
- Consumes: `AIEnvelope.is_demo` from any provider method.
- Produces: persisted provenance matching the provider envelope; real provider results are never marked demo.

- [ ] **Step 1:** Add a failing integration test using a real-provider-shaped envelope with `is_demo=False` and assert persisted analysis is not demo.
- [ ] **Step 2:** Run the test and verify the current hard-coded `True` fails it.
- [ ] **Step 3:** Persist envelope provenance and audit other generated entities for the same hard-coded bug.
- [ ] **Step 4:** Run all provider and affected domain tests.

### Task 5: Free Render Runtime and Public-Site Safety

**Files:**
- Modify: `Dockerfile`
- Create: `render.yaml`
- Create: `scripts/container-start.sh`
- Modify: `workbench/settings.py`
- Modify: `workbench/main.py`
- Modify: `.env.example`
- Create: `tests/unit/test_public_deployment.py`

**Interfaces:**
- Produces: container startup using `PORT`, one worker, Alembic migration, and a single `WORKBENCH_ROOT`/`DATABASE_URL` database location.
- Produces: production security headers and bounded request bodies without breaking file-specific upload validation.

- [ ] **Step 1:** Add failing deployment tests that build settings from Render-style environment variables, run startup contract checks, and exercise `/health` plus security headers.
- [ ] **Step 2:** Verify the current Python 3.9 image, fixed port, and split database paths fail the contract.
- [ ] **Step 3:** Upgrade the runtime image to Python 3.12, install locked dependencies, add the portable startup script, and add the free Render Blueprint.
- [ ] **Step 4:** Add minimal production response headers and a configurable request-body ceiling appropriate for the existing 20 MB-per-file and 200 MB-per-project rules.
- [ ] **Step 5:** Run deployment tests, build the Docker image if Docker is available, and run a container health check; otherwise record Docker unavailability and verify the startup script locally.

### Task 6: Documentation, Architecture Memory, and Final Acceptance

**Files:**
- Modify: `README.md`
- Modify: `docs/demo-script.md`
- Create: `docs/render-deployment.md`
- Modify: `docs/acceptance-record.md`
- Modify: `memory-bank/architecture.md`
- Modify: `memory-bank/progress.md`

**Interfaces:**
- Consumes: verified commands and limitations from Tasks 1–5.
- Produces: a reproducible GitHub-to-Render deployment guide and accurate current architecture record.

- [ ] **Step 1:** Document GitHub push, Render Blueprint creation, required/optional environment variables, cold-start behavior, ephemeral data, public shared state, model-budget risk, and TEXT/LINK/SCREENSHOT usage.
- [ ] **Step 2:** Update architecture and progress only with behaviors proven by tests.
- [ ] **Step 3:** Run `scripts/test.ps1 -q`, `scripts/e2e.ps1 -q`, Ruff, Alembic current, and `git diff --check`.
- [ ] **Step 4:** Record exact results and provide the user with local acceptance commands plus the remaining Render dashboard actions that require their GitHub/Render account.
