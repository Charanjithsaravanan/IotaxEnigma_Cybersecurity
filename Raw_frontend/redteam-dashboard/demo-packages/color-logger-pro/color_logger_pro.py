ANSI_COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
}
RESET = "\033[0m"


def colorize(text: str, color: str) -> str:
    """Wrap text in an ANSI color code, or return it unchanged for unknown colors."""
    color_code = ANSI_COLORS.get(color.lower())
    if color_code is None:
        return text
    return f"{color_code}{text}{RESET}"


# Synthetic import-phase records; no environment variables or network are accessed.
SIMULATED_IMPORT_EVENTS = (
    {
        "phase": "import",
        "type": "env_read",
        "detail": "SIMULATED: read environment variable AWS_SECRET_ACCESS_KEY",
        "severity": "anomalous",
        "timestamp": "2026-10-26T12:00:02+00:00",
    },
    {
        "phase": "import",
        "type": "network",
        "detail": "SIMULATED: GET https://httpbin.org/get with a synthetic value",
        "severity": "anomalous",
        "timestamp": "2026-10-26T12:00:03+00:00",
    },
)
