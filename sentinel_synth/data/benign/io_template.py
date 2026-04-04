def render_template(template, context):
    """Simple template rendering replacing {{key}}."""
    result = template
    for key, value in context.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result