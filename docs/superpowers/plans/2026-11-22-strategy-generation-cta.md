# Strategy Generation CTA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit, gated transition from completed inspiration analysis to three generated strategy proposals.

**Architecture:** Page routes derive readiness from the same eligible-fact rule used by the strategy service and expose a shared Jinja CTA partial. Native JavaScript calls the existing strategy generation API and redirects after success; missing facts route the user to the Agent workspace.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy, Jinja2, native JavaScript, pytest, Playwright

**Spec:** `docs/superpowers/specs/2026-11-22-strategy-generation-cta-design.md`

## Global Constraints

- Preserve the existing strategy service as the authoritative backend gate.
- Do not trigger a model request without an explicit click.
- Add no dependency or new persistence model.
- Keep API keys server-side and do not log reference or fact text.

## Review Focus

- Missing facts: show the Agent recovery action and do not render an enabled generation button.
- Missing analysis: do not claim the project is ready to generate strategies.
- Provider/API failure: keep the user on the page, show the error and re-enable the button.
- Existing three strategies: navigate/render without generating duplicates automatically.
- Browser cache: bump the shared static version when JavaScript changes.

---

### Task 1: Shared strategy generation CTA

**Files:**
- Create: `workbench/templates/strategy/generate_cta.html`
- Modify: `workbench/web/inspiration_routes.py`
- Modify: `workbench/web/strategy_routes.py`
- Modify: `workbench/templates/inspiration/page.html`
- Modify: `workbench/templates/strategy/page.html`
- Modify: `tests/unit/web/test_inspiration_layout.py`
- Modify: `tests/unit/web/test_strategy_page.py`

**Interfaces:**
- Consumes: `get_eligible_facts(session, project_id)` and `has_minimum_fact_set(fact_types)`.
- Produces: template context boolean `can_generate_strategies` and a shared CTA with `data-generate-strategies`.

- [ ] Write failing template tests for eligible and missing-fact CTA states on both pages.
- [ ] Run the focused tests and verify they fail because the CTA is absent.
- [ ] Derive `can_generate_strategies` in both page routes and render the shared partial.
- [ ] Run the focused tests and verify they pass.

### Task 2: Generate and redirect interaction

**Files:**
- Modify: `workbench/static/js/app.js`
- Modify: `workbench/templates/base.html`
- Modify: `tests/e2e/test_reference_input.py`

**Interfaces:**
- Consumes: `POST /api/projects/{project_id}/strategies/generate`.
- Produces: disabled loading state, taskbar feedback, redirect to `/project/{project_id}/strategy`, and recoverable API errors.

- [ ] Extend the browser test to click the enabled CTA and assert three proposal windows after navigation.
- [ ] Run the focused browser test and verify it fails because no CTA handler exists; if the sandbox cannot start Uvicorn, record that environment error without treating it as a behavior pass.
- [ ] Implement the native JavaScript handler and bump `static_version`.
- [ ] Run JavaScript syntax, focused template/service tests, Ruff and the browser test when the environment permits.

### Task 3: Architecture memory

**Files:**
- Modify: `memory-bank/architecture.md`
- Modify: `memory-bank/progress.md`

**Interfaces:**
- Consumes: verified behavior and test evidence from Tasks 1–2.
- Produces: an accurate handoff record for later developers.

- [ ] Record the gated transition, file responsibilities and exact verification evidence.
- [ ] Re-read the entries and ensure no unverified browser result is described as passing.
