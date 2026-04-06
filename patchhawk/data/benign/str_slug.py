def generate_slug(title):
    """Generate a URL-friendly slug."""
    import re

    title = title.lower()
    title = re.sub(r"[^a-z0-9\s-]", "", title)
    return re.sub(r"[\s-]+", "-", title).strip("-")
