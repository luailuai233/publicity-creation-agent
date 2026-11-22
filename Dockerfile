FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WORKBENCH_ROOT=/tmp/workbench
COPY requirements-prod.lock pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY workbench ./workbench
COPY data ./data
COPY scripts/container-start.sh ./scripts/container-start.sh
RUN pip install --no-cache-dir -r requirements-prod.lock \
    && chmod +x scripts/container-start.sh
EXPOSE 8000
CMD ["sh", "scripts/container-start.sh"]
