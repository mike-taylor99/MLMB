# MLMB API

FastAPI application serving ML predictions for NCAA basketball, deployed on Azure Container Apps.

## Endpoints

| Endpoint             | Method | Description                      |
| -------------------- | ------ | -------------------------------- |
| `/health`            | GET    | Health check                     |
| `/predictions`       | POST   | Create prediction (with caching) |
| `/predictions`       | GET    | Query prediction history         |
| `/predictions/{id}`  | GET    | Get prediction by ID             |
| `/predictions/batch` | POST   | Batch predictions (up to 500)    |
| `/rankings/{sport}`  | GET    | Get top 25 rankings              |
| `/teams`             | GET    | List teams (paginated)           |
| `/teams/{id}`        | GET    | Get single team by ID            |

## Sports

Currently supported sports:

- `ncaam_basketball` - NCAA Men's Basketball
- `ncaaw_basketball` - NCAA Women's Basketball

## Local Development

### Prerequisites

- Python 3.11+
- Docker (optional, for container builds)

### Setup

```bash
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate   # Mac/Linux

pip install -r requirements.txt
```

### Running Locally

```bash
cd api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:create_app --factory --reload --port 8000
```

Or with Docker:

```bash
cd api
docker build -t mlmb-api .
docker run -p 8000:8000 --env-file .env mlmb-api
```

### Environment Variables

Create a `.env` file in the `api/` directory:

```
AZURE_STORAGE_CONNECTION_STRING=<your-connection-string>
COSMOS_CONNECTION_STRING=<your-cosmos-connection-string>
```

## API Usage

### Predictions Endpoint

**Create Prediction (POST):**

```bash
POST /predictions
Content-Type: application/json

{
  "home_team": "duke",
  "away_team": "connecticut",
  "span": 3,                          # Optional: 3, 5, or 7 (default: 3)
  "neutral": false,                   # Optional: true/false (default: false)
  "sport": "ncaam_basketball",        # Optional: see sports above (default: "ncaam_basketball")
  "model": "ensemble"                 # Optional: see model options below (default: "ensemble")
}
```

**Model Options:**

- `ensemble` - Ensemble of all models (recommended)
- `logistic_regression`
- `knn` - K-Nearest Neighbors
- `random_forest`
- `gradient_boosting`
- `mlp` - Neural Network (Multilayer Perceptron)
- `svm` - Support Vector Machine

**Response:**

Predictions are cached using content-hash based IDs. Identical requests return the same `id` instantly.

```json
{
  "id": "pred_a3f2b8c1d4e5f6a7b8c9d0e1f2a3b4c5",
  "type": "prediction",
  "model": "ensemble",
  "span": 3,
  "sport": "ncaam_basketball",
  "home_team": "duke",
  "away_team": "connecticut",
  "home_last_played": "2026-01-28",
  "away_last_played": "2026-01-27",
  "neutral": false,
  "home_win_probability": 0.5218,
  "created_at": "2026-01-30T12:00:00Z"
}
```

**Get Prediction by ID:**

```bash
GET /predictions/pred_a3f2b8c1d4e5f6a7b8c9d0e1f2a3b4c5?sport=ncaam_basketball
```

**Query Prediction History:**

```bash
GET /predictions?sport=ncaam_basketball&home_team=duke&limit=20
```

**Query Parameters:**

| Parameter    | Type   | Required | Description                       |
| ------------ | ------ | -------- | --------------------------------- |
| `sport`      | string | Yes      | Sport code (partition key)        |
| `home_team`  | string | No       | Filter by home team               |
| `away_team`  | string | No       | Filter by away team               |
| `start_date` | string | No       | Filter after date (ISO format)    |
| `end_date`   | string | No       | Filter before date (ISO format)   |
| `limit`      | int    | No       | Max results (default 20, max 100) |
| `before_id`  | string | No       | Cursor: get items before this ID  |
| `after_id`   | string | No       | Cursor: get items after this ID   |

**History Response:**

```json
{
  "data": [...],
  "has_more": true,
  "first_id": "pred_abc123...",
  "last_id": "pred_xyz789..."
}
```

### Batch Endpoint

High-performance batch predictions for generating rankings or bulk processing. Models are loaded once and reused for all predictions.

**Request (POST):**

```bash
POST /predictions/batch
Content-Type: application/json

{
  "input": [
    {
      "home_team": "duke",
      "away_team": "connecticut",
      "span": 3,                          # Optional: 3, 5, or 7 (default: 3)
      "neutral": false,                   # Optional: true/false (default: false)
      "sport": "ncaam_basketball",        # Optional: see sports above (default: "ncaam_basketball")
      "model": "ensemble"                 # Optional: see model options below (default: "ensemble")
    },
    {
      "home_team": "kansas",
      "away_team": "kentucky",
      "span": 5,
      "sport": "ncaam_basketball"
    }
  ]
}
```

**Response:**

Results are returned in the same order as the input array. Failed predictions include an `error` field instead of the full response.

```json
{
  "type": "prediction_batch",
  "output": [
    {
      "id": "pred_a3f2b8c1d4e5f6a7b8c9d0e1f2a3b4c5",
      "type": "prediction",
      "model": "ensemble",
      "span": 3,
      "sport": "ncaam_basketball",
      "home_team": "duke",
      "away_team": "connecticut",
      "home_last_played": "2026-01-28",
      "away_last_played": "2026-01-27",
      "neutral": false,
      "home_win_probability": 0.5218,
      "created_at": "2026-01-30T12:00:00Z"
    },
    {
      "id": "pred_b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9",
      "type": "prediction",
      "model": "ensemble",
      "span": 5,
      "sport": "ncaam_basketball",
      "home_team": "kansas",
      "away_team": "kentucky",
      "home_last_played": "2026-01-29",
      "away_last_played": "2026-01-28",
      "neutral": false,
      "home_win_probability": 0.6413,
      "created_at": "2026-01-30T12:00:00Z"
    }
  ]
}
```

**Error Response (per-prediction):**

```json
{
  "type": "error",
  "error": {
    "code": "validation_error",
    "message": "Stats not found for team: invalid-team"
  }
}
```

**Limits:**

- Maximum batch size: 500 predictions per request
- Results are stored in Cosmos DB (skips existing records)

### Rankings Endpoint

```bash
GET /rankings/ncaam_basketball
GET /rankings/ncaaw_basketball
```

**Response:**

```json
{
  "sport": "ncaam_basketball",
  "updated_at": "2026-01-25T12:00:00Z",
  "rankings": [
    { "rank": 1, "team": "kansas", "rating": 94.13 },
    { "rank": 2, "team": "auburn", "rating": 93.87 },
    ...
  ]
}
```

### Teams Endpoint

List teams with cursor pagination:

```bash
GET /teams                                  # First 100 teams
GET /teams?limit=50                         # First 50 teams
GET /teams?after_id=duke                    # Next page after "duke"
GET /teams?before_id=duke                   # Previous page before "duke"
GET /teams?sport=ncaam_basketball           # Filter to men's programs
GET /teams?sport=ncaaw_basketball           # Filter to women's programs
GET /teams/connecticut                      # Single team lookup
```

**Query Parameters:**

| Parameter   | Type   | Default | Description                                      |
| ----------- | ------ | ------- | ------------------------------------------------ |
| `limit`     | int    | 100     | Items per page (max: 500)                        |
| `after_id`  | string | —       | Get teams after this ID (forward pagination)     |
| `before_id` | string | —       | Get teams before this ID (backward pagination)   |
| `sport`     | string | —       | Filter: `ncaam_basketball` or `ncaaw_basketball` |

**List Response:**

```json
{
  "data": [
    {
      "id": "duke",
      "type": "team",
      "school": "Duke",
      "name": "Duke University",
      "location": "Durham, North Carolina",
      "ncaa_key": "duke",
      "color": "#002D72",
      "sports": ["ncaam_basketball", "ncaaw_basketball"]
    }
  ],
  "first_id": "abilene-christian",
  "last_id": "concordia-seminary",
  "has_more": true
}
```

**Single Team Response:**

```json
{
  "id": "connecticut",
  "type": "team",
  "school": "Connecticut",
  "name": "University of Connecticut",
  "location": "Storrs, Connecticut",
  "ncaa_key": "uconn",
  "color": "#0C2340",
  "sports": ["ncaam_basketball", "ncaaw_basketball"]
}
```

### Error Responses

All errors follow a structured format:

```json
{
  "type": "error",
  "error": {
    "code": "error_code",
    "message": "Human readable message"
  }
}
```

**Error Codes:**

| Code               | HTTP Status | Description                      |
| ------------------ | ----------- | -------------------------------- |
| `validation_error` | 400/422     | Invalid input or team not found  |
| `invalid_sport`    | 400         | sport must be a valid sport code |
| `batch_too_large`  | 400         | Batch exceeds 500 predictions    |
| `not_found`        | 404         | Resource not found               |
| `internal_error`   | 500         | Internal server error            |

### Request Tracing

All responses include an `X-Request-ID` header for debugging:

```bash
# Auto-generated
curl -i http://localhost:8000/health
# Response header: X-Request-ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Pass your own for distributed tracing
curl -H "X-Request-ID: my-trace-123" http://localhost:8000/health
# Response header: X-Request-ID: my-trace-123
```

### OpenAPI Documentation

Interactive API docs available at:

- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`

## Architecture

### Model Versioning

Models are tracked via `models_manifest.json` in blob storage:

- Each model has version history with `current` pointer
- Enables rollback, A/B testing, and training lineage
- Model versions are included in prediction IDs for traceability

### Prediction Caching

Predictions use content-hash based IDs:

- `pred_{SHA256(inputs + model_version + stats_version)}`
- Identical requests = identical IDs = automatic deduplication
- Cache lookup is O(1) via Cosmos DB point read (~10ms)

### Feature Schema

Features are defined in `feature_schema.json`:

- Ensures training/inference alignment
- Named DataFrames eliminate sklearn warnings
- Schema version tracked in manifest

## Deployment

The API deploys automatically to Azure Container Apps when you push to the `master` branch (via `.github/workflows/deploy-api.yml`).

The workflow builds a Docker image, pushes it to Azure Container Registry, and updates the Container App.
