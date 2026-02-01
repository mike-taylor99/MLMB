"""
Shared pagination utilities.

Provides consistent cursor-based pagination across all list endpoints.
"""
from typing import Any, Dict, List, Optional


def build_list_response(
    items: List[Dict[str, Any]],
    limit: int,
    id_field: str = 'id'
) -> Dict[str, Any]:
    """
    Build a standard list response with cursor pagination.
    
    Args:
        items: List of items (should contain limit + 1 items if there are more)
        limit: The requested limit
        id_field: The field name to use for first_id/last_id (default: 'id')
        
    Returns:
        Dict with structure:
        {
            "data": [...],
            "has_more": bool,
            "first_id": str | None,
            "last_id": str | None
        }
    """
    # Determine if there are more results
    has_more = len(items) > limit
    if has_more:
        items = items[:limit]  # Remove the extra item
    
    return {
        "data": items,
        "has_more": has_more,
        "first_id": items[0][id_field] if items else None,
        "last_id": items[-1][id_field] if items else None
    }


def parse_pagination_params(
    params: Dict[str, str],
    default_limit: int = 20,
    max_limit: int = 100
) -> Dict[str, Any]:
    """
    Parse pagination parameters from request query params.
    
    Args:
        params: Request query parameters dict
        default_limit: Default limit if not specified (default: 20)
        max_limit: Maximum allowed limit (default: 100)
        
    Returns:
        Dict with:
        {
            "limit": int,
            "before_id": str | None,
            "after_id": str | None
        }
    """
    # Parse limit
    try:
        limit = min(int(params.get('limit', default_limit)), max_limit)
    except (ValueError, TypeError):
        limit = default_limit
    
    return {
        "limit": limit,
        "before_id": params.get('before_id'),
        "after_id": params.get('after_id')
    }
