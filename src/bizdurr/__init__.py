"""bizdurr - A lightweight, flexible business duration calculator.

This library provides tools for calculating business hours duration,
accounting for weekly schedules, holidays, and per-date overrides.

Example:
    >>> from bizdurr import BusinessDuration
    >>> from datetime import datetime
    >>>
    >>> duration = BusinessDuration(
    ...     business_hours={
    ...         "monday": {"start": "09:00", "end": "17:00"},
    ...         "tuesday": {"start": "09:00", "end": "17:00"},
    ...     },
    ...     timezone="America/New_York",
    ... )
    >>> duration.calculate(
    ...     start=datetime(2025, 12, 22, 10, 0),
    ...     end=datetime(2025, 12, 22, 15, 0)
    ... )
    datetime.timedelta(seconds=18000)  # 5 hours
"""

from bizdurr.BusinessDuration import BusinessDuration
from bizdurr.BusinessHours import BusinessHours
from bizdurr.BusinessHoursOverrides import BusinessHoursOverrides

__all__ = [
    "BusinessDuration",
    "BusinessHours",
    "BusinessHoursOverrides",
]

__version__ = "1.0.0"
