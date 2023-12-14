from atopile import errors


class InvalidPhysicalValue(errors.AtoError):
    """Raised when a unit is unprocessable."""


def _strip_unit_letter(s: str) -> str:
    if s.endswith(("R", "F", "r", "f")):
        return s[:-1]
    return s


def parse_number(s: str | float) -> float:
    """Return a float from a string containing a number and a multiplier."""
    if isinstance(s, float):
        return s

    if not s:
        raise InvalidPhysicalValue("Empty string")

    s = _strip_unit_letter(s)

    multipliers = {
        "M": 1E6,
        "k": 1E3,
        "m": 1E-3,
        "u": 1E-6,
        "n": 1E-9,
        "p": 1E-12,
    }

    # Extract the number from the string
    if s[-1].isdigit():
        number_str = s
        multiplier_str = ""
    else:
        number_str = s[:-1]
        multiplier_str = s[-1]

    try:
        number = float(number_str)
    except ValueError as ex:
        raise InvalidPhysicalValue(f"{number_str} is not a valid number") from ex

    # If the string is nothing but numbers, return it as a float
    if not multiplier_str:
        return number

    # Extract the multiplier from the string
    try:
        multiplier = multipliers[multiplier_str]
    except KeyError as ex:
        raise InvalidPhysicalValue(f"{multiplier_str} is not a valid multiplier") from ex

    # Return the number multiplied by the multiplier
    return number * multiplier
