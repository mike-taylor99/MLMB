import json
import logging
import os
import azure.functions as func
from azure.storage.blob import BlobServiceClient

# Cache for top 25 data
_top25_cache = {
    'mens': None,
    'womens': None
}

def get_blob_service_client():
    """Get Azure Blob Storage client."""
    conn_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    return BlobServiceClient.from_connection_string(conn_str)

def load_top25(is_womens: bool = False) -> dict:
    """Load top 25 data from Blob Storage with caching."""
    cache_key = 'womens' if is_womens else 'mens'
    
    if _top25_cache[cache_key] is not None:
        return _top25_cache[cache_key]
    
    try:
        blob_service = get_blob_service_client()
        container_name = 'mlmb-api'
        blob_name = 'womens-top25' if is_womens else 'top25'
        
        blob_client = blob_service.get_blob_client(container=container_name, blob=blob_name)
        blob_data = blob_client.download_blob().readall()
        
        data = json.loads(blob_data.decode())
        _top25_cache[cache_key] = data
        
        return data
    except Exception as e:
        logging.error(f"Failed to load top 25 data: {e}")
        raise

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Top 25 function triggered')
    
    try:
        gender = req.route_params.get('gender', 'men').lower()
        
        if gender not in ['men', 'women']:
            return func.HttpResponse(
                json.dumps({"error": "Invalid gender. Use 'men' or 'women'."}),
                mimetype="application/json",
                status_code=400
            )
        
        is_womens = gender == 'women'
        data = load_top25(is_womens)
        
        return func.HttpResponse(
            json.dumps(data),
            mimetype="application/json",
            status_code=200
        )
    
    except Exception as e:
        logging.error(f"Top 25 error: {e}")
        return func.HttpResponse(
            json.dumps({"error": "Failed to retrieve top 25 data"}),
            mimetype="application/json",
            status_code=500
        )
