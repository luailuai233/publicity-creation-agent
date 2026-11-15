FROM python:3.9-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WORKBENCH_ROOT=/app
COPY requirements.txt pyproject.toml alembic.ini ./
COPY alembic ./alembic
COPY workbench ./workbench
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/storage/projects /app/exports /app/test-results /app/.runtime
EXPOSE 8000
CMD ["sh", "-c", "python -m alembic upgrade head && python -m uvicorn workbench.main:app --host 0.0.0.0 --port 8000"]
