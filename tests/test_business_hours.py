from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest

from bizdurr.BusinessHours import BusinessHours


def test_get_day_hours_parsed():
    sched = {"monday": {"start": "09:30", "end": "17:30"}}
    bh = BusinessHours(schedule=sched, timezone="UTC")
    assert bh.get_day_hours("Monday") == (
        time(9, 30, tzinfo=ZoneInfo("UTC")),
        time(17, 30, tzinfo=ZoneInfo("UTC")),
    )


def test_is_within_business_hours_naive_interpreted():
    sched = {"monday": {"start": "09:30", "end": "17:30"}}
    bh = BusinessHours(schedule=sched, timezone="UTC")
    dt = datetime(2025, 9, 29, 10, 0)  # Monday
    assert bh.is_within_business_hours(dt)


def test_is_business_time_outside():
    sched = {"monday": {"start": "09:30", "end": "17:30"}}
    bh = BusinessHours(schedule=sched, timezone="UTC")
    dt = datetime(2025, 9, 29, 8, 30)  # Monday before start
    assert not bh.is_within_business_hours(dt)


def test_invalid_weekday_name_raises():
    with pytest.raises(ValueError):
        BusinessHours(
            schedule={"funday": {"start": "09:00", "end": "17:00"}}, timezone="UTC"
        )


def test_invalid_schedule_type_raises():
    with pytest.raises(TypeError):
        BusinessHours(schedule="not-a-dict", timezone="UTC")


def test_missing_start_or_end_key_raises():
    with pytest.raises(ValueError):
        BusinessHours(schedule={"monday": {"start": "09:00"}}, timezone="UTC")


def test_invalid_time_format_raises():
    with pytest.raises(ValueError):
        BusinessHours(
            schedule={"monday": {"start": "9am", "end": "5pm"}}, timezone="UTC"
        )


def test_timezone_validation():
    with pytest.raises(ValueError):
        BusinessHours(
            schedule={"monday": {"start": "09:00", "end": "17:00"}},
            timezone="Invalid/Zone",
        )


def test_day_lookup_case_insensitive_and_boundaries():
    sched = {"monday": {"start": "09:00", "end": "17:00"}}
    bh = BusinessHours(schedule=sched, timezone="UTC")
    # start inclusive
    assert bh.is_within_business_hours(datetime(2025, 9, 29, 9, 0))
    # end exclusive
    assert not bh.is_within_business_hours(datetime(2025, 9, 29, 17, 0))


def test_missing_weekday_returns_false():
    sched = {"monday": {"start": "09:00", "end": "17:00"}}
    bh = BusinessHours(schedule=sched, timezone="UTC")
    # Sunday not present
    assert not bh.is_within_business_hours(datetime(2025, 9, 28, 10, 0))


def test_overnight_interval_raises():
    # If start > end (overnight), current implementation raises ValueError
    sched = {"monday": {"start": "22:00", "end": "06:00"}}
    with pytest.raises(ValueError):
        BusinessHours(schedule=sched, timezone="UTC")


def test_shorthand_schedule_expands_to_monday_friday():
    """Test that a simple start/end dict expands to Mon-Fri."""
    bh = BusinessHours(schedule={"start": "09:00", "end": "17:00"}, timezone="UTC")

    # All weekdays should have the same hours
    expected = (time(9, 0, tzinfo=ZoneInfo("UTC")), time(17, 0, tzinfo=ZoneInfo("UTC")))
    assert bh.get_day_hours("monday") == expected
    assert bh.get_day_hours("tuesday") == expected
    assert bh.get_day_hours("wednesday") == expected
    assert bh.get_day_hours("thursday") == expected
    assert bh.get_day_hours("friday") == expected

    # Weekend should not be included
    assert bh.get_day_hours("saturday") is None
    assert bh.get_day_hours("sunday") is None


def test_shorthand_schedule_is_within_business_hours():
    """Test that shorthand schedule works with is_within_business_hours."""
    bh = BusinessHours(schedule={"start": "09:00", "end": "17:00"}, timezone="UTC")

    # Monday during business hours
    assert bh.is_within_business_hours(datetime(2025, 12, 8, 10, 0))

    # Monday outside business hours
    assert not bh.is_within_business_hours(datetime(2025, 12, 8, 8, 0))

    # Saturday (not in shorthand schedule)
    assert not bh.is_within_business_hours(datetime(2025, 12, 6, 10, 0))


def test_shorthand_schedule_validation():
    """Test that shorthand schedule validates times correctly."""
    # Invalid time format
    with pytest.raises(ValueError):
        BusinessHours(schedule={"start": "9am", "end": "5pm"}, timezone="UTC")

    # Start equals end
    with pytest.raises(ValueError):
        BusinessHours(schedule={"start": "09:00", "end": "09:00"}, timezone="UTC")

    # Start after end
    with pytest.raises(ValueError):
        BusinessHours(schedule={"start": "17:00", "end": "09:00"}, timezone="UTC")


def test_full_schedule_not_affected_by_shorthand_expansion():
    """Test that providing a full schedule still works normally."""
    sched = {
        "monday": {"start": "08:00", "end": "16:00"},
        "wednesday": {"start": "10:00", "end": "18:00"},
    }
    bh = BusinessHours(schedule=sched, timezone="UTC")

    assert bh.get_day_hours("monday") == (
        time(8, 0, tzinfo=ZoneInfo("UTC")),
        time(16, 0, tzinfo=ZoneInfo("UTC")),
    )
    assert bh.get_day_hours("wednesday") == (
        time(10, 0, tzinfo=ZoneInfo("UTC")),
        time(18, 0, tzinfo=ZoneInfo("UTC")),
    )
    # Tuesday not defined
    assert bh.get_day_hours("tuesday") is None


# =============================================================================
# Edge Cases
# =============================================================================


def test_timezone_accepts_zoneinfo_object():
    """Test that timezone parameter accepts ZoneInfo objects directly."""
    tz = ZoneInfo("America/New_York")
    bh = BusinessHours(
        schedule={"monday": {"start": "09:00", "end": "17:00"}},
        timezone=tz,
    )
    assert bh.get_day_hours("monday")[0].tzinfo == tz


def test_is_within_business_hours_rejects_non_datetime():
    """Test that is_within_business_hours raises TypeError for non-datetime."""
    bh = BusinessHours(
        schedule={"monday": {"start": "09:00", "end": "17:00"}},
        timezone="UTC",
    )
    with pytest.raises(TypeError, match="Expected datetime"):
        bh.is_within_business_hours("2025-12-08 10:00:00")

    with pytest.raises(TypeError, match="Expected datetime"):
        bh.is_within_business_hours(None)


def test_get_day_hours_with_whitespace():
    """Test that get_day_hours handles whitespace in day names."""
    bh = BusinessHours(
        schedule={"monday": {"start": "09:00", "end": "17:00"}},
        timezone="UTC",
    )
    # With leading/trailing whitespace
    assert bh.get_day_hours("  monday  ") is not None
    assert bh.get_day_hours("MONDAY") is not None


def test_empty_schedule_creates_no_hours():
    """Test that an empty schedule dict results in no business hours."""
    bh = BusinessHours(schedule={}, timezone="UTC")
    assert bh.get_day_hours("monday") is None
    assert not bh.is_within_business_hours(datetime(2025, 12, 8, 10, 0))


def test_aware_datetime_converted_to_schedule_timezone():
    """Test that aware datetimes are correctly converted for comparison."""
    bh = BusinessHours(
        schedule={"monday": {"start": "09:00", "end": "17:00"}},
        timezone="America/New_York",
    )
    # 2 PM UTC on Monday Dec 8, 2025 = 9 AM Eastern (start of business hours)
    utc_dt = datetime(2025, 12, 8, 14, 0, tzinfo=ZoneInfo("UTC"))
    assert bh.is_within_business_hours(utc_dt)

    # 1 PM UTC = 8 AM Eastern (before business hours)
    utc_dt_before = datetime(2025, 12, 8, 13, 0, tzinfo=ZoneInfo("UTC"))
    assert not bh.is_within_business_hours(utc_dt_before)


def test_schedule_with_only_one_minute_duration():
    """Test schedule with minimal valid duration (1 minute)."""
    bh = BusinessHours(
        schedule={"monday": {"start": "09:00", "end": "09:01"}},
        timezone="UTC",
    )
    # Exactly at start (inclusive)
    assert bh.is_within_business_hours(datetime(2025, 12, 8, 9, 0))
    # At end (exclusive)
    assert not bh.is_within_business_hours(datetime(2025, 12, 8, 9, 1))
