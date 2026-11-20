# Repository Guide

## Project

This repository contains the 热点驱动宣传创作工作台, a local-first single-agent web application for organizing publicity materials, resolving facts, analyzing user-provided references, generating writing strategies, drafting content, and checking exports.

## Technology

- Python 3 with FastAPI and Uvicorn
- Jinja2, HTMX, vanilla JavaScript, and CSS
- Pydantic models for application and AI contracts
- SQLAlchemy, Alembic, and SQLite
- Local project file storage
- A typed Agent Runner, Planner, Tool Registry, and AI Provider abstraction
- pytest and Playwright for automated verification

## Repository Structure

- `workbench/`: application code
- `workbench/agent/`: agent planning, execution, tools, snapshots, and recovery
- `workbench/ai/`: model provider interfaces, schemas, mock provider, and fault injection
- `workbench/api/`: JSON API routes
- `workbench/web/`: server-rendered page routes
- `workbench/templates/`: Jinja2 templates
- `workbench/static/`: CSS, JavaScript, and vendored browser assets
- `workbench/db/`: database models, repositories, and sessions
- `alembic/`: database migrations
- `tests/`: unit, integration, and end-to-end tests
- `scripts/`: supported setup, development, and verification commands
- `memory-bank/`: approved product design, technical decisions, implementation plan, architecture memory, and delivery progress
- `storage/`, `exports/`, `.runtime/`, and `test-results/`: runtime output under the D drive workspace

## Supported Commands

Use the repository wrapper scripts instead of invoking package tools directly:

```powershell
.\scripts\setup.ps1
.\scripts\dev.ps1
.\scripts\test.ps1
.\scripts\e2e.ps1
```

All generated files, caches, databases, uploads, exports, and test artifacts must remain within `D:\aipm`.

## Engineering Rules

- Preserve the separation between activity facts and reference-case inspiration.
- Never invent unsupported facts or silently bypass a human confirmation gate.
- Keep agent tools typed, allowlisted, independently testable, and free of arbitrary shell or filesystem access.
- Persist important agent state before starting long-running or external work.
- Keep the default mock-provider flow deterministic and runnable without external credentials.
- Never commit API keys, real sensitive material, runtime databases, uploads, or generated exports.
- Preserve unrelated user changes in the working tree.
- Use `apply_patch` for source and documentation edits.
- Add or update focused tests for behavior changes and run the relevant wrapper verification before reporting completion.

写任何代码前必须完整阅读memory-bank/architecture.md
写任何代码前必须完整阅读memory-bank/design-document.md
每完成一个重大功能或里程碑后，必须更新memory-bank/architecture.md
