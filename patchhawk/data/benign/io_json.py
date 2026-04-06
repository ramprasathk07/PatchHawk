import json


def format_json(obj):
    """Format dictionary as readable JSON string."""
    return json.dumps(obj, indent=4, sort_keys=True)
