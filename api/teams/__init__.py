import json
import logging
import azure.functions as func

from shared.blob_service import get_blob_service


DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle teams requests.
    
    GET /teams - List teams (paginated)
    GET /teams?gender=men - Filter to men's programs
    GET /teams?gender=women - Filter to women's programs
    GET /teams?limit=50 - Limit results (default: 100, max: 500)
    GET /teams?after={key} - Cursor for next page
    GET /teams/{key} - Get single team by key
    
    List Response (OpenAI-style pagination):
    {
        "data": [...],
        "first_id": "abilene-christian",
        "last_id": "arizona",
        "has_more": true,
        "updated_at": "2026-01-25T12:00:00Z"
    }
    
    Single Team Response:
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
    """
    logging.info('Teams function triggered')
    
    try:
        blob_service = get_blob_service()
        teams_data, last_modified = blob_service.get_teams()
        
        # Single team lookup - handle first, no query param validation needed
        team_key = req.route_params.get('key')
        if team_key:
            team = next((t for t in teams_data if t['key'] == team_key), None)
            
            if not team:
                return func.HttpResponse(
                    json.dumps({"error": {"code": "team_not_found", "message": f"Team not found: {team_key}"}}),
                    mimetype="application/json",
                    status_code=404
                )
            
            return func.HttpResponse(
                json.dumps(team),
                mimetype="application/json",
                status_code=200
            )
        
        # List endpoint - get and validate query parameters
        gender = req.params.get('gender')
        after = req.params.get('after')
        limit_param = req.params.get('limit')
        
        if gender and gender not in ['men', 'women']:
            return func.HttpResponse(
                json.dumps({"error": {"code": "invalid_gender", "message": "gender must be 'men' or 'women'"}}),
                mimetype="application/json",
                status_code=400
            )
        
        # Parse and validate limit
        try:
            limit = int(limit_param) if limit_param else DEFAULT_LIMIT
            if limit < 1:
                limit = DEFAULT_LIMIT
            elif limit > MAX_LIMIT:
                limit = MAX_LIMIT
        except ValueError:
            limit = DEFAULT_LIMIT
        
        # Apply gender filter
        filtered_teams = teams_data
        if gender == 'men':
            filtered_teams = [t for t in teams_data if t.get('has_mens_program')]
        elif gender == 'women':
            filtered_teams = [t for t in teams_data if t.get('has_womens_program')]
        
        # Apply cursor (after)
        start_index = 0
        if after:
            for i, team in enumerate(filtered_teams):
                if team['key'] == after:
                    start_index = i + 1
                    break
        
        # Apply pagination
        paginated_teams = filtered_teams[start_index:start_index + limit]
        has_more = start_index + limit < len(filtered_teams)
        
        response = {
            'data': paginated_teams,
            'first_id': paginated_teams[0]['key'] if paginated_teams else None,
            'last_id': paginated_teams[-1]['key'] if paginated_teams else None,
            'has_more': has_more,
            'updated_at': last_modified
        }
        
        return func.HttpResponse(
            json.dumps(response),
            mimetype="application/json",
            status_code=200
        )
    
    except Exception as e:
        logging.error(f"Teams error: {e}")
        return func.HttpResponse(
            json.dumps({"error": {"code": "internal_error", "message": "Internal server error"}}),
            mimetype="application/json",
            status_code=500
        )
