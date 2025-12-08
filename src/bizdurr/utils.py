"""Shared utility functions for the bizdurr library."""

from datetime import date, time, datetime
from typing import Union
from zoneinfo import ZoneInfo
from zoneinfo._common import ZoneInfoNotFoundError


def parse_time_string(time_str: str) -> time:
    """Parse a time string in 'HH:MM' format into a datetime.time object.

    Args:
        time_str: A string representing time in 24-hour 'HH:MM' format.

    Returns:
        A datetime.time object.

    Raises:
        ValueError: If the string is not in valid 'HH:MM' format.

    Examples:
        >>> parse_time_string("09:30")
        datetime.time(9, 30)
        >>> parse_time_string("17:00")
        datetime.time(17, 0)
    """
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(
            f"Invalid time string: {time_str!r}. Expected 'HH:MM' format (e.g., '09:00')."
        )

    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        raise ValueError(
            f"Invalid time string: {time_str!r}. Hour and minute must be integers."
        )

    if not (0 <= hour <= 23):
        raise ValueError(
            f"Invalid hour in time string: {time_str!r}. Hour must be 0-23."
        )
    if not (0 <= minute <= 59):
        raise ValueError(
            f"Invalid minute in time string: {time_str!r}. Minute must be 0-59."
        )

    return time(hour=hour, minute=minute)


def parse_date_string(date_input: Union[str, date]) -> date:
    """Parse a date string or date object into a datetime.date object.

    Args:
        date_input: Either an ISO date string ('YYYY-MM-DD') or a date object.

    Returns:
        A datetime.date object.

    Raises:
        ValueError: If the string is not a valid ISO date.
        TypeError: If the input is neither a string nor a date object.

    Examples:
        >>> parse_date_string("2025-12-25")
        datetime.date(2025, 12, 25)
        >>> parse_date_string(date(2025, 12, 25))
        datetime.date(2025, 12, 25)
    """
    # Handle date objects (but not datetime, which is a subclass of date)
    if isinstance(date_input, date) and not isinstance(date_input, datetime):
        return date_input

    # Handle ISO date strings
    if isinstance(date_input, str):
        try:
            return date.fromisoformat(date_input)
        except ValueError:
            raise ValueError(
                f"Invalid date string: {date_input!r}. Expected 'YYYY-MM-DD' format."
            )

    raise TypeError(
        f"Expected a date object or ISO date string, got {type(date_input).__name__}."
    )


def resolve_timezone(timezone_input: Union[str, ZoneInfo]) -> ZoneInfo:
    """Convert a timezone string or ZoneInfo object to a ZoneInfo object.

    Args:
        timezone_input: Either an IANA timezone string (e.g., 'America/New_York')
            or a ZoneInfo object.

    Returns:
        A ZoneInfo object.

    Raises:
        TypeError: If the input is neither a string nor a ZoneInfo object.
        ValueError: If the timezone string is not recognized.

    Examples:
        >>> resolve_timezone("UTC")
        zoneinfo.ZoneInfo(key='UTC')
        >>> resolve_timezone("America/New_York")
        zoneinfo.ZoneInfo(key='America/New_York')
    """
    if isinstance(timezone_input, ZoneInfo):
        return timezone_input

    if isinstance(timezone_input, str):
        if not timezone_input.strip():
            raise ValueError("Timezone string cannot be empty.")
        try:
            return ZoneInfo(timezone_input)
        except ZoneInfoNotFoundError:
            raise ValueError(
                f"Unknown timezone: {timezone_input!r}. "
                "Use an IANA timezone name like 'UTC' or 'America/New_York'."
            )

    raise TypeError(
        f"Timezone must be a string or ZoneInfo object, got {type(timezone_input).__name__}."
    )
