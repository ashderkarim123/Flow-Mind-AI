# FlowMind AI — FastAPI backend
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Optional: Node.js (npx) and uv (uvx) so the "command" MCP servers from the catalog can run in this container.
# Off by default - it adds ~150 MB. Enable with: docker compose build --build-arg INSTALL_MCP_RUNTIMES=true
ARG INSTALL_MCP_RUNTIMES=false
RUN if [ "$INSTALL_MCP_RUNTIMES" = "true" ]; then \
      apt-get update && apt-get install -y --no-install-recommends nodejs npm \
      && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir uv; \
    fi

# Run as an unprivileged user
RUN useradd --create-home flowmind && chown -R flowmind /app
USER flowmind

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ[\"PORT\"]}/health')" || exit 1

# Same start command as Render (backend/render.yaml)
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
