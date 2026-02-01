import json
import logging
import azure.functions as func

from shared.blob_service import get_blob_service


DEFAULT_LIMIT = 100
MAX_LIMIT = 500


def format_team(team: dict) -> dict:
    """Format team object for API response with id, type, and sports array."""
    sports = []
    if team.get('has_mens_program'):
        sports.append('ncaam_basketball')
    if team.get('has_womens_program'):
        sports.append('ncaaw_basketball')
    
    return {
        'id': team['key'],
        'type': 'team',
        'school': team['school'],
        'name': team['name'],
        'location': team['location'],
        'ncaa_key': team['ncaa_key'],
        'color': team['color'],
        'sports': sports
    }


def main(req: func.HttpRequest) -> func.HttpResponse:
    """
    Handle teams requests.
    
    GET /teams - List teams (paginated)
    GET /teams?sport=ncaam_basketball - Filter to teams with men's programs
    GET /teams?sport=ncaaw_basketball - Filter to teams with women's programs
    GET /teams?limit=50 - Limit results (default: 100, max: 500)
    GET /teams?after_id={id} - Get teams after this ID (forward pagination)
    GET /teams?before_id={id} - Get teams before this ID (backward pagination)
    GET /teams/{id} - Get single team by ID
    
    List Response (cursor pagination):
    {
        "data": [...],
        "first_id": "abilene-christian",
        "last_id": "arizona",
        "has_more": true
    }
    
    Single Team Response:
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
    """
    logging.info('Teams function triggered')
    
    try:
        blob_service = get_blob_service()
        teams_data, _ = blob_service.get_teams()
        
        # Single team lookup - handle first, no query param validation needed
        team_id = req.route_params.get('key')
        if team_id:
            team = next((t for t in teams_data if t['key'] == team_id), None)
            
            if not team:
                return func.HttpResponse(
                    json.dumps({"error": {"code": "team_not_found", "message": f"Team not found: {team_id}"}}),
                    mimetype="application/json",
                    status_code=404
                )
            
            return func.HttpResponse(
                json.dumps(format_team(team)),
                mimetype="application/json",
                status_code=200
            )
        
        # List endpoint - get and validate query parameters
        sport = req.params.get('sport')
        after_id = req.params.get('after_id')
        before_id = req.params.get('before_id')
        limit_param = req.params.get('limit')
        
        valid_sports = ['ncaam_basketball', 'ncaaw_basketball']
        if sport and sport not in valid_sports:
            return func.HttpResponse(
                json.dumps({"error": {"code": "invalid_sport", "message": f"sport must be one of: {', '.join(valid_sports)}"}}),
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
        
        # Apply sport filter (source data uses has_mens/womens_program flags)
        filtered_teams = teams_data
        if sport == 'ncaam_basketball':
            filtered_teams = [t for t in teams_data if t.get('has_mens_program')]
        elif sport == 'ncaaw_basketball':
            filtered_teams = [t for t in teams_data if t.get('has_womens_program')]
        
        # Apply cursor pagination
        start_index = 0
        end_index = len(filtered_teams)
        
        if after_id:
            # Get items after this ID (further in the list)
            for i, team in enumerate(filtered_teams):
                if team['key'] == after_id:
                    start_index = i + 1
                    break
        
        if before_id:
            # Get items before this ID (earlier in the list)
            for i, team in enumerate(filtered_teams):
                if team['key'] == before_id:
                    end_index = i
                    break
        
        # Slice to cursor range, then apply limit
        cursor_filtered = filtered_teams[start_index:end_index]
        
        # For before_id, take from the end; for after_id or no cursor, take from start
        if before_id and not after_id:
            paginated_teams = cursor_filtered[-limit:] if len(cursor_filtered) > limit else cursor_filtered
            has_more = len(cursor_filtered) > limit
        else:
            paginated_teams = cursor_filtered[:limit]
            has_more = len(cursor_filtered) > limit
        
        # Format teams for response
        formatted_teams = [format_team(t) for t in paginated_teams]
        
        response = {
            'data': formatted_teams,
            'first_id': formatted_teams[0]['id'] if formatted_teams else None,
            'last_id': formatted_teams[-1]['id'] if formatted_teams else None,
            'has_more': has_more
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
