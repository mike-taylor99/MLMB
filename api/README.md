# MLMB API (Azure Static Web Apps Functions)

This folder contains the serverless API functions for MLMB, designed to run as Azure Static Web Apps managed functions.

## Endpoints

| Endpoint              | Method | Description                     |
| --------------------- | ------ | ------------------------------- |
| `/api/predict`        | POST   | Get game predictions            |
| `/api/top25/{gender}` | GET    | Get top 25 rankings (men/women) |

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
  }
}
```

## API Usage

### Predict Endpoint

```bash
POST /api/predict
Content-Type: application/json

[
  {
    "model": "3span_ensemble",   # or "5span_ensemble", "7span_ensemble"
    "isNeutral": true,
    "isWomens": false,
    "team1": "connecticut",       # team slug
    "team2": "duke"               # team slug
  }
]
```

**Response:**

```json
[
  {
    "model": "3span_ensemble",
    "isNeutral": true,
    "isWomens": false,
    "team1": "connecticut",
    "team2": "duke",
    "predict": [1],
    "predictProba": [0.35, 0.65],
    "team1LastPlayed": "2026-01-15",
    "team2LastPlayed": "2026-01-14"
  }
]
```

### Top 25 Endpoint

```bash
GET /api/top25/mens
GET /api/top25/womens
```

## Deployment

This API deploys automatically with the Static Web App when you push to the `master` branch.
