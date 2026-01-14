# Booking Operations Insights

## Overview
This project provides a lightweight, internal-style approach to analyzing booking and scheduling data for operational decision-making. It focuses on:

- Detecting data integrity issues (invalid time ranges, overlaps)
- Understanding utilization patterns (room-level utilization, peak demand windows)
- Producing a clear, decision-ready summary for operations stakeholders

## Context
The input is assumed to be a **sanitized snapshot from a production PostgreSQL system** (extracted via **Supabase**). It is intentionally static:

- No live database connections
- No operational writes
- Analysis runs locally against a CSV export

## What’s inside
- `data/bookings_sample.csv`: realistic sample bookings (sanitized / fake)
- `scripts/analyze_integrity.py`: integrity checks (invalid ranges, overlaps)
- `scripts/utilization_summary.py`: utilization + peak window analysis and report generation
- `outputs/ops_report.md`: decision-ready markdown summary
- `requirements.txt`: minimal dependencies

## Problem
Operations teams often need fast, reliable answers to questions like:

- Are there booking records that will distort reporting (invalid timestamps, overlaps)?
- Which rooms are under- or over-utilized relative to operating capacity?
- When do peak booking windows occur, and do they align with staffing/availability?

## Approach
1. **Data integrity checks** (`scripts/analyze_integrity.py`)
   - Parse timestamps
   - Flag bookings where `end_time <= start_time`
   - Detect overlapping bookings within the same room

2. **Utilization analysis** (`scripts/utilization_summary.py`)
   - Compute total booked time per room
   - Estimate utilization assuming a 12-hour operating window per day
   - Identify low-utilization rooms (below 30%)
   - Identify peak booking hours/windows

3. **Decision-ready output**
   - Generate a markdown operational report at `outputs/ops_report.md`

## Tools Used
- **Python**
- **pandas**
- **python-dateutil** (via pandas parsing)

## Output
- **Sample data**: `data/bookings_sample.csv`
- **Integrity summary**: printed / returned from `scripts/analyze_integrity.py`
- **Utilization summary**: printed / returned from `scripts/utilization_summary.py`
- **Operational report**: `outputs/ops_report.md`

## Why This Matters
Booking data is often a proxy for real operational demand. Small issues—like overlaps or invalid timestamps—can materially distort utilization metrics and planning decisions. A repeatable, explainable analysis like this helps teams:

- Catch data issues early (before they reach dashboards)
- Identify capacity mismatches (under- or over-utilized rooms)
- Align staffing and availability to observed demand patterns

## How to Run
1. Clone the repo
2. Install dependencies
3. Run the integrity and utilization scripts
4. Review the markdown report

From the repo root:

```bash
python3 -m pip install -r requirements.txt
python3 scripts/analyze_integrity.py
python3 scripts/utilization_summary.py
```

The markdown report is written to `outputs/ops_report.md`.