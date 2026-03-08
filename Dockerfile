# =============================================================================
# Production image — API + Pipelines
# Used by: Container App (mlmb-api), Container Apps Jobs (team-stats, top25)
# =============================================================================

FROM python:3.11-slim

# Install system deps needed by lxml
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libxml2-dev libxslt1-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    rm /tmp/requirements.txt

# Copy application code
COPY api/ /app/api/
COPY pipelines/ /app/pipelines/
COPY data/mens_teams.csv /app/data/mens_teams.csv
COPY data/womens_teams.csv /app/data/womens_teams.csv
COPY data/tournaments/ /app/data/tournaments/

# Default: run the API
# Pipeline jobs override this command at the Container Apps Job level
WORKDIR /app/api
EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
