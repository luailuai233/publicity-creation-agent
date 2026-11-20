# Repository Instructions

## Purpose

This repository implements the 热点驱动宣传创作工作台 as a local-first, single-agent web application. The product turns activity materials and user-provided references into traceable facts, differentiated writing strategies, editable drafts, and checked Markdown exports.

## Stack

- Python, FastAPI, Uvicorn
- Jinja2, HTMX, vanilla JavaScript, CSS
- Pydantic and pydantic-settings
- SQLAlchemy, Alembic, SQLite
- Local filesystem storage
- Typed Agent Runner, Planner, Tool Registry, and AI Provider interfaces
- pytest, HTTPX, and Playwright

## Working Areas

- `workbench/agent/`: orchestration, planning, tools, recovery, and run history
- `workbench/ai/`: provider contracts and structured model schemas
- `workbench/materials/`, `workbench/facts/`, `workbench/references/`, `workbench/strategies/`, `workbench/drafts/`, `workbench/quality/`, `workbench/exports/`: domain services
- `workbench/api/`: JSON endpoints
- `workbench/web/` and `workbench/templates/`: server-rendered UI
- `workbench/db/` and `alembic/`: persistence and migrations
- `tests/`: unit, integration, and browser tests
- `memory-bank/`: approved design, stack decisions, implementation plan, architecture memory, and progress tracking

## Commands

Use only the repository wrappers for normal development and verification:

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
.\scripts\test.ps1
.\scripts\e2e.ps1
```

Do not allow tools, libraries, or test runners to place generated files outside `D:\aipm`.

## Implementation Constraints

- Maintain strict isolation between activity facts and reference-case content.
- Normal supported facts may pass automatically; conflicts, low-confidence facts, missing evidence, privacy risks, and safety risks must trigger the documented human gate.
- The model may use only the inputs exposed through typed provider methods. It must not receive a database session, shell, unrestricted filesystem handle, or tool registry.
- Every agent step must have bounded retries, a call limit, a persisted status, and an actionable error state.
- Database migrations must use Alembic.
- Path reads, writes, and deletions must resolve and validate their project boundary first.
- Runtime data, credentials, uploads, and exports must remain ignored by Git.
- Preserve existing user changes and avoid unrelated rewrites.
- Use `apply_patch` for code and documentation edits.
- Verify behavior with the smallest relevant wrapper command, and run broader tests when the change crosses domain or UI boundaries.

写任何代码前必须完整阅读memory-bank/architecture.md
写任何代码前必须完整阅读memory-bank/design-document.md
每完成一个重大功能或里程碑后，必须更新memory-bank/architecture.md
