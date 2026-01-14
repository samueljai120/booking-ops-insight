"""
analyze_integrity.py

Internal-style integrity checks for booking/scheduling data.

Assumptions:
- Input data is a sanitized snapshot exported from production (CSV).
- No live DB access; scripts operate purely on the CSV.
- Time columns are stored as local timestamps (no timezone handling here).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class IntegrityIssue:
    """
    Represents a single integrity issue found in the dataset.
    """

    issue_type: str  # e.g., "invalid_time_range" or "overlap"
    booking_id: str
    room_id: str
    start_time: str
    end_time: str
    details: str


def load_bookings(csv_path: Path) -> pd.DataFrame:
    """
    Load the bookings CSV and parse time fields.
    """
    df = pd.read_csv(csv_path)

    # Parse timestamps. `errors="coerce"` turns bad parses into NaT so they can be flagged if needed.
    for col in ("start_time", "end_time", "created_at"):
        df[col] = pd.to_datetime(df[col], errors="coerce")

    return df


def find_invalid_time_ranges(df: pd.DataFrame) -> list[IntegrityIssue]:
    """
    Detect bookings where end_time <= start_time.
    """
    issues: list[IntegrityIssue] = []

    invalid_mask = df["end_time"].notna() & df["start_time"].notna() & (df["end_time"] <= df["start_time"])
    invalid_df = df.loc[invalid_mask, ["booking_id", "room_id", "start_time", "end_time"]].copy()

    for _, row in invalid_df.iterrows():
        issues.append(
            IntegrityIssue(
                issue_type="invalid_time_range",
                booking_id=str(row["booking_id"]),
                room_id=str(row["room_id"]),
                start_time=str(row["start_time"]),
                end_time=str(row["end_time"]),
                details="end_time is less than or equal to start_time",
            )
        )

    return issues


def find_overlaps_per_room(df: pd.DataFrame) -> list[IntegrityIssue]:
    """
    Detect overlapping bookings within the same room.

    Logic (simple, explainable):
    - For each room, sort bookings by start_time.
    - Track the previous booking's end_time.
    - If a booking starts before the previous booking ends, we flag an overlap.
    """
    issues: list[IntegrityIssue] = []

    # Work only with rows that have usable start/end times and a valid time range.
    usable = df["start_time"].notna() & df["end_time"].notna() & (df["end_time"] > df["start_time"])
    df_ok = df.loc[usable].copy()

    for room_id, room_df in df_ok.groupby("room_id"):
        room_sorted = room_df.sort_values(["start_time", "end_time", "booking_id"]).reset_index(drop=True)

        prev_end = None
        prev_booking_id = None
        for _, row in room_sorted.iterrows():
            start = row["start_time"]
            end = row["end_time"]

            if prev_end is not None and start < prev_end:
                issues.append(
                    IntegrityIssue(
                        issue_type="overlap",
                        booking_id=str(row["booking_id"]),
                        room_id=str(room_id),
                        start_time=str(start),
                        end_time=str(end),
                        details=f"Overlaps prior booking {prev_booking_id} (prior end_time={prev_end})",
                    )
                )

            # Update tracker. This uses the maximum end time so chained overlaps are handled correctly.
            if prev_end is None or end > prev_end:
                prev_end = end
                prev_booking_id = str(row["booking_id"])

    return issues


def analyze_integrity(csv_path: Path) -> dict[str, Any]:
    """
    Run integrity checks and return a structured summary dictionary.
    """
    df = load_bookings(csv_path)

    invalid_time_issues = find_invalid_time_ranges(df)
    overlap_issues = find_overlaps_per_room(df)

    all_issues = invalid_time_issues + overlap_issues

    summary: dict[str, Any] = {
        "total_bookings": int(len(df)),
        "issues_total": int(len(all_issues)),
        "issues_by_type": {
            "invalid_time_range": int(len(invalid_time_issues)),
            "overlap": int(len(overlap_issues)),
        },
        "issues": [asdict(i) for i in all_issues],
    }

    return summary


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    csv_path = project_root / "data" / "bookings_sample.csv"

    summary = analyze_integrity(csv_path)

    # Pretty-ish console output without additional dependencies.
    print("Integrity Summary")
    print("-" * 80)
    print(f"Total bookings analyzed: {summary['total_bookings']}")
    print(f"Integrity issues found:  {summary['issues_total']}")
    print(f"  - invalid_time_range: {summary['issues_by_type']['invalid_time_range']}")
    print(f"  - overlap:            {summary['issues_by_type']['overlap']}")
    print()

    if summary["issues_total"] > 0:
        print("Issues (first 20):")
        for issue in summary["issues"][:20]:
            print(
                f"- [{issue['issue_type']}] {issue['booking_id']} | {issue['room_id']} | "
                f"{issue['start_time']} -> {issue['end_time']} | {issue['details']}"
            )


if __name__ == "__main__":
    main()
