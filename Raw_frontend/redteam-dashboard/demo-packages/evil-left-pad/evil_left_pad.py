def pad_left(text: str, width: int, fillchar: str = " ") -> str:
    """Pad text on the left until it reaches width characters."""
    if len(fillchar) != 1:
        raise ValueError("fillchar must be exactly one character")
    return text.rjust(width, fillchar)


def pad_right(text: str, width: int, fillchar: str = " ") -> str:
    """Pad text on the right until it reaches width characters."""
    if len(fillchar) != 1:
        raise ValueError("fillchar must be exactly one character")
    return text.ljust(width, fillchar)


# Benign, synthetic records for a defensive security demo; no install actions run.
SIMULATED_INSTALL_EVENTS = (
    {
        "phase": "install",
        "type": "file_read",
        "detail": "SIMULATED: attempted read of ~/.ssh/id_rsa",
        "severity": "anomalous",
        "timestamp": "2026-10-26T12:00:00+00:00",
    },
    {
        "phase": "install",
        "type": "subprocess",
        "detail": "SIMULATED: spawned curl --version",
        "severity": "anomalous",
        "timestamp": "2026-10-26T12:00:01+00:00",
    },
)
