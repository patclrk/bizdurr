"""Business duration calculation.

This module provides the BusinessDuration class for calculating how much time
within a given interval falls within defined business hours.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Set, Union
from zoneinfo import ZoneInfo

from bizdurr.BusinessHours import BusinessHours
from bizdurr.BusinessHoursOverrides import BusinessHoursOverrides
from bizdurr.utils import parse_date_string, resolve_timezone


@dataclass
class BusinessDuration:
    """Calculate the duration of time that falls within business hours.

    This class combines a weekly schedule, optional per-date overrides,
    and optional holidays to calculate how much of a time interval
    falls within defined business hours.

    Args:
        business_hours: Weekly schedule as a BusinessHours object or a dict
            mapping weekday names to {'start': 'HH:MM', 'end': 'HH:MM'}.
        timezone: IANA timezone string (e.g., 'America/New_York') or ZoneInfo object.
        holidays: Optional list of dates when the business is closed.
            Can be date objects or ISO date strings ('YYYY-MM-DD').
        overrides: Optional per-date schedule overrides as a BusinessHoursOverrides
            object or a dict mapping dates to {'start': 'HH:MM', 'end': 'HH:MM'}.

    Raises:
        TypeError: If business_hours or overrides are invalid types.
        ValueError: If timezone is invalid or holiday dates are malformed.

    Example:
        >>> duration = BusinessDuration(
        ...     business_hours={
        ...         "monday": {"start": "09:00", "end": "17:00"},
        ...         "tuesday": {"start": "09:00", "end": "17:00"},
        ...     },
        ...     timezone="America/New_York",
        ...     holidays=["2025-12-25"],
        ... )
        >>> duration.calculate(
        ...     start=datetime(2025, 12, 22, 10, 0),
        ...     end=datetime(2025, 12, 22, 15, 0)
        ... )
        datetime.timedelta(seconds=18000)  # 5 hours
    """

    business_hours: Union[BusinessHours, Dict[str, Dict[str, str]]]
    timezone: Union[str, ZoneInfo]
    holidays: Optional[List[Union[date, str]]] = None
    overrides: Optional[Union[BusinessHoursOverrides, Dict[str, Dict[str, str]]]] = None

    # Internal fields (initialized in __post_init__)
    _tz: ZoneInfo = field(default=None, init=False, repr=False)
    _holidays: Set[date] = field(default=None, init=False, repr=False)

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def __post_init__(self):
        """Validate and normalize all inputs."""
        self._tz = resolve_timezone(self.timezone)
        self.timezone = self._tz  # Store as ZoneInfo for consistency

        self._convert_business_hours_if_needed()
        self._convert_overrides_if_needed()
        self._holidays = self._normalize_holidays()

    def _convert_business_hours_if_needed(self) -> None:
        """Convert business_hours dict to BusinessHours object if necessary."""
        if isinstance(self.business_hours, dict):
            self.business_hours = BusinessHours(
                schedule=self.business_hours, timezone=self._tz
            )

    def _convert_overrides_if_needed(self) -> None:
        """Convert overrides dict to BusinessHoursOverrides object if necessary."""
        if isinstance(self.overrides, dict):
            self.overrides = BusinessHoursOverrides(
                overrides=self.overrides, timezone=self._tz
            )

    def _normalize_holidays(self) -> Set[date]:
        """Convert holiday list to a set of date objects.

        Returns:
            A set of date objects representing holidays.

        Raises:
            TypeError: If a holiday entry is not a date or string.
            ValueError: If a holiday string is not a valid ISO date.
        """
        if not self.holidays:
            return set()

        normalized: Set[date] = set()

        for holiday in self.holidays:
            if isinstance(holiday, date) and not isinstance(holiday, datetime):
                normalized.add(holiday)
            elif isinstance(holiday, str):
                try:
                    normalized.add(parse_date_string(holiday))
                except ValueError:
                    raise ValueError(
                        f"Invalid holiday date: {holiday!r}. Expected 'YYYY-MM-DD' format."
                    )
            else:
                raise TypeError(
                    f"Holiday must be a date object or ISO date string, "
                    f"got {type(holiday).__name__}."
                )

        return normalized

    # -------------------------------------------------------------------------
    # Public Methods
    # -------------------------------------------------------------------------

    def calculate(self, start: datetime, end: datetime) -> timedelta:
        """Calculate the business duration between two datetimes.

        Computes the total time that falls within business hours between
        the start and end times, accounting for the weekly schedule,
        per-date overrides, and holidays.

        Args:
            start: The start of the time interval.
            end: The end of the time interval.

        Returns:
            A timedelta representing the total business time.
            Returns timedelta(0) if start >= end.

        Example:
            >>> duration.calculate(
            ...     start=datetime(2025, 12, 22, 10, 0),
            ...     end=datetime(2025, 12, 22, 15, 0)
            ... )
            datetime.timedelta(seconds=18000)  # 5 hours
        """
        if start >= end:
            return timedelta(0)

        # Convert to schedule timezone
        start_dt = self._to_schedule_timezone(start)
        end_dt = self._to_schedule_timezone(end)

        # Sum business time for each day in the range
        total_duration = timedelta(0)
        current_date = start_dt.date()
        last_date = end_dt.date()

        while current_date <= last_date:
            day_duration = self._calculate_day_business_time(
                current_date, start_dt, end_dt
            )
            total_duration += day_duration
            current_date = self._next_day(current_date)

        return total_duration

    def is_within_business_hours(self, dt: datetime) -> bool:
        """Check if a datetime falls within business hours.

        Considers holidays and per-date overrides in addition to
        the regular weekly schedule.

        Args:
            dt: The datetime to check.

        Returns:
            True if the datetime is within business hours, False otherwise.

        Example:
            >>> duration.is_within_business_hours(datetime(2025, 12, 22, 10, 30))
            True
        """
        # Check if it's a holiday
        if self._is_holiday(dt.date()):
            return False

        # Check for per-date override
        if self.overrides:
            override = self.overrides.get_override_for_date(dt)
            if override is not None:
                return self._is_time_in_range(dt, override)

        # Fall back to regular schedule
        return self.business_hours.is_within_business_hours(dt)

    # -------------------------------------------------------------------------
    # Internal Calculation Methods
    # -------------------------------------------------------------------------

    def _calculate_day_business_time(
        self, current_date: date, start_dt: datetime, end_dt: datetime
    ) -> timedelta:
        """Calculate the business time for a single day.

        Args:
            current_date: The date to calculate for.
            start_dt: The overall interval start (timezone-aware).
            end_dt: The overall interval end (timezone-aware).

        Returns:
            The business duration for this day.
        """
        # Skip holidays
        if self._is_holiday(current_date):
            return timedelta(0)

        # Get business hours for this day (override or regular schedule)
        business_interval = self._get_business_interval_for_date(current_date)
        if business_interval is None:
            return timedelta(0)

        biz_start_time, biz_end_time = business_interval

        # Build full datetime objects for the business interval
        biz_start_dt = self._build_datetime(current_date, biz_start_time)
        biz_end_dt = self._build_datetime(current_date, biz_end_time)

        # Calculate overlap between request interval and business interval
        return self._calculate_overlap(start_dt, end_dt, biz_start_dt, biz_end_dt)

    def _get_business_interval_for_date(self, current_date: date):
        """Get the business hours interval for a specific date.

        Checks overrides first, then falls back to the regular weekly schedule.

        Args:
            current_date: The date to look up.

        Returns:
            A tuple of (start_time, end_time) or None if closed.
        """
        # Check for override first
        if self.overrides:
            override = self.overrides.get_override_for_date(current_date)
            if override is not None:
                return override

        # Fall back to weekly schedule
        day_name = self._date_to_weekday_name(current_date)
        return self.business_hours.get_day_hours(day_name)

    def _calculate_overlap(
        self,
        request_start: datetime,
        request_end: datetime,
        business_start: datetime,
        business_end: datetime,
    ) -> timedelta:
        """Calculate the overlap between two time intervals.

        Args:
            request_start: Start of the requested interval.
            request_end: End of the requested interval.
            business_start: Start of the business hours interval.
            business_end: End of the business hours interval.

        Returns:
            The duration of the overlap, or timedelta(0) if no overlap.
        """
        overlap_start = max(request_start, business_start)
        overlap_end = min(request_end, business_end)

        if overlap_end > overlap_start:
            return overlap_end - overlap_start
        return timedelta(0)

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _to_schedule_timezone(self, dt: datetime) -> datetime:
        """Convert a datetime to the schedule's timezone.

        Args:
            dt: The datetime to convert.

        Returns:
            The datetime in the schedule's timezone.
        """
        if dt.tzinfo is None:
            return dt.replace(tzinfo=self._tz)
        return dt.astimezone(self._tz)

    def _is_holiday(self, d: date) -> bool:
        """Check if a date is a holiday.

        Args:
            d: The date to check.

        Returns:
            True if the date is in the holidays set.
        """
        return d in self._holidays

    def _is_time_in_range(self, dt: datetime, time_range) -> bool:
        """Check if a datetime's time is within a given range.

        Args:
            dt: The datetime to check.
            time_range: A tuple of (start_time, end_time).

        Returns:
            True if the time is within the range [start, end).
        """
        start_time, end_time = time_range
        dt_local = self._to_schedule_timezone(dt)
        current_time = dt_local.timetz()
        return start_time <= current_time < end_time

    def _build_datetime(self, d: date, t) -> datetime:
        """Build a datetime from a date and time, preserving timezone.

        Args:
            d: The date.
            t: The time (with tzinfo).

        Returns:
            A timezone-aware datetime.
        """
        return datetime(d.year, d.month, d.day, t.hour, t.minute, tzinfo=t.tzinfo)

    def _date_to_weekday_name(self, d: date) -> str:
        """Get the lowercase weekday name for a date.

        Args:
            d: The date.

        Returns:
            The weekday name in lowercase (e.g., 'monday').
        """
        return datetime(d.year, d.month, d.day).strftime("%A").lower()

    def _next_day(self, d: date) -> date:
        """Get the next day.

        Args:
            d: The current date.

        Returns:
            The next date.
        """
        return (datetime(d.year, d.month, d.day) + timedelta(days=1)).date()
