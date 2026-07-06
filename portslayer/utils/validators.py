import re


_PORT_MIN = 1
_PORT_MAX = 65535


def validate_port(value: object) -> tuple[bool, str]:
    """
    Validate that *value* is a usable port number.

    Returns (True, "") on success or (False, reason) on failure.
    The function deliberately accepts strings so callers don't have to
    pre-convert user input.
    """
    if isinstance(value, str):
        if not re.fullmatch(r"\d{1,5}", value.strip()):
            return False, f"'{value}' is not a valid port number (digits only)."
        value = int(value.strip())

    if not isinstance(value, int):
        return False, "Port must be an integer."

    if value < _PORT_MIN or value > _PORT_MAX:
        return (
            False,
            f"Port {value} is out of the valid range "
            f"({_PORT_MIN}–{_PORT_MAX}).",
        )

    return True, ""


def validate_port_prefix(value: str) -> tuple[bool, str]:
    """
    Validate that *value* is usable as a port prefix for partial search
    (e.g. "808" to match 8080/8081/8083). Unlike :func:`validate_port`,
    this does not require the digits to form a value within 1-65535,
    since a prefix like "8" or "80" legitimately isn't a full port itself.
    """
    v = value.strip()
    if not re.fullmatch(r"\d{1,5}", v):
        return False, f"'{value}' is not a valid port or port prefix (1-5 digits)."
    return True, ""
