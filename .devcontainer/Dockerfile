# =============================================================================
# Dev container image
# Same production deps + dev tools. Code is volume-mounted by VS Code.
# =============================================================================

FROM python:3.11-slim

# Install system deps (lxml build deps + git for VS Code + libicu for Azure MCP)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc libxml2-dev libxslt1-dev \
        git curl libicu-dev && \
    rm -rf /var/lib/apt/lists/*

# Install production dependencies (same versions as prod image)
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Install dev-only tools
RUN pip install --no-cache-dir \
    pytest==8.0.0 \
    httpx==0.26.0 \
    ruff==0.2.0 \
    ipykernel==6.29.3

WORKDIR /workspace
