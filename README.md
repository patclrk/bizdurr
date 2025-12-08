# bizdurr

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
    timezone="America/New_York",
)

# Calculate the business duration between two datetimes
start = datetime(2025, 12, 8, 8, 0)   # Monday 8:00 AM
end   = datetime(2025, 12, 8, 18, 0)  # Monday 6:00 PM

duration = bd.calculate(start, end)
print(duration)  # 8:00:00 (8 hours of business time)
type(duration)  # <class 'datetime.timedelta'>
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
    timezone="America/New_York",
)
```

This automatically expands to Monday through Friday with the same hours. Weekend days (Saturday and Sunday) are excluded.

### Holidays

Exclude specific dates from business hours:

```python
bd = BusinessDuration(
    business_hours=schedule,
    timezone="America/New_York",
    holidays=["2025-12-25", "2026-01-01"],  # ISO date strings or date objects
)
```

### Per-Date Overrides

Override business hours for specific dates (e.g., early close):

```python
bd = BusinessDuration(
    business_hours=schedule,
    timezone="America/New_York",
    overrides={
        # Christmas Eve: half day
        "2025-12-24": {"start": "09:00", "end": "12:00"},
    },
)
```

### Timezone Support

All times are interpreted in the specified IANA timezone:
```python
bd = BusinessDuration(
    business_hours=schedule,
    timezone="Europe/London",
)
```