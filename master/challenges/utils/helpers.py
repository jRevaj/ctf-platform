def get_time_string_from_seconds(seconds: float) -> str:
    """Returns time string in '%dh %dm %ds' format from seconds."""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    seconds = seconds % 60
    return f"{hours}h {minutes}m {seconds}s"
