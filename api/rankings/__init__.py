"""
Rankings API - Get top 25 team rankings by sport.

GET /rankings/{sport}
"""
import json
import logging
import azure.functions as func

from shared.blob_service import get_blob_service


VALID_SPORTS = ['ncaam_basketball', 'ncaaw_basketball']


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle rankings requests.
    
    GET /rankings/{sport}
    
    Response:
    {
        "sport": "ncaam_basketball",
        "updated_at": "2026-01-25T12:00:00Z",
        "rankings": [
            { "rank": 1, "team": "kansas", "rating": 94.13 },
            { "rank": 2, "team": "auburn", "rating": 93.87 },
            ...
        ]
    }
    """
    logging.info('GET /rankings')
    
    try:
        blob_service = get_blob_service()
        sport = req.route_params.get('sport', 'ncaam_basketball').lower()
        
        if sport not in VALID_SPORTS:
            return func.HttpResponse(
                json.dumps({"error": {"code": "invalid_sport", "message": f"sport must be one of: {', '.join(VALID_SPORTS)}"}}),
                mimetype="application/json",
                status_code=400
            )
        
        is_womens = sport == 'ncaaw_basketball'
        data, last_modified = blob_service.get_top25(is_womens)
        
        # Transform { team: rating } dict to ranked array
        sorted_teams = sorted(data.items(), key=lambda x: x[1], reverse=True)
        rankings = [
            {"rank": i + 1, "team": team, "rating": round(rating, 2)}
            for i, (team, rating) in enumerate(sorted_teams)
        ]
        
        response = {
            "sport": sport,
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
