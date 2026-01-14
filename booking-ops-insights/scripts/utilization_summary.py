"""
utilization_summary.py

Utilization analysis for booking/scheduling data.

Key design goals:
- Keep logic explainable and easy to audit.
- Avoid complex dependencies; use pandas for basic aggregation.

Operating assumptions:
- Operating window is a fixed 12 hours per day (default: 10:00–22:00).
- Utilization is based on booked time within the operating window.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

# These scripts are intended to be runnable directly (no package install step),
# so we use a same-folder import instead of a package import.
from analyze_integrity import analyze_integrity, load_bookings


@dataclass(frozen=True)
class OperatingWindow:
    start: time
    end: time

    @property
    def hours_per_day(self) -> float:
        # Assumes end is later than start on the same day (no overnight windows).
        dt0 = datetime(2000, 1, 1, self.start.hour, self.start.minute)
        dt1 = datetime(2000, 1, 1, self.end.hour, self.end.minute)
        return (dt1 - dt0).total_seconds() / 3600.0


def _overlap_minutes(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> float:
    """
    Compute overlap in minutes between [a_start, a_end) and [b_start, b_end).
    """
    latest_start = max(a_start, b_start)
    earliest_end = min(a_end, b_end)
    delta = earliest_end - latest_start
    return max(0.0, delta.total_seconds() / 60.0)


def booked_minutes_within_operating_window(
    start_dt: datetime, end_dt: datetime, window: OperatingWindow
) -> float:
    """
    Compute minutes booked within the operating window across potentially multi-day bookings.

    This is written defensively even though typical room bookings are same-day.
    """
    if end_dt <= start_dt:
        return 0.0

    total_minutes = 0.0

    day = start_dt.date()
    last_day = end_dt.date()
    while day <= last_day:
        win_start = datetime.combine(day, window.start)
        win_end = datetime.combine(day, window.end)

        # For the day, overlap with the booking interval.
        total_minutes += _overlap_minutes(start_dt, end_dt, win_start, win_end)

        day = day + timedelta(days=1)

    return total_minutes


def peak_booking_window(df: pd.DataFrame, window_hours: int = 4) -> dict[str, Any]:
    """
    Identify peak booking hours and best contiguous peak window.

    Method:
    - Accumulate booked minutes by hour-of-day across all rooms.
    - Find the best contiguous N-hour window by total minutes.
    """
    # Minutes booked per hour-of-day (0..23)
    minutes_by_hour = [0.0] * 24

    usable = df["start_time"].notna() & df["end_time"].notna() & (df["end_time"] > df["start_time"])
    df_ok = df.loc[usable].copy()

    for _, row in df_ok.iterrows():
        start = row["start_time"].to_pydatetime()
        end = row["end_time"].to_pydatetime()

        # Iterate hour buckets for the span. This is small data; clarity > micro-optimizations.
        cursor = start.replace(minute=0, second=0, microsecond=0)
        if cursor > start:
            cursor = cursor - timedelta(hours=1)

        while cursor < end:
            hour_start = cursor
            hour_end = cursor + timedelta(hours=1)
            minutes_by_hour[hour_start.hour] += _overlap_minutes(start, end, hour_start, hour_end)
            cursor = cursor + timedelta(hours=1)

    # Top hours (for quick read-outs)
    ranked_hours = sorted(range(24), key=lambda h: minutes_by_hour[h], reverse=True)
    top_hours = [{"hour": h, "booked_minutes": round(minutes_by_hour[h], 1)} for h in ranked_hours[:5]]

    # Best contiguous window
    best_start = 0
    best_minutes = -1.0
    for h in range(0, 24 - window_hours + 1):
        window_minutes = sum(minutes_by_hour[h : h + window_hours])
        if window_minutes > best_minutes:
            best_minutes = window_minutes
            best_start = h

    best_end = best_start + window_hours
    best_label = f"{best_start:02d}:00–{best_end:02d}:00"

    return {
        "minutes_by_hour": {f"{h:02d}:00": round(minutes_by_hour[h], 1) for h in range(24)},
        "top_hours": top_hours,
        "peak_window": {"start_hour": best_start, "end_hour": best_end, "label": best_label, "booked_minutes": round(best_minutes, 1)},
    }


def utilization_summary(
    csv_path: Path,
    operating_window: OperatingWindow | None = None,
    low_utilization_threshold: float = 0.30,
) -> dict[str, Any]:
    """
    Calculate utilization per room and detect low-utilization rooms.
    Returns a structured summary dictionary.
    """
    if operating_window is None:
        operating_window = OperatingWindow(start=time(10, 0), end=time(22, 0))  # 12-hour window

    df = load_bookings(csv_path)

    # Determine analysis date range (based on booking start dates present).
    usable_start = df["start_time"].notna()
    unique_days = sorted(df.loc[usable_start, "start_time"].dt.date.unique().tolist())
    days_count = len(unique_days)

    # Booked minutes per room, within operating window
    def _row_booked_minutes(row: pd.Series) -> float:
        if pd.isna(row["start_time"]) or pd.isna(row["end_time"]):
            return 0.0
        return booked_minutes_within_operating_window(
            row["start_time"].to_pydatetime(),
            row["end_time"].to_pydatetime(),
            operating_window,
        )

    df["booked_minutes_operating"] = df.apply(_row_booked_minutes, axis=1)

    booked_by_room = (
        df.groupby("room_id", dropna=False)["booked_minutes_operating"]
        .sum()
        .sort_values(ascending=False)
        .to_dict()
    )

    # Total available minutes is room_count * days * operating_hours_per_day
    rooms = sorted([str(r) for r in df["room_id"].dropna().unique().tolist()])
    available_minutes_per_room = days_count * operating_window.hours_per_day * 60.0

    utilization_by_room: dict[str, dict[str, Any]] = {}
    for room in rooms:
        booked_minutes = float(booked_by_room.get(room, 0.0))
        utilization = 0.0 if available_minutes_per_room == 0 else booked_minutes / available_minutes_per_room
        utilization_by_room[room] = {
            "booked_hours": round(booked_minutes / 60.0, 2),
            "available_hours": round(available_minutes_per_room / 60.0, 2),
            "utilization_pct": round(utilization * 100.0, 1),
        }

    underutilized_rooms = [
        room
        for room, metrics in utilization_by_room.items()
        if (metrics["utilization_pct"] / 100.0) < low_utilization_threshold
    ]

    peak = peak_booking_window(df, window_hours=4)

    summary: dict[str, Any] = {
        "total_bookings": int(len(df)),
        "days_analyzed": int(days_count),
        "operating_window": {
            "start": operating_window.start.strftime("%H:%M"),
            "end": operating_window.end.strftime("%H:%M"),
            "hours_per_day": round(operating_window.hours_per_day, 2),
        },
        "utilization_by_room": utilization_by_room,
        "rooms_under_threshold": underutilized_rooms,
        "low_utilization_threshold_pct": round(low_utilization_threshold * 100.0, 1),
        "peak_booking": peak,
    }

    return summary


def write_ops_report(
    report_path: Path,
    integrity: dict[str, Any],
    utilization: dict[str, Any],
) -> None:
    """
    Write a simple internal markdown report to disk.
    """
    report_path.parent.mkdir(parents=True, exist_ok=True)

    total_bookings = integrity["total_bookings"]
    issues_total = integrity["issues_total"]
    issues_by_type = integrity["issues_by_type"]

    peak_window = utilization["peak_booking"]["peak_window"]["label"]
    under = utilization["rooms_under_threshold"]

    lines: list[str] = []
    lines.append("# Booking Operations Report (Sample)\n")
    lines.append("## Summary\n")
    lines.append(f"- **Total bookings analyzed**: {total_bookings}\n")
    lines.append(
        f"- **Integrity issues**: {issues_total} "
        f"(invalid time ranges: {issues_by_type['invalid_time_range']}, overlaps: {issues_by_type['overlap']})\n"
    )
    lines.append(f"- **Peak booking window (4h)**: {peak_window}\n")
    lines.append(f"- **Rooms under {utilization['low_utilization_threshold_pct']}% utilization**: {', '.join(under) if under else 'None'}\n")

    lines.append("\n## Utilization by Room\n")
    lines.append("| Room | Booked Hours | Available Hours | Utilization |\n")
    lines.append("|---|---:|---:|---:|\n")
    for room, metrics in utilization["utilization_by_room"].items():
        lines.append(
            f"| {room} | {metrics['booked_hours']:.2f} | {metrics['available_hours']:.2f} | {metrics['utilization_pct']:.1f}% |\n"
        )

    lines.append("\n## Operational Notes\n")
    lines.append(
        "- **Data hygiene**: Overlaps and invalid time ranges should be triaged first; they can skew downstream utilization and SLA reporting.\n"
    )
    lines.append(
        "- **Capacity alignment**: Rooms below 30% utilization are candidates for consolidation, repurposing, or targeted demand generation (depending on business context).\n"
    )
    lines.append(
        "- **Peak demand**: Peak window can inform staffing, on-call coverage, and housekeeping/turnover scheduling.\n"
    )
    lines.append(
        "- **Next step**: If this were a recurring workflow, schedule a weekly export + run and track trends (utilization, overlaps, invalid bookings) over time.\n"
    )

    report_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    csv_path = project_root / "data" / "bookings_sample.csv"
    report_path = project_root / "outputs" / "ops_report.md"

    integrity = analyze_integrity(csv_path)
    utilization = utilization_summary(csv_path)

    write_ops_report(report_path, integrity=integrity, utilization=utilization)

    print("Utilization Summary")
    print("-" * 80)
    print(f"Days analyzed: {utilization['days_analyzed']}")
    print(f"Operating window: {utilization['operating_window']['start']}–{utilization['operating_window']['end']}")
    print(f"Peak booking window: {utilization['peak_booking']['peak_window']['label']}")
    print(f"Rooms under {utilization['low_utilization_threshold_pct']}% utilization: {utilization['rooms_under_threshold']}")
    print()
    print(f"Wrote report: {report_path}")


if __name__ == "__main__":
    main()

