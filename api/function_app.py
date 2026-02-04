"""
MLMB API - Azure Functions entry point.

This wraps the FastAPI application with Azure Functions' ASGI adapter
for serverless deployment.
"""

import azure.functions as func

from app.main import create_app


# Create the FastAPI app
app = create_app()

# Wrap with Azure Functions ASGI adapter
function_app = func.AsgiFunctionApp(
    app=app,
    http_auth_level=func.AuthLevel.ANONYMOUS
)
