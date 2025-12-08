"""Per-date business hours overrides.

This module provides the BusinessHoursOverrides class for defining
exceptions to the regular weekly schedule (e.g., holidays with reduced hours,
special events with extended hours).
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Dict, Optional, Tuple, Union
from zoneinfo import ZoneInfo

from bizdurr.utils import parse_date_string, parse_time_string, resolve_timezone


@dataclass
class BusinessHoursOverrides:
    """Per-date overrides for business hours.

    Use this class to define exceptions to the regular weekly schedule,
    such as reduced hours on holidays or extended hours for special events.

    Args:
        overrides: A mapping of dates to business hours for those dates.
            Keys can be date objects or ISO date strings ('YYYY-MM-DD').
            Values are dicts with 'start' and 'end' time strings in 'HH:MM' format.
        timezone: IANA timezone string (e.g., 'America/New_York') or ZoneInfo object.

    Raises:
        TypeError: If overrides is not a dictionary or timezone is invalid type.
        ValueError: If date keys are invalid, time formats are wrong,
            or start time equals end time.

    Example:
        >>> overrides = BusinessHoursOverrides(
        ...     overrides={
        ...         "2025-12-24": {"start": "09:00", "end": "12:00"},  # Christmas Eve
        ...         "2025-12-31": {"start": "09:00", "end": "15:00"},  # New Year's Eve
        ...     },
        ...     timezone="America/New_York"
        ... )
        >>> overrides.get_override_for_date("2025-12-24")
        (datetime.time(9, 0, tzinfo=...), datetime.time(12, 0, tzinfo=...))
    """

    overrides: Dict[Union[str, date], Dict[str, str]]
    timezone: Union[str, ZoneInfo]

    # Internal fields (initialized in __post_init__)
    _tz: ZoneInfo = field(default=None, init=False, repr=False)
    _normalized: Dict[date, Tuple[time, time]] = field(
        default=None, init=False, repr=False
    )

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __post_init__(self):
        """Validate inputs and normalize the overrides."""
        self._validate_overrides_type()
        self._tz = resolve_timezone(self.timezone)
        self._normalized = self._build_normalized_overrides()

    def _validate_overrides_type(self) -> None:
        """Ensure overrides is a dictionary."""
        if not isinstance(self.overrides, dict):
            raise TypeError(
                f"overrides must be a dict, got {type(self.overrides).__name__}."
            )

    def _build_normalized_overrides(self) -> Dict[date, Tuple[time, time]]:
        """Parse and validate all override entries.

        Returns:
            A dictionary mapping date objects to (start_time, end_time) tuples
            with timezone information attached.
        """
        normalized: Dict[date, Tuple[time, time]] = {}

        for date_key, hours_dict in self.overrides.items():
            override_date = self._parse_date_key(date_key)
            start_time, end_time = self._parse_override_hours(date_key, hours_dict)
            normalized[override_date] = (start_time, end_time)

        return normalized

    # -------------------------------------------------------------------------
    # Validation Helpers
    # -------------------------------------------------------------------------

    def _parse_date_key(self, date_key: Union[str, date]) -> date:
        """Parse and validate a date key.

        Args:
            date_key: The date from the overrides dict (string or date object).

        Returns:
            A date object.

        Raises:
            TypeError: If the key is not a string or date.
            ValueError: If the string is not a valid ISO date.
        """
        try:
            return parse_date_string(date_key)
        except (TypeError, ValueError) as e:
            raise type(e)(f"Invalid override date key {date_key!r}: {e}")

    def _parse_override_hours(
        self, date_key: Union[str, date], hours_dict: Dict[str, str]
    ) -> Tuple[time, time]:
        """Parse and validate a single date's override hours.

        Args:
            date_key: The original date key (for error messages).
            hours_dict: Dictionary with 'start' and 'end' time strings.

        Returns:
            A tuple of (start_time, end_time) with timezone info attached.

        Raises:
            TypeError: If hours_dict is not a dictionary.
            ValueError: If required keys are missing, times are invalid,
                or start equals end.
        """
        # Validate structure
        if not isinstance(hours_dict, dict):
            raise TypeError(
                f"overrides[{date_key!r}] must be a dict with 'start' and 'end' keys, "
                f"got {type(hours_dict).__name__}."
            )

        if "start" not in hours_dict or "end" not in hours_dict:
            raise ValueError(
                f"overrides[{date_key!r}] must contain both 'start' and 'end' keys."
            )

        # Parse times and attach timezone
        start_time = self._parse_time_with_context(
            hours_dict["start"], date_key, "start"
        )
        end_time = self._parse_time_with_context(hours_dict["end"], date_key, "end")

        # Validate: no zero-length overrides
        self._validate_non_zero_duration(date_key, start_time, end_time)

        return start_time, end_time

    def _parse_time_with_context(
        self, time_str: str, date_key: Union[str, date], field_name: str
    ) -> time:
        """Parse a time string and attach timezone, with contextual error messages.

        Args:
            time_str: The time string to parse.
            date_key: The date key (for error context).
            field_name: 'start' or 'end' (for error context).

        Returns:
            A time object with timezone info attached.
        """
        try:
            parsed_time = parse_time_string(time_str)
        except ValueError as e:
            raise ValueError(f"overrides[{date_key!r}] {field_name} time error: {e}")

        return parsed_time.replace(tzinfo=self._tz)

    def _validate_non_zero_duration(
        self, date_key: Union[str, date], start_time: time, end_time: time
    ) -> None:
        """Validate that the override has a non-zero duration.

        Args:
            date_key: The date key (for error messages).
            start_time: The override start time.
            end_time: The override end time.

        Raises:
            ValueError: If start equals end time.
        """
        if start_time == end_time:
            raise ValueError(
                f"overrides[{date_key!r}] has identical start and end times "
                f"({start_time.strftime('%H:%M')}). "
                "Override hours must have a non-zero duration. "
                "To mark a date as closed, exclude it from overrides and add it to holidays."
            )

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def get_override_for_date(
        self, d: Union[date, datetime, str]
    ) -> Optional[Tuple[time, time]]:
        """Get the override hours for a specific date.

        Args:
            d: The date to look up. Can be a date object, datetime object,
               or ISO date string ('YYYY-MM-DD').

        Returns:
            A tuple of (start_time, end_time) if an override exists for that date,
            or None if no override is defined.

        Example:
            >>> overrides.get_override_for_date("2025-12-24")
            (datetime.time(9, 0, tzinfo=...), datetime.time(12, 0, tzinfo=...))
            >>> overrides.get_override_for_date("2025-12-25")  # No override
            None
        """
        lookup_date = self._normalize_date_lookup(d)
        return self._normalized.get(lookup_date)

    def is_override_for_date(self, d: Union[date, datetime, str]) -> bool:
        """Check if an override exists for a specific date.

        Args:
            d: The date to check. Can be a date object, datetime object,
               or ISO date string ('YYYY-MM-DD').

        Returns:
            True if an override is defined for that date, False otherwise.

        Example:
            >>> overrides.is_override_for_date("2025-12-24")
            True
            >>> overrides.is_override_for_date("2025-12-25")
            False
        """
        return self.get_override_for_date(d) is not None

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _normalize_date_lookup(self, d: Union[date, datetime, str]) -> date:
        """Normalize a date input for lookup.

        Args:
            d: A date, datetime, or ISO date string.

        Returns:
            A date object.
        """
        if isinstance(d, datetime):
            return d.date()
        elif isinstance(d, str):
            return parse_date_string(d)
        return d
