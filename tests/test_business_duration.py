from datetime import datetime, timedelta

import pytest

from bizdurr.BusinessDuration import BusinessDuration
from bizdurr.BusinessHours import BusinessHours
from bizdurr.BusinessHoursOverrides import BusinessHoursOverrides


def test_business_duration_creation():
    wh = {"monday": {"start": "09:30", "end": "17:30"}}
    bd = BusinessDuration(
        timezone="UTC",
        business_hours=wh,
    )
    assert isinstance(bd.business_hours, BusinessHours)


def test_calculate_within_working_hours():
    wh = {"monday": {"start": "09:00", "end": "17:00"}}
    bd = BusinessDuration(
        timezone="UTC",
        business_hours=wh,
    )
    start = datetime(2025, 9, 29, 10, 0)
    end = datetime(2025, 9, 29, 12, 0)
    duration = bd.calculate(start, end)
    assert duration == timedelta(hours=2)


def test_calculate_outside_working_hours():
    bh = {"monday": {"start": "09:00", "end": "17:00"}}
    bd = BusinessDuration(
        timezone="UTC",
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
            timezone="UTC",
            business_hours=bh,
            overrides=overrides,
        )


def test_calculate_respects_overrides_extends_hours():
    # Override Monday to start earlier and end later
    bh = {"monday": {"start": "09:00", "end": "17:00"}}
    overrides = {"2025-09-29": {"start": "08:00", "end": "20:00"}}
    bd = BusinessDuration(
        timezone="UTC",
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
        timezone="UTC",
        business_hours=bh,
        holidays=["2025-09-29"],
    )
    start = datetime(2025, 9, 29, 10, 0)
    end = datetime(2025, 9, 29, 12, 0)
    duration = bd.calculate(start, end)
    assert duration == timedelta(0)


def test_business_hours_dict_converted_to_object():
    bd = BusinessDuration(
        timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    assert isinstance(bd.business_hours, BusinessHours)


def test_overrides_dict_converted_to_object():
    bd = BusinessDuration(
        timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        overrides={"2025-09-29": {"start": "08:00", "end": "20:00"}},
    )
    assert isinstance(bd.overrides, BusinessHoursOverrides)


def test_invalid_timezone_raises():
    with pytest.raises(ValueError):
        BusinessDuration(
            timezone="Invalid/Zone",
            business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        )


def test_invalid_holiday_string_raises():
    with pytest.raises(ValueError):
        BusinessDuration(
            timezone="UTC",
            business_hours={"monday": {"start": "09:00", "end": "17:00"}},
            holidays=["not-a-date"],
        )


def test_invalid_holiday_type_raises():
    with pytest.raises(TypeError):
        BusinessDuration(
            timezone="UTC",
            business_hours={"monday": {"start": "09:00", "end": "17:00"}},
            holidays=[123],
        )


def test_is_business_time_with_override():
    bd = BusinessDuration(
        timezone="UTC",
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
        timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
        holidays=["2025-09-29"],
    )
    dt = datetime(2025, 9, 29, 10, 0)
    assert not bd.is_within_business_hours(dt)


def test_calculate_start_greater_end_returns_zero():
    bd = BusinessDuration(
        timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 9, 30, 10, 0)
    end = datetime(2025, 9, 29, 10, 0)
    assert bd.calculate(start, end) == timedelta(0)


def test_calculate_multi_day_sum():
    # Monday and Tuesday both 09:00-17:00
    bd = BusinessDuration(
        timezone="UTC",
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
        timezone="UTC",
        business_hours={"monday": {"start": "09:00", "end": "17:00"}},
    )
    start = datetime(2025, 9, 28, 10, 0)  # Sunday
    end = datetime(2025, 9, 28, 15, 0)
    assert bd.calculate(start, end) == timedelta(0)


def test_shorthand_schedule_in_business_duration():
    """Shorthand schedule should work when passed to BusinessDuration."""
    bd = BusinessDuration(
        timezone="UTC",
        business_hours={"start": "09:00", "end": "17:00"},
    )
    # Monday 10:00-12:00 should be 2 hours
    start = datetime(2025, 9, 29, 10, 0)
    end = datetime(2025, 9, 29, 12, 0)
    assert bd.calculate(start, end) == timedelta(hours=2)
