def is_strong_password(pwd):
    """Check if password meets basic strength criteria."""
    if len(pwd) < 8:
        return False
    has_upper = any(c.isupper() for c in pwd)
    has_lower = any(c.islower() for c in pwd)
    has_digit = any(c.isdigit() for c in pwd)
    return has_upper and has_lower and has_digit