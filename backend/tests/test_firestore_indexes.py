"""
Regression: template and integration queries must not need Firestore composite indexes.

Production had no such indexes, so `GET /templates/search` returned 500 and the "featured",
"my templates" and "popular integrations" lists silently came back empty. The fake below
enforces Firestore's rule — an equality filter combined with order_by raises — so any query that
reintroduces the problem fails here.

Run from backend/:  python -m pytest tests/test_firestore_indexes.py -q
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import firebase_admin.firestore as _fs  # noqa: E402
_fs.client = lambda *a, **k: MagicMock()          # the DB classes create a client when imported

from app.db.integration_db import IntegrationDB  # noqa: E402
from app.db.sorting import sort_desc  # noqa: E402
from app.db.template_db import TemplateDB  # noqa: E402


class Doc:
    def __init__(self, data):
        self._data = data

    def to_dict(self):
        return dict(self._data)


class StrictQuery:
    def __init__(self, rows, filters=()):
        self.rows, self.filters = rows, filters

    def where(self, field, op, value):
        assert op == "=="
        return StrictQuery(self.rows, self.filters + ((field, value),))

    def order_by(self, *args, **kwargs):
        if self.filters:      # exactly what Firestore does when the composite index is missing
            raise RuntimeError("400 The query requires an index. (FAILED_PRECONDITION)")
        return self

    def limit(self, n):
        return self

    def stream(self):
        return [Doc(r) for r in self.rows if all(r.get(f) == v for f, v in self.filters)]


class StrictDB:
    def __init__(self, **collections):
        self.collections = collections

    def collection(self, name):
        return StrictQuery(self.collections[name])


NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def templates_db():
    db = TemplateDB()
    db.db = StrictDB(**{db.templates_collection: [
        {"id": "a", "name": "Email digest", "tags": ["email"], "isActive": True, "isFeatured": True, "usageCount": 5, "rating": 4.0, "createdAt": NOW, "authorId": "u1"},
        {"id": "b", "name": "Slack alert", "tags": ["slack"], "isActive": True, "isFeatured": True, "usageCount": 50, "rating": 3.0, "createdAt": NOW - timedelta(days=5), "authorId": "u1"},
        {"id": "c", "name": "CRM sync", "tags": ["crm"], "isActive": True, "isFeatured": False, "usageCount": 20, "rating": 4.9, "createdAt": NOW - timedelta(days=2), "authorId": "u2"},
        {"id": "x", "name": "Hidden", "tags": [], "isActive": False, "isFeatured": True, "usageCount": 999, "rating": 5.0, "createdAt": NOW, "authorId": "u1"},
    ]})
    return db


def ids(result):
    return [t["id"] for t in result["templates"]]


def search(db, **kw):
    return asyncio.run(db.search_templates(**kw))


def test_search_works_for_every_sort_order_and_hides_inactive_templates():
    db = templates_db()
    assert ids(search(db, sort_by="popular")) == ["b", "c", "a"]
    assert ids(search(db, sort_by="most_used")) == ["b", "c", "a"]
    assert ids(search(db, sort_by="rating")) == ["c", "a", "b"]
    assert ids(search(db, sort_by="newest")) == ["a", "c", "b"]


def test_search_filters_then_paginates_the_sorted_list():
    db = templates_db()
    page2 = search(db, sort_by="popular", page=2, page_size=2)
    assert ids(page2) == ["a"] and page2["total"] == 3
    assert ids(search(db, query="slack")) == ["b"]


def test_featured_returns_the_best_rated_featured_templates():
    db = templates_db()
    assert [t["id"] for t in asyncio.run(db.get_featured_templates(limit=10))] == ["a", "b"]
    assert [t["id"] for t in asyncio.run(db.get_featured_templates(limit=1))] == ["a"]


def test_a_users_templates_are_listed_newest_first():
    assert [t["id"] for t in asyncio.run(templates_db().get_user_templates("u1"))] == ["a", "x", "b"]   # a and x tie on date; stable order


def integrations_db():
    db = IntegrationDB()
    db.db = StrictDB(**{db.integrations_collection: [
        {"id": "i1", "isActive": True, "popularity": 10, "category": "crm"},
        {"id": "i2", "isActive": True, "popularity": 90, "category": "email"},
        {"id": "i3", "isActive": True, "popularity": 50, "category": "crm"},
        {"id": "i4", "isActive": False, "popularity": 100, "category": "crm"},
    ]})
    return db


def test_integration_catalog_is_listed_most_popular_first():
    db = integrations_db()
    listing = asyncio.run(db.get_all_integrations())
    assert listing["success"] and [i["id"] for i in listing["integrations"]] == ["i2", "i3", "i1"]
    assert [i["id"] for i in asyncio.run(db.get_all_integrations(category="crm"))["integrations"]] == ["i3", "i1"]
    assert [i["id"] for i in asyncio.run(db.get_all_integrations(page=2, page_size=2))["integrations"]] == ["i1"]


def test_popular_integrations():
    assert [i["id"] for i in asyncio.run(integrations_db().get_popular_integrations(limit=2))] == ["i2", "i3"]


def test_the_strict_fake_really_rejects_the_old_query_shape():
    """Guards the guard: if this stops raising, the tests above prove nothing."""
    with pytest.raises(RuntimeError, match="requires an index"):
        StrictDB(t=[]).collection("t").where("isActive", "==", True).order_by("usageCount")


def test_sort_desc_copes_with_missing_and_mixed_values():
    rows = [{"n": 3}, {}, {"n": None}, {"n": 10}, {"n": "x"}, {"n": NOW}]
    assert [r.get("n") for r in sort_desc(rows, "n")][:2] == [NOW, 10]        # datetimes (epoch seconds) outrank small numbers
    assert sort_desc([], "n") == []
