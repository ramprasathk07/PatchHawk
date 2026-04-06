def parse_csv(csv_content):
    """Parse simple CSV content."""
    lines = csv_content.strip().split("\n")
    if not lines:
        return []
    headers = lines[0].split(",")
    result = []
    for line in lines[1:]:
        values = line.split(",")
        result.append(dict(zip(headers, values)))
    return result
