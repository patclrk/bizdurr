"""Business hours schedule management.

This module provides the BusinessHours class for defining weekly business
schedules with timezone support.
"""

import calendar
from dataclasses import dataclass, field
from datetime import datetime, time
from typing import Dict, Optional, Tuple
from zoneinfo import ZoneInfo

from bizdurr.utils import parse_time_string, resolve_timezone

# Valid weekday names (lowercase) from the calendar module
VALID_WEEKDAYS = frozenset(day.lower() for day in calendar.day_name if day)

# Standard weekdays for shorthand schedule expansion (Monday-Friday)
WEEKDAYS_MON_FRI = ("monday", "tuesday", "wednesday", "thursday", "friday")


@dataclass
class BusinessHours:
    """Represents weekly business hours for an organization.

    This class defines when a business is open during a typical week,
    with full timezone support for accurate time comparisons.

    Args:
        schedule: Business hours definition. Can be either:
            - A mapping of weekday names to business hours, where keys are
              case-insensitive weekday names ('monday', 'Tuesday', etc.) and
              values are dicts with 'start' and 'end' time strings in 'HH:MM' format.
            - A shorthand dict with just 'start' and 'end' keys, which will be
              expanded to Monday-Friday with the same hours.
        timezone: IANA timezone string (e.g., 'America/New_York') or ZoneInfo object.

    Raises:
        TypeError: If schedule is not a dictionary or timezone is invalid type.
        ValueError: If schedule contains invalid weekday names, time formats,
            or if start time equals or exceeds end time.

    Example:
        >>> # Full schedule
        >>> hours = BusinessHours(
        ...     schedule={
        ...         "monday": {"start": "09:00", "end": "17:00"},
        ...         "tuesday": {"start": "09:00", "end": "17:00"},
        ...         "wednesday": {"start": "09:00", "end": "17:00"},
        ...         "thursday": {"start": "09:00", "end": "17:00"},
        ...         "friday": {"start": "09:00", "end": "17:00"},
        ...     },
        ...     timezone="America/New_York"
        ... )

        >>> # Shorthand for Monday-Friday with same hours
        >>> hours = BusinessHours(
        ...     schedule={"start": "09:00", "end": "17:00"},
        ...     timezone="America/New_York"
        ... )
        >>> hours.get_day_hours("monday")
        (datetime.time(9, 0, tzinfo=ZoneInfo('America/New_York')),
         datetime.time(17, 0, tzinfo=ZoneInfo('America/New_York')))
    """

    schedule: Dict[str, Dict[str, str]]
    timezone: ZoneInfo

    # Internal fields (initialized in __post_init__)
    _tz: ZoneInfo = field(default=None, init=False, repr=False)
    _normalized: Dict[str, Tuple[time, time]] = field(
        default=None, init=False, repr=False
    )

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __post_init__(self):
        """Validate inputs and normalize the schedule."""
        self._validate_schedule_type()
        self.schedule = self._expand_shorthand_schedule(self.schedule)
        self._tz = resolve_timezone(self.timezone)
        self._normalized = self._build_normalized_schedule()

    def _validate_schedule_type(self) -> None:
        """Ensure schedule is a dictionary."""
        if not isinstance(self.schedule, dict):
            raise TypeError(
                f"schedule must be a dict, got {type(self.schedule).__name__}."
            )

    def _expand_shorthand_schedule(self, schedule: Dict) -> Dict[str, Dict[str, str]]:
        """Expand shorthand schedule to full Monday-Friday schedule.

        If the schedule contains only 'start' and 'end' keys (no weekday names),
        assume the user means a full Monday-Friday schedule with the same hours each day.

        Args:
            schedule: The input schedule dict.

        Returns:
            Either the original schedule (if already in full format) or
            an expanded Monday-Friday schedule.

        Example:
            >>> self._expand_shorthand_schedule({"start": "09:00", "end": "17:00"})
            {
                "monday": {"start": "09:00", "end": "17:00"},
                "tuesday": {"start": "09:00", "end": "17:00"},
                ...
            }
        """
        # Check if this is a shorthand schedule (only 'start' and 'end' keys)
        schedule_keys = set(schedule.keys())
        if schedule_keys == {"start", "end"}:
            # Expand to Monday-Friday
            hours_dict = {"start": schedule["start"], "end": schedule["end"]}
            return {day: hours_dict.copy() for day in WEEKDAYS_MON_FRI}

        # Not shorthand, return as-is
        return schedule

    def _build_normalized_schedule(self) -> Dict[str, Tuple[time, time]]:
        """Parse and validate all schedule entries.

        Returns:
            A dictionary mapping lowercase weekday names to (start_time, end_time) tuples
            with timezone information attached.
        """
        normalized: Dict[str, Tuple[time, time]] = {}

        for day_key, hours_dict in self.schedule.items():
            day_name = self._validate_weekday_key(day_key)
            start_time, end_time = self._parse_day_hours(day_name, hours_dict)
            normalized[day_name] = (start_time, end_time)

        return normalized

    # -------------------------------------------------------------------------
    # Validation Helpers
    # -------------------------------------------------------------------------

    def _validate_weekday_key(self, day_key: str) -> str:
        """Validate and normalize a weekday key.

        Args:
            day_key: The weekday name from the schedule.

        Returns:
            The lowercase, stripped weekday name.

        Raises:
            TypeError: If the key is not a string.
            ValueError: If the key is not a valid weekday name.
        """
        if not isinstance(day_key, str):
            raise TypeError(
                f"Schedule keys must be weekday name strings, got {type(day_key).__name__}."
            )

        day_name = day_key.strip().lower()

        if day_name not in VALID_WEEKDAYS:
            raise ValueError(
                f"Invalid weekday name: {day_key!r}. "
                f"Valid names are: {', '.join(sorted(VALID_WEEKDAYS))}."
            )

        return day_name

    def _parse_day_hours(
        self, day_name: str, hours_dict: Dict[str, str]
    ) -> Tuple[time, time]:
        """Parse and validate a single day's hours entry.

        Args:
            day_name: The normalized weekday name (for error messages).
            hours_dict: Dictionary with 'start' and 'end' time strings.

        Returns:
            A tuple of (start_time, end_time) with timezone info attached.

        Raises:
            TypeError: If hours_dict is not a dictionary.
            ValueError: If required keys are missing, times are invalid,
                or start >= end.
        """
        # Validate structure
        if not isinstance(hours_dict, dict):
            raise TypeError(
                f"schedule[{day_name!r}] must be a dict with 'start' and 'end' keys, "
                f"got {type(hours_dict).__name__}."
            )

        if "start" not in hours_dict or "end" not in hours_dict:
            raise ValueError(
                f"schedule[{day_name!r}] must contain both 'start' and 'end' keys."
            )

        # Parse times and attach timezone
        start_time = self._parse_time_with_context(
            hours_dict["start"], day_name, "start"
        )
        end_time = self._parse_time_with_context(hours_dict["end"], day_name, "end")

        # Validate time ordering
        self._validate_time_ordering(day_name, start_time, end_time)

        return start_time, end_time

    def _parse_time_with_context(
        self, time_str: str, day_name: str, field_name: str
    ) -> time:
        """Parse a time string and attach timezone, with contextual error messages.

        Args:
            time_str: The time string to parse.
            day_name: The weekday name (for error context).
            field_name: 'start' or 'end' (for error context).

        Returns:
            A time object with timezone info attached.
        """
        try:
            parsed_time = parse_time_string(time_str)
        except ValueError as e:
            raise ValueError(f"schedule[{day_name!r}] {field_name} time error: {e}")

        return parsed_time.replace(tzinfo=self._tz)

    def _validate_time_ordering(
        self, day_name: str, start_time: time, end_time: time
    ) -> None:
        """Validate that start time is before end time.

        Args:
            day_name: The weekday name (for error messages).
            start_time: The business day start time.
            end_time: The business day end time.

        Raises:
            ValueError: If start equals or exceeds end time.
        """
        if start_time == end_time:
            raise ValueError(
                f"schedule[{day_name!r}] has identical start and end times "
                f"({start_time.strftime('%H:%M')}). "
                "Business hours must have a non-zero duration."
            )

        if start_time > end_time:
            raise ValueError(
                f"schedule[{day_name!r}] has start time ({start_time.strftime('%H:%M')}) "
                f"after end time ({end_time.strftime('%H:%M')}). "
                "Overnight schedules are not currently supported."
            )

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def get_day_hours(self, day: str) -> Optional[Tuple[time, time]]:
        """Get the business hours for a specific weekday.

        Args:
            day: Weekday name (case-insensitive), e.g., 'Monday' or 'monday'.

        Returns:
            A tuple of (start_time, end_time) if the day has defined hours,
            or None if the business is closed that day.

        Example:
            >>> hours.get_day_hours("Monday")
            (datetime.time(9, 0, tzinfo=...), datetime.time(17, 0, tzinfo=...))
            >>> hours.get_day_hours("Sunday")  # Not in schedule
            None
        """
        return self._normalized.get(day.strip().lower())

    def is_within_business_hours(self, dt: datetime) -> bool:
        """Check if a datetime falls within business hours.

        For naive datetimes (no timezone info), the datetime is assumed to be
        in the schedule's timezone. For aware datetimes, the time is converted
        to the schedule's timezone before comparison.

        Args:
            dt: The datetime to check.

        Returns:
            True if the datetime is within business hours, False otherwise.
            Returns False for days not defined in the schedule.

        Raises:
            TypeError: If dt is not a datetime object.

        Example:
            >>> from datetime import datetime
            >>> hours.is_within_business_hours(datetime(2025, 12, 8, 10, 30))  # Monday
            True
            >>> hours.is_within_business_hours(datetime(2025, 12, 8, 6, 0))   # Too early
            False
        """
        if not isinstance(dt, datetime):
            raise TypeError(f"Expected datetime, got {type(dt).__name__}.")

        # Convert to schedule timezone
        dt_in_tz = self._to_schedule_timezone(dt)

        # Look up hours for this weekday
        day_name = dt_in_tz.strftime("%A").lower()
        hours = self._normalized.get(day_name)

        if hours is None:
            return False

        start_time, end_time = hours
        current_time = dt_in_tz.timetz()

        # Check if current time is within range [start, end)
        return start_time <= current_time < end_time

    # -------------------------------------------------------------------------
    # Internal Helpers
    # -------------------------------------------------------------------------

    def _to_schedule_timezone(self, dt: datetime) -> datetime:
        """Convert a datetime to the schedule's timezone.

        Args:
            dt: The datetime to convert.

        Returns:
            The datetime in the schedule's timezone.
        """
        if dt.tzinfo is None:
            # Naive datetime: assume it's already in schedule timezone
            return dt.replace(tzinfo=self._tz)
        else:
            # Aware datetime: convert to schedule timezone
            return dt.astimezone(self._tz)
