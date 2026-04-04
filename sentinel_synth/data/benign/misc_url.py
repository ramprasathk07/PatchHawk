def parse_url_params(url):
    """Parse query parameters from a URL."""
    if '?' not in url:
        return {}
    query = url.split('?', 1)[1]
    params = {}
    for pair in query.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            params[k] = v
    return params