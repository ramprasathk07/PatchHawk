def parse_logs(log_lines):
    """Parse simple log lines into level and message."""
    parsed = []
    for line in log_lines:
        parts = line.split(' - ', 1)
        if len(parts) == 2:
            parsed.append({"level": parts[0].strip('[]'), "message": parts[1]})
    return parsed