#!/bin/sh
set -eu

: "${WORKBENCH_ROOT:=/tmp/workbench}"
: "${PORT:=8000}"

mkdir -p "${WORKBENCH_ROOT}/storage/projects" "${WORKBENCH_ROOT}/exports" "${WORKBENCH_ROOT}/test-results" "${WORKBENCH_ROOT}/.runtime"
export WORKBENCH_ROOT
export DATABASE_URL="sqlite:///${WORKBENCH_ROOT}/storage/app.db"

python -m alembic upgrade head
exec python -m uvicorn workbench.main:app --host 0.0.0.0 --port "${PORT}" --workers 1
