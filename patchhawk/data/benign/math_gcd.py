def gcd(a, b):
    """Calculate the Greatest Common Divisor."""
    while b:
        a, b = b, a % b
    return a
