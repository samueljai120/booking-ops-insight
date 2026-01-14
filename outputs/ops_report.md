# Booking Operations Report (Sample)
## Summary
- **Total bookings analyzed**: 40
- **Integrity issues**: 6 (invalid time ranges: 1, overlaps: 5)
- **Peak booking window (4h)**: 18:00–22:00
- **Rooms under 30.0% utilization**: Room B, Room D

## Utilization by Room
| Room | Booked Hours | Available Hours | Utilization |
|---|---:|---:|---:|
| Room A | 11.50 | 36.00 | 31.9% |
| Room B | 9.75 | 36.00 | 27.1% |
| Room C | 11.58 | 36.00 | 32.2% |
| Room D | 6.75 | 36.00 | 18.8% |

## Operational Notes
- **Data hygiene**: Overlaps and invalid time ranges should be triaged first; they can skew downstream utilization and SLA reporting.
- **Capacity alignment**: Rooms below 30% utilization are candidates for consolidation, repurposing, or targeted demand generation (depending on business context).
- **Peak demand**: Peak window can inform staffing, on-call coverage, and housekeeping/turnover scheduling.
- **Next step**: If this were a recurring workflow, schedule a weekly export + run and track trends (utilization, overlaps, invalid bookings) over time.
