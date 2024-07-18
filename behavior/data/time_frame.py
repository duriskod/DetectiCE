from __future__ import annotations

from datetime import datetime, timedelta


class TimeFrame:
    start: datetime
    end: datetime

    def __init__(self, start: datetime, end: datetime):
        self.start = start
        self.end = end

    @property
    def duration(self):
        return self.end - self.start

    def relative_offset(self, time: datetime):
        return (time - self.start) / self.duration

    def __contains__(self, other: "TimeFrame"):
        return self.start <= other.start and other.end <= self.end


class RelativeTimeFrame:
    minimal: timedelta
    maximal: timedelta

    def __init__(self, minimal: timedelta | None = None, maximal: timedelta | None = None):
        self.minimal = minimal or timedelta(0)
        self.maximal = maximal or timedelta.max

    @property
    def duration(self):
        return self.maximal - self.minimal

    @property
    def has_min(self) -> bool:
        return self.minimal > timedelta(0)

    @property
    def has_max(self) -> bool:
        return self.maximal < timedelta.max

    def union(self, other: RelativeTimeFrame) -> RelativeTimeFrame:
        return RelativeTimeFrame(min(self.minimal, other.minimal), max(self.maximal, other.maximal))

    def intersect(self, other: RelativeTimeFrame) -> RelativeTimeFrame:
        return RelativeTimeFrame(max(self.minimal, other.minimal), min(self.maximal, other.maximal))

    def __contains__(self, other: timedelta | RelativeTimeFrame):
        if isinstance(other, RelativeTimeFrame):
            return self.minimal <= other.minimal and other.maximal <= self.maximal
        elif isinstance(other, timedelta):
            return self.minimal <= other <= self.maximal

    def __add__(self, other: RelativeTimeFrame):
        minimal = min(timedelta.max, max(timedelta(0), self.minimal + other.minimal))

        if self.maximal == timedelta.max or other.maximal == timedelta.max:
            max_maximal = timedelta.max
        else:
            max_maximal = self.maximal + other.maximal

        maximal = min(timedelta.max, max(timedelta(0), max_maximal))
        return RelativeTimeFrame(minimal, maximal)

    def __eq__(self, other: RelativeTimeFrame) -> bool:
        if not isinstance(other, RelativeTimeFrame):
            return False
        return self.minimal == other.minimal and self.maximal == other.maximal

    def name_string(self) -> str:
        if not self.has_min and not self.has_max:
            return "any amount of time"
        if self.has_min and self.has_max:
            return f"between {self.minimal.total_seconds()} seconds and {self.maximal.total_seconds()} seconds"
        if self.has_min:
            return f"at least {self.minimal.total_seconds()} seconds"
        return f"at most {self.maximal.total_seconds()} seconds"

    def __repr__(self):
        return f"RelativeTimeFrame(minimal={self.minimal}, maximal={self.maximal})"

    def __str__(self):
        return f"({self.minimal} - {self.maximal})"
