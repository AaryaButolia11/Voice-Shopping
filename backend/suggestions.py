"""Smart suggestion engine.

Combines three signals:

1. History     - items the user adds often but aren't on the current list.
2. Seasonal    - produce in season this month that isn't already listed.
3. Substitute  - alternatives for items currently on the list.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc
from sqlalchemy.orm import Session

from catalog import categorize, seasonal_items, substitutes_for
from models import Item, PurchaseHistory


def build_suggestions(db: Session, limit: int = 6) -> list[dict]:
    current = {i.name.strip().lower() for i in db.query(Item).all()}
    suggestions: list[dict] = []
    seen: set[str] = set()

    def add(
        name: str,
        reason: str,
        kind: str,
        category: str | None = None,
    ):
        key = name.strip().lower()

        if not key or key in current or key in seen:
            return

        seen.add(key)

        suggestions.append(
            {
                "name": name,
                "reason": reason,
                "type": kind,
                "category": category or categorize(name),
            }
        )

    # 1. History-based: frequently added items not on the list right now.
    history = (
        db.query(PurchaseHistory)
        .order_by(
            desc(PurchaseHistory.count),
            desc(PurchaseHistory.last_added),
        )
        .limit(15)
        .all()
    )

    for record in history:
        if record.count >= 2:
            add(
                record.name,
                f"You've added this {record.count} times — running low?",
                "history",
                record.category,
            )

    # 2. Seasonal produce for the current month.
    month = datetime.utcnow().month

    for produce in seasonal_items(month):
        add(
            produce,
            "In season right now",
            "seasonal",
            "produce",
        )

    # 3. Substitutes for items already on the list.
    for item in db.query(Item).all():
        for sub in substitutes_for(item.name):
            add(
                sub,
                f"Alternative to {item.name}",
                "substitute",
            )

    return suggestions[:limit]


def record_purchase(
    db: Session,
    name: str,
    category: str,
) -> None:
    """Increment the purchase-history counter for an added item."""

    key = name.strip().lower()

    record = (
        db.query(PurchaseHistory)
        .filter(PurchaseHistory.name == key)
        .one_or_none()
    )

    if record:
        record.count += 1
        record.last_added = datetime.utcnow()
    else:
        record = PurchaseHistory(
            name=key,
            category=category,
            count=1,
        )
        db.add(record)

    db.commit()