from datetime import date, datetime

import pytest

from bizdurr.BusinessHoursOverrides import BusinessHoursOverrides


def test_parse_and_get_override():
    overrides = {"2025-09-29": {"start": "09:00", "end": "17:00"}}
    bho = BusinessHoursOverrides(overrides=overrides, timezone="UTC")

    assert bho.is_override_for_date(date(2025, 9, 29))
    start, end = bho.get_override_for_date(date(2025, 9, 29))
    assert start.hour == 9 and start.minute == 0
    assert end.hour == 17 and end.minute == 0


def test_get_override_for_datetime_and_string_key():
    overrides = {"2025-09-30": {"start": "10:00", "end": "18:00"}}
    bho = BusinessHoursOverrides(overrides=overrides, timezone="UTC")

    dt = datetime(2025, 9, 30, 12, 0)
    assert bho.is_override_for_date(dt)
    assert bho.get_override_for_date("2025-09-30") is not None


def test_invalid_override_key_raises():
    with pytest.raises(ValueError):
        BusinessHoursOverrides(
            overrides={"not-a-date": {"start": "09:00", "end": "17:00"}}, timezone="UTC"
        )


def test_invalid_time_format_raises():
    with pytest.raises(ValueError):
        BusinessHoursOverrides(
            overrides={"2025-09-29": {"start": "9am", "end": "5pm"}}, timezone="UTC"
        )


def test_zero_length_override_rejected():
    with pytest.raises(ValueError):
        BusinessHoursOverrides(
            overrides={"2025-09-29": {"start": "09:00", "end": "09:00"}}, timezone="UTC"
        )


# =============================================================================
# Edge Cases
# =============================================================================


def test_override_with_date_object_key():
    """Test that date objects can be used as keys in overrides."""
    overrides = {date(2025, 12, 24): {"start": "09:00", "end": "12:00"}}
    bho = BusinessHoursOverrides(overrides=overrides, timezone="UTC")

    assert bho.is_override_for_date(date(2025, 12, 24))
    assert bho.get_override_for_date("2025-12-24") is not None


def test_timezone_accepts_zoneinfo_object():
    """Test that timezone parameter accepts ZoneInfo objects directly."""
    from zoneinfo import ZoneInfo

    tz = ZoneInfo("America/New_York")
    bho = BusinessHoursOverrides(
        overrides={"2025-12-24": {"start": "09:00", "end": "12:00"}},
        timezone=tz,
    )
    start, _ = bho.get_override_for_date("2025-12-24")
    assert start.tzinfo == tz


def test_empty_overrides_dict():
    """Test that an empty overrides dict is valid."""
    bho = BusinessHoursOverrides(overrides={}, timezone="UTC")
    assert bho.get_override_for_date("2025-12-24") is None
    assert not bho.is_override_for_date(date(2025, 12, 24))


def test_missing_start_key_raises():
    """Test that missing 'start' key raises ValueError."""
    with pytest.raises(ValueError, match="must contain both 'start' and 'end'"):
        BusinessHoursOverrides(
            overrides={"2025-12-24": {"end": "12:00"}},
            timezone="UTC",
        )


def test_missing_end_key_raises():
    """Test that missing 'end' key raises ValueError."""
    with pytest.raises(ValueError, match="must contain both 'start' and 'end'"):
        BusinessHoursOverrides(
            overrides={"2025-12-24": {"start": "09:00"}},
            timezone="UTC",
        )


def test_override_value_not_dict_raises():
    """Test that non-dict override value raises TypeError."""
    with pytest.raises(TypeError, match="must be a dict"):
        BusinessHoursOverrides(
            overrides={"2025-12-24": "09:00-12:00"},
            timezone="UTC",
        )


def test_override_with_reduced_hours():
    """Test that overrides can reduce hours compared to what might be normal."""
    # This just verifies the override stores reduced hours correctly
    bho = BusinessHoursOverrides(
        overrides={"2025-12-24": {"start": "09:00", "end": "12:00"}},
        timezone="UTC",
    )
    start, end = bho.get_override_for_date("2025-12-24")
    assert start.hour == 9
    assert end.hour == 12


def test_get_override_returns_none_for_undefined_date():
    """Test that get_override_for_date returns None for dates not in overrides."""
    bho = BusinessHoursOverrides(
        overrides={"2025-12-24": {"start": "09:00", "end": "12:00"}},
        timezone="UTC",
    )
    assert bho.get_override_for_date("2025-12-25") is None
    assert bho.get_override_for_date(date(2025, 12, 25)) is None
    assert bho.get_override_for_date(datetime(2025, 12, 25, 10, 0)) is None
