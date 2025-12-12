from datetime import datetime, timedelta

import pytest

from bizdurr.BusinessDuration import BusinessDuration
from bizdurr.BusinessHours import BusinessHours
from bizdurr.BusinessHoursOverrides import BusinessHoursOverrides


def test_business_duration_creation():
    wh = {"monday": {"start": "09:30", "end": "17:30"}}
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours=wh,
    )
    assert isinstance(bd.business_hours, BusinessHours)


def test_calculate_within_working_hours():
    wh = {"monday": {"start": "09:00", "end": "17:00"}}
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours=wh,
    )
    start = datetime(2025, 9, 29, 10, 0)
    end = datetime(2025, 9, 29, 12, 0)
    duration = bd.calculate(start, end)
    assert duration == timedelta(hours=2)


def test_calculate_outside_working_hours():
    bh = {"monday": {"start": "09:00", "end": "17:00"}}
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours=bh,
    )
    start = datetime(2025, 9, 29, 7, 0)
    end = datetime(2025, 9, 29, 8, 0)
    duration = bd.calculate(start, end)
    assert duration == timedelta(0)


def test_zero_length_override_raises():
    # zero-length override (start == end) is invalid and should raise ValueError
    bh = {"monday": {"start": "09:00", "end": "17:00"}}
    overrides = {"2025-09-29": {"start": "00:00", "end": "00:00"}}
    with pytest.raises(ValueError):
        BusinessDuration(
            business_timezone="UTC",
            business_hours=bh,
            overrides=overrides,
        )


def test_calculate_respects_overrides_extends_hours():
    # Override Monday to start earlier and end later
    bh = {"monday": {"start": "09:00", "end": "17:00"}}
    overrides = {"2025-09-29": {"start": "08:00", "end": "20:00"}}
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours=bh,
        overrides=overrides,
    )
    start = datetime(2025, 9, 29, 7, 30)
    end = datetime(2025, 9, 29, 20, 30)
    duration = bd.calculate(start, end)
    # business time from 08:00 to 20:00 -> 12 hours
    assert duration == timedelta(hours=12)


def test_calculate_respects_holidays():
    # If the start/end fall on a holiday, no business time should be counted
    bh = {"monday": {"start": "09:00", "end": "17:00"}}
    # 2025-09-29 is a Monday
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours=bh,
        holidays=["2025-09-29"],
    )
    start = datetime(2025, 9, 29, 10, 0)
    end = datetime(2025, 9, 29, 12, 0)
    duration = bd.calculate(start, end)
    assert duration == timedelta(0)


def test_business_hours_dict_converted_to_object():
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    assert isinstance(bd.business_hours, BusinessHours)


def test_overrides_dict_converted_to_object():
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        overrides={"2025-09-29": {"start": "08:00", "end": "20:00"}},
    )
    assert isinstance(bd.overrides, BusinessHoursOverrides)


def test_invalid_timezone_raises():
    with pytest.raises(ValueError):
        BusinessDuration(
            business_timezone="Invalid/Zone",
            business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        )


def test_invalid_holiday_string_raises():
    with pytest.raises(ValueError):
        BusinessDuration(
            business_timezone="UTC",
            business_hours={"monday": {"start": "09:00", "end": "17:00"}},
            holidays=["not-a-date"],
        )


def test_invalid_holiday_type_raises():
    with pytest.raises(TypeError):
        BusinessDuration(
            business_timezone="UTC",
            business_hours={"monday": {"start": "09:00", "end": "17:00"}},
            holidays=[123],
        )


def test_is_business_time_with_override():
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        overrides={"2025-09-29": {"start": "08:00", "end": "20:00"}},
    )
    # 09:00 is within override
    dt_in = datetime(2025, 9, 29, 9, 0)
    assert bd.is_within_business_hours(dt_in)
    # 07:00 is outside override
    dt_out = datetime(2025, 9, 29, 7, 0)
    assert not bd.is_within_business_hours(dt_out)


def test_is_business_time_holiday():
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        holidays=["2025-09-29"],
    )
    dt = datetime(2025, 9, 29, 10, 0)
    assert not bd.is_within_business_hours(dt)


def test_calculate_start_greater_end_returns_zero():
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 9, 30, 10, 0)
    end = datetime(2025, 9, 29, 10, 0)
    assert bd.calculate(start, end) == timedelta(0)


def test_calculate_multi_day_sum():
    # Monday and Tuesday both 09:00-17:00
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
        },
    )
    start = datetime(2025, 9, 29, 10, 0)
    end = datetime(2025, 9, 30, 15, 0)
    # Day1: 10:00-17:00 = 7h ; Day2: 09:00-15:00 = 6h ; total = 13h
    assert bd.calculate(start, end) == timedelta(hours=13)


def test_missing_weekday_treated_as_non_business():
    # Sunday missing -> should count zero
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 9, 28, 10, 0)  # Sunday
    end = datetime(2025, 9, 28, 15, 0)
    assert bd.calculate(start, end) == timedelta(0)


def test_shorthand_schedule_in_business_duration():
    """Shorthand schedule should work when passed to BusinessDuration."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"start": "09:00", "end": "17:00"},
    )
    # Monday 10:00-12:00 should be 2 hours
    start = datetime(2025, 9, 29, 10, 0)
    end = datetime(2025, 9, 29, 12, 0)
    assert bd.calculate(start, end) == timedelta(hours=2)


def test_mixed_timezone_datetimes_converted_correctly():
    """Datetimes with different timezones should be converted to business timezone."""
    from zoneinfo import ZoneInfo

    bd = BusinessDuration(
        business_timezone="America/New_York",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    # 7 AM Pacific = 10 AM Eastern
    # 12 PM Pacific = 3 PM Eastern
    # Business hours: 9 AM - 5 PM Eastern
    # So 10 AM - 3 PM Eastern = 5 hours of business time
    start = datetime(2025, 12, 8, 7, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    end = datetime(2025, 12, 8, 12, 0, tzinfo=ZoneInfo("America/Los_Angeles"))

    result = bd.calculate(start, end)
    assert result == timedelta(hours=5)


def test_start_after_end_with_different_timezones_returns_zero():
    """When start > end after comparing aware datetimes, return zero."""
    from zoneinfo import ZoneInfo

    bd = BusinessDuration(
        business_timezone="America/New_York",
        business_hours={"start": "09:00", "end": "17:00"},
    )
    # 10 AM Pacific (1 PM Eastern / 6 PM UTC) > 10 AM London (5 AM Eastern / 10 AM UTC)
    start = datetime(2025, 12, 8, 10, 0, tzinfo=ZoneInfo("America/Los_Angeles"))
    end = datetime(2025, 12, 8, 10, 0, tzinfo=ZoneInfo("Europe/London"))

    result = bd.calculate(start, end)
    assert result == timedelta(0)


# =============================================================================
# Edge Cases
# =============================================================================


def test_passing_business_hours_object_directly():
    """Test that BusinessHours objects can be passed directly."""
    bh = BusinessHours(
        schedule={"monday": {"start": "09:00", "end": "17:00"}},
        timezone="UTC",
    )
    bd = BusinessDuration(business_timezone="UTC", business_hours=bh)
    assert bd.business_hours is bh


def test_passing_overrides_object_directly():
    """Test that BusinessHoursOverrides objects can be passed directly."""
    bho = BusinessHoursOverrides(
        overrides={"2025-12-24": {"start": "09:00", "end": "12:00"}},
        timezone="UTC",
    )
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        overrides=bho,
    )
    assert bd.overrides is bho


def test_holidays_with_date_objects():
    """Test that date objects can be used in holidays list."""
    from datetime import date as date_type

    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        holidays=[date_type(2025, 12, 29)],  # Monday
    )
    start = datetime(2025, 12, 29, 10, 0)
    end = datetime(2025, 12, 29, 15, 0)
    assert bd.calculate(start, end) == timedelta(0)


def test_interval_spanning_full_business_day():
    """Test interval that starts before and ends after business hours."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    # Start at 6 AM, end at 10 PM - should capture full 8 hour business day
    start = datetime(2025, 12, 8, 6, 0)
    end = datetime(2025, 12, 8, 22, 0)
    assert bd.calculate(start, end) == timedelta(hours=8)


def test_interval_spanning_weekend():
    """Test calculation spanning Friday to Monday."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={
            "friday": {"start": "09:00", "end": "17:00"},
            "monday": {"start": "09:00", "end": "17:00"},
        },
    )
    # Friday Dec 5, 2025 at 3 PM to Monday Dec 8, 2025 at 11 AM
    start = datetime(2025, 12, 5, 15, 0)
    end = datetime(2025, 12, 8, 11, 0)
    # Friday: 15:00-17:00 = 2h; Saturday/Sunday = 0h; Monday: 09:00-11:00 = 2h
    assert bd.calculate(start, end) == timedelta(hours=4)


def test_interval_spanning_multiple_weeks():
    """Test calculation spanning more than one week."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    # Monday Dec 1, 2025 at 10 AM to Monday Dec 15, 2025 at 15:00
    # Mondays: Dec 1, Dec 8, Dec 15
    start = datetime(2025, 12, 1, 10, 0)
    end = datetime(2025, 12, 15, 15, 0)
    # Dec 1: 10:00-17:00 = 7h
    # Dec 8: 09:00-17:00 = 8h
    # Dec 15: 09:00-15:00 = 6h
    assert bd.calculate(start, end) == timedelta(hours=21)


def test_same_start_and_end_returns_zero():
    """Test that identical start and end times return zero."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    dt = datetime(2025, 12, 8, 10, 0)
    assert bd.calculate(dt, dt) == timedelta(0)


def test_start_exactly_at_business_end():
    """Test interval starting exactly when business hours end."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 12, 8, 17, 0)
    end = datetime(2025, 12, 8, 20, 0)
    assert bd.calculate(start, end) == timedelta(0)


def test_end_exactly_at_business_start():
    """Test interval ending exactly when business hours start."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 12, 8, 6, 0)
    end = datetime(2025, 12, 8, 9, 0)
    assert bd.calculate(start, end) == timedelta(0)


def test_holiday_takes_precedence_over_override():
    """Test that holidays take precedence over overrides."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        holidays=["2025-12-29"],  # Monday
        overrides={"2025-12-29": {"start": "08:00", "end": "20:00"}},
    )
    start = datetime(2025, 12, 29, 10, 0)
    end = datetime(2025, 12, 29, 15, 0)
    # Holiday should result in 0 hours, even with override
    assert bd.calculate(start, end) == timedelta(0)


def test_multi_day_with_holiday_in_middle():
    """Test calculation with a holiday in the middle of the range."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={
            "monday": {"start": "09:00", "end": "17:00"},
            "tuesday": {"start": "09:00", "end": "17:00"},
            "wednesday": {"start": "09:00", "end": "17:00"},
        },
        holidays=["2025-12-09"],  # Tuesday
    )
    # Monday to Wednesday
    start = datetime(2025, 12, 8, 10, 0)
    end = datetime(2025, 12, 10, 15, 0)
    # Monday: 10:00-17:00 = 7h
    # Tuesday (holiday): 0h
    # Wednesday: 09:00-15:00 = 6h
    assert bd.calculate(start, end) == timedelta(hours=13)


def test_is_within_business_hours_at_exact_start():
    """Test is_within_business_hours at exact start time (inclusive)."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    assert bd.is_within_business_hours(datetime(2025, 12, 8, 9, 0))


def test_is_within_business_hours_at_exact_end():
    """Test is_within_business_hours at exact end time (exclusive)."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    assert not bd.is_within_business_hours(datetime(2025, 12, 8, 17, 0))


def test_override_extends_hours_on_normally_closed_day():
    """Test that override can add hours to a day not in the regular schedule."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        overrides={"2025-12-13": {"start": "10:00", "end": "14:00"}},  # Saturday
    )
    # Saturday normally has no hours, but override adds them
    start = datetime(2025, 12, 13, 11, 0)
    end = datetime(2025, 12, 13, 13, 0)
    assert bd.calculate(start, end) == timedelta(hours=2)


def test_zoneinfo_object_as_business_timezone():
    """Test that ZoneInfo object can be used as business_timezone."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/New_York")
    bd = BusinessDuration(
        business_timezone=tz,
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 12, 8, 10, 0)
    end = datetime(2025, 12, 8, 12, 0)
    assert bd.calculate(start, end) == timedelta(hours=2)


def test_empty_holidays_list():
    """Test that empty holidays list is valid."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        holidays=[],
    )
    start = datetime(2025, 12, 8, 10, 0)
    end = datetime(2025, 12, 8, 12, 0)
    assert bd.calculate(start, end) == timedelta(hours=2)


def test_none_holidays():
    """Test that None holidays is valid."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        holidays=None,
    )
    start = datetime(2025, 12, 8, 10, 0)
    end = datetime(2025, 12, 8, 12, 0)
    assert bd.calculate(start, end) == timedelta(hours=2)


def test_interval_entirely_before_business_hours():
    """Test interval that ends before business hours start."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 12, 8, 5, 0)
    end = datetime(2025, 12, 8, 7, 0)
    assert bd.calculate(start, end) == timedelta(0)


def test_interval_entirely_after_business_hours():
    """Test interval that starts after business hours end."""
    bd = BusinessDuration(
        business_timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 12, 8, 19, 0)
    end = datetime(2025, 12, 8, 22, 0)
    assert bd.calculate(start, end) == timedelta(0)
