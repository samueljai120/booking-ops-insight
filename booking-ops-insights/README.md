# Booking Operations Insights

## Overview
This project demonstrates a lightweight, internal-style approach to analyzing booking and scheduling data for operational decision-making. It focuses on two core analytical needs:

- Validating data integrity (e.g., invalid timestamps, overlapping bookings)
- Understanding utilization patterns (e.g., room-level utilization, peak demand windows)

The goal is to provide a clear, explainable workflow that can be reused for periodic audits of booking data extracts.

## Context
The dataset is assumed to be a **sanitized snapshot from a production PostgreSQL system** (extracted via **Supabase**). It is intentionally static:

- No live database connections
- No operational writes
- Analysis runs locally against a CSV export

## Problem
Operations teams often need quick answers to questions like:

- Are there obvious data quality problems that could distort reporting?
- Which rooms are over/under-utilized relative to operating capacity?
- When do peak booking windows occur, and do they align with staffing/availability?

## Approach
1. **Data integrity checks** (`scripts/analyze_integrity.py`)
   - Parse timestamps
   - Identify bookings with invalid time ranges (end <= start)
   - Detect overlapping bookings within the same room

2. **Utilization analysis** (`scripts/utilization_summary.py`)
   - Compute total booked time per room
   - Estimate utilization assuming a fixed operating window per day
   - Identify low-utilization rooms (below 30%)
   - Identify peak booking hours/windows

3. **Decision-ready output**
   - A markdown operational report is written to `outputs/ops_report.md`

## Tools Used
- **Python**
- **pandas** for data manipulation
- **python-dateutil** (via pandas parsing) for resilient datetime handling

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

This repo is intentionally simple and readable so it can be adapted to internal workflows and run as part of periodic operational reviews.
