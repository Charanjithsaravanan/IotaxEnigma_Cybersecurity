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
