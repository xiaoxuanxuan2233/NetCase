from collections import Counter
from datetime import UTC, datetime, timedelta, timezone
from statistics import median

from app.models.schemas import DiagnosisRecord


def summarize(records: list[DiagnosisRecord], days: int, offset: int) -> dict:
    """Calendar-day windows in the viewer's supplied UTC offset, including today."""
    today = datetime.now(timezone(timedelta(minutes=offset))).date()
    dates = [today - timedelta(days=i) for i in reversed(range(days))]
    tz = timezone(timedelta(minutes=offset))
    now = datetime.now(UTC)
    scoped = sorted(
        (r for r in records if r.created_at <= now and r.created_at.astimezone(tz).date() in dates),
        key=lambda r: (r.created_at, r.id),
        reverse=True,
    )
    counts = Counter(r.created_at.astimezone(tz).date().isoformat() for r in scoped)
    errors: Counter[str] = Counter()
    for record in scoped:
        # Each error type counted once per diagnosis, not once per address or module.
        errors.update(
            {
                m.error_type or f"{m.name.upper()}_{m.status.upper()}"
                for m in record.modules
                if m.status in {"warning", "failed"}
            }
        )
    eligible = [r for r in scoped if r.status != "unsupported"]
    return {
        "days": days,
        "timezone_offset_minutes": offset,
        "stats": {
            "total": len(scoped),
            "passed": sum(r.status == "success" for r in eligible),
            "eligible": len(eligible),
            "issues": sum(r.status in {"failed", "warning"} for r in scoped),
            "median_duration_ms": median(r.duration_ms for r in scoped) if scoped else None,
        },
        "activity": [{"date": d.isoformat(), "count": counts[d.isoformat()]} for d in dates],
        "errors": [{"type": kind, "count": count} for kind, count in errors.most_common(5)],
        "latest": scoped[0].model_dump(mode="json") if scoped else None,
        "recent": [r.model_dump(mode="json") for r in scoped[:8]],
    }
