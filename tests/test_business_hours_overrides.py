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
