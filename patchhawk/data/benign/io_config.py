def read_ini_config(content):
    """Read a simple INI configuration."""
    config = {}
    current_section = None
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            config[current_section] = {}
        elif '=' in line and current_section:
            key, val = line.split('=', 1)
            config[current_section][key.strip()] = val.strip()
    return config