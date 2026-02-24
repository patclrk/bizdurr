# bizdurr

[![Tests](https://github.com/patclrk/bizdurr/actions/workflows/tests.yml/badge.svg)](https://github.com/patclrk/bizdurr/actions/workflows/tests.yml)
[![PyPI version](https://img.shields.io/pypi/v/bizdurr.svg)](https://pypi.org/project/bizdurr/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/bizdurr.svg?color=blue)](https://pypistats.org/packages/bizdurr)
[![Python versions](https://img.shields.io/pypi/pyversions/bizdurr.svg)](https://pypi.org/project/bizdurr/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

### A lightweight, flexible business duration calculator

Calculate the amount of time that falls within your defined business hours — accounting for weekly schedules, holidays, and per-date overrides.

---

## Installation

```bash
uv add bizdurr
```

Or with pip:

```bash
pip install bizdurr
```

Or install from source:

```bash
git clone https://github.com/patclrk/bizdurr.git
cd bizdurr
uv pip install .
```

---

## Quick Start

```python
from datetime import datetime
from bizdurr import BusinessDuration

# Define your weekly business hours
schedule = {
    "monday":    {"start": "09:00", "end": "17:00"},
    "tuesday":   {"start": "09:00", "end": "17:00"},
    "wednesday": {"start": "09:00", "end": "17:00"},
    "thursday":  {"start": "09:00", "end": "17:00"},
    "friday":    {"start": "09:00", "end": "17:00"},
}

# Create a BusinessDuration instance
bd = BusinessDuration(
    business_hours=schedule,
    business_timezone="America/New_York",
)

# Calculate the business duration between two datetimes
start = datetime(2025, 12, 8, 8, 0)   # Monday 8:00 AM
end   = datetime(2025, 12, 8, 18, 0)  # Monday 6:00 PM

duration = bd.calculate(start, end)
print(duration)  # 8:00:00 (8 hours of business time)
type(duration)  # <class 'datetime.timedelta'>
```

---

## In a DataFrame

```python
from datetime import datetime
import polars as pl
from bizdurr import BusinessDuration

# Set up business hours
bd = BusinessDuration(
    business_hours={"start": "09:00", "end": "17:00"},
    business_timezone="America/New_York",
)

# Create a dataframe with start and end timestamps
df = pl.DataFrame({
    "ticket_id": [1, 2, 3, 4],
    "start_time": [
        datetime(2025, 12, 8, 9, 0),   # Monday 9:00 AM
        datetime(2025, 12, 8, 16, 0),  # Monday 4:00 PM
        datetime(2025, 12, 9, 10, 0),  # Tuesday 10:00 AM
        datetime(2025, 12, 12, 11, 0), # Friday 11:00 AM
    ],
    "end_time": [
        datetime(2025, 12, 8, 12, 0),  # Monday 12:00 PM
        datetime(2025, 12, 9, 10, 0),  # Tuesday 10:00 AM
        datetime(2025, 12, 9, 15, 0),  # Tuesday 3:00 PM
        datetime(2025, 12, 12, 17, 0), # Friday 5:00 PM
    ],
})

# Calculate business duration for each row
df_with_duration = df.with_columns(
    business_duration=pl.struct("start_time", "end_time").map_elements(
        lambda row: bd.calculate(row["start_time"], row["end_time"])
    )
)

print(df_with_duration)
# Output:
# ┌───────────┬─────────────────────┬─────────────────────┬──────────────────┐
# │ ticket_id ┆ start_time          ┆ end_time            ┆ business_duration│
# │ ---       ┆ ---                 ┆ ---                 ┆ ---              │
# │ i64       ┆ datetime[μs]        ┆ datetime[μs]        ┆ duration[μs]     │
# ╞═══════════╪═════════════════════╪═════════════════════╪══════════════════╡
# │ 1         ┆ 2025-12-08 09:00:00 ┆ 2025-12-08 12:00:00 ┆ 3h               │
# │ 2         ┆ 2025-12-08 16:00:00 ┆ 2025-12-09 10:00:00 ┆ 2h               │
# │ 3         ┆ 2025-12-09 10:00:00 ┆ 2025-12-09 15:00:00 ┆ 5h               │
# │ 4         ┆ 2025-12-12 11:00:00 ┆ 2025-12-12 17:00:00 ┆ 6h               │
# └───────────┴─────────────────────┴─────────────────────┴──────────────────┘
```

---

## Features

### Weekly Schedule

Pass a dict mapping weekday names (case-insensitive) to start/end times in `HH:MM` 24-hour format:

```python
schedule = {
    "monday": {"start": "09:00", "end": "17:00"},
    "tuesday": {"start": "10:00", "end": "16:00"},
    # ...
}
```

### Shorthand Schedule (Monday–Friday)

For a fixed Monday through Friday schedule, use the shorthand format:

```python
bd = BusinessDuration(
    business_hours={"start": "09:00", "end": "17:00"},  # Expands to Mon-Fri
    business_timezone="America/New_York",
)
```

This automatically expands to Monday through Friday with the same hours. Weekend days (Saturday and Sunday) are excluded.

### Holidays

Exclude specific dates from business hours:

```python
bd = BusinessDuration(
    business_hours=schedule,
    business_timezone="America/New_York",
    holidays=["2025-12-25", "2026-01-01"],  # ISO date strings or date objects
)
```

### Per-Date Overrides

Override business hours for specific dates (e.g., early close):

```python
bd = BusinessDuration(
    business_hours=schedule,
    business_timezone="America/New_York",
    overrides={
        # Christmas Eve: half day
        "2025-12-24": {"start": "09:00", "end": "12:00"},
    },
)
```

### Timezone Handling

The `business_timezone` parameter specifies **where the business is located**. All business hours are interpreted in this timezone, and all calculations are performed relative to it.

```python
from datetime import datetime
from zoneinfo import ZoneInfo
from bizdurr import BusinessDuration

# Business is located in New York
bd = BusinessDuration(
    business_hours={"start": "09:00", "end": "17:00"},
    business_timezone="America/New_York",
)

# 1. Naive datetimes are assumed to be in the business timezone
bd.calculate(
    datetime(2025, 12, 8, 10, 0),
    datetime(2025, 12, 8, 15, 0)
)  # 5 hours

# 2. Aware datetimes in the same timezone work as expected
eastern = ZoneInfo("America/New_York")
bd.calculate(
    datetime(2025, 12, 8, 10, 0, tzinfo=eastern),
    datetime(2025, 12, 8, 15, 0, tzinfo=eastern)
)  # 5 hours

# 3. Aware datetimes in different timezones are converted automatically
pacific = ZoneInfo("America/Los_Angeles")
bd.calculate(
    datetime(2025, 12, 8, 7, 0, tzinfo=pacific),   # 7 AM Pacific = 10 AM Eastern
    datetime(2025, 12, 8, 12, 0, tzinfo=pacific)   # 12 PM Pacific = 3 PM Eastern
)  # 5 hours
```