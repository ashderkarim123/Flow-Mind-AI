"""
Sorting helpers for Firestore results.

Firestore rejects a query that filters on one field and orders by another unless a *composite
index* exists for that pair. Nobody had created those indexes, so such queries failed in
production (or, where the error was swallowed, silently returned nothing). These catalogs are
small and already paginated in memory, so we fetch with the equality filter only and sort here —
no index needed, no deploy step to forget.
"""

from datetime import datetime
from typing import Any, Dict, Iterable, List


def _sort_value(value: Any) -> float:
    if isinstance(value, datetime):
        return value.timestamp()
    if hasattr(value, "timestamp"):          # Firestore DatetimeWithNanoseconds
        return float(value.timestamp())
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def sort_desc(rows: Iterable[Dict[str, Any]], field: str) -> List[Dict[str, Any]]:
    """Highest/newest first; rows missing the field sort last."""
    return sorted(rows, key=lambda row: _sort_value(row.get(field)), reverse=True)
