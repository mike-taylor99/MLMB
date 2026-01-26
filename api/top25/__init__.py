import json
import logging
import azure.functions as func

from shared.blob_service import get_blob_service


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle rankings requests.
    
    GET /rankings/{gender}
    
    Response:
    {
        "gender": "men",
        "updated_at": "2026-01-25T12:00:00Z",
        "rankings": [
            { "rank": 1, "team": "kansas", "rating": 94.13 },
            { "rank": 2, "team": "auburn", "rating": 93.87 },
            ...
        ]
    }
    """
    logging.info('Rankings function triggered')
    
    try:
        blob_service = get_blob_service()
        gender = req.route_params.get('gender', 'men').lower()
        
        if gender not in ['men', 'women']:
            return func.HttpResponse(
                json.dumps({"error": {"code": "invalid_gender", "message": "gender must be 'men' or 'women'"}}),
                mimetype="application/json",
                status_code=400
            )
        
        is_womens = gender == 'women'
        data, last_modified = blob_service.get_top25(is_womens)
        
        # Transform { team: rating } dict to ranked array
        sorted_teams = sorted(data.items(), key=lambda x: x[1], reverse=True)
        rankings = [
            {"rank": i + 1, "team": team, "rating": round(rating, 2)}
            for i, (team, rating) in enumerate(sorted_teams)
        ]
        
        response = {
            "gender": gender,
            "updated_at": last_modified,
            "rankings": rankings
        }
        
        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            status_code=200
        )
    
    except Exception as e:
        logging.error(f"Rankings error: {e}")
        return func.HttpResponse(
            json.dumps({"error": {"code": "internal_error", "message": "Failed to retrieve rankings"}}),
            mimetype="application/json",
            status_code=500
        )
