# Booking Operations Insights

This repository contains a small internal-style operational analysis tool for reviewing booking and scheduling data from a sanitized production snapshot.

## What’s inside
- `booking-ops-insights/`: the Python project (data, scripts, and generated report)
  - `data/bookings_sample.csv`: realistic sample bookings (sanitized / fake)
  - `scripts/analyze_integrity.py`: integrity checks (invalid ranges, overlaps)
  - `scripts/utilization_summary.py`: utilization + peak window analysis and report generation
  - `outputs/ops_report.md`: decision-ready markdown summary

## How to run (local)
From the repo root:

```bash
python3 -m pip install -r booking-ops-insights/requirements.txt
python3 booking-ops-insights/scripts/analyze_integrity.py
python3 booking-ops-insights/scripts/utilization_summary.py
```

The markdown report is written to `booking-ops-insights/outputs/ops_report.md`.