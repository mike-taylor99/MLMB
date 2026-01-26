# MLMB API (Azure Functions)

This folder contains the serverless API functions for MLMB, designed to run as Azure Functions (Flex Consumption).

## Endpoints

| Endpoint             | Method | Description                     |
| -------------------- | ------ | ------------------------------- |
| `/predictions`       | POST   | Get game predictions            |
| `/rankings/{gender}` | GET    | Get top 25 rankings (men/women) |
| `/teams`             | GET    | List teams (paginated)          |
| `/teams/{key}`       | GET    | Get single team by key          |

## Local Development

### Prerequisites

1. Install [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
2. Python 3.11+

### Setup

```bash
# Create and activate virtual environment
cd api
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Running Locally

```bash
cd api
.\.venv\Scripts\Activate.ps1
func start
```

### Environment Variables

Create `local.settings.json` with:

```json
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "AZURE_STORAGE_CONNECTION_STRING": "<your-connection-string>"
  },
  "Host": {
    "CORS": "*"
  }
}
```

## API Usage

### Predictions Endpoint

```bash
POST /predictions
Content-Type: application/json

{
  "home_team": "duke",
  "away_team": "connecticut",
  "span": 3,              # Optional: 3, 5, or 7 (default: 3)
  "neutral": false,       # Optional: true/false (default: false)
  "gender": "men",        # Optional: "men" or "women" (default: "men")
  "model": "ensemble"     # Optional: see model options below (default: "ensemble")
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

```json
{
  "home_team": "duke",
  "away_team": "connecticut",
  "home_win_probability": 0.5218,
  "home_last_played": "2026-01-17",
  "away_last_played": "2026-01-17",
  "predicted_winner": "duke",
  "neutral": false,
  "span": 3,
  "gender": "men",
  "model": "ensemble"
}
```

### Rankings Endpoint

```bash
GET /rankings/men
GET /rankings/women
```

**Response:**

```json
{
  "gender": "men",
  "updated_at": "2026-01-25T12:00:00Z",
  "rankings": [
    { "rank": 1, "team": "kansas", "rating": 94.13 },
    { "rank": 2, "team": "auburn", "rating": 93.87 },
    ...
  ]
}
```

### Teams Endpoint

List teams with pagination (OpenAI-style cursor pagination):

```bash
GET /teams                    # First 100 teams
GET /teams?limit=50           # First 50 teams
GET /teams?after=duke         # Next page after "duke"
GET /teams?gender=men         # Filter to men's programs
GET /teams?gender=women       # Filter to women's programs
GET /teams/connecticut        # Single team lookup
```

**Query Parameters:**

| Parameter | Type   | Default | Description                    |
| --------- | ------ | ------- | ------------------------------ |
| `limit`   | int    | 100     | Items per page (max: 500)      |
| `after`   | string | —       | Cursor: team key for next page |
| `gender`  | string | —       | Filter: `men` or `women`       |

**List Response:**

```json
{
  "data": [
    {
      "key": "duke",
      "school": "Duke",
      "name": "Duke University",
      "location": "Durham, North Carolina",
      "ncaa_key": "duke",
      "color": "#002D72",
      "has_mens_program": true,
      "has_womens_program": true
    }
  ],
  "first_id": "abilene-christian",
  "last_id": "concordia-seminary",
  "has_more": true,
  "updated_at": "2026-01-25T12:00:00Z"
}
```

**Single Team Response:**

```json
{
  "key": "connecticut",
  "school": "Connecticut",
  "name": "University of Connecticut",
  "location": "Storrs, Connecticut",
  "ncaa_key": "uconn",
  "color": "#0C2340",
  "has_mens_program": true,
  "has_womens_program": true
}
```

### Error Responses

All errors follow a structured format:

```json
{
  "error": {
    "code": "error_code",
    "message": "Human readable message"
  }
}
```

**Error Codes:**

| Code               | HTTP Status | Description                              |
| ------------------ | ----------- | ---------------------------------------- |
| `missing_teams`    | 400         | home_team and away_team are required     |
| `invalid_span`     | 400         | span must be 3, 5, or 7                  |
| `invalid_gender`   | 400         | gender must be 'men' or 'women'          |
| `invalid_model`    | 400         | model must be one of the valid options   |
| `team_not_found`   | 404         | Team key not found in /teams/{key}       |
| `validation_error` | 400         | Team not found or other validation error |
| `internal_error`   | 500         | Internal server error                    |

## Deployment

This API deploys automatically with the Static Web App when you push to the `master` branch.
