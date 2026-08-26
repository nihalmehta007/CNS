"""
backend/db.py  –  MongoDB backend (pymongo, synchronous)

Uses centralised settings from ``backend.config``.

Exports:  init_db()  |  close_db()  |  db_health()
          insert_message(...)  |  list_messages(...)
"""

from __future__ import annotations

from typing import Any

from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from backend.config import settings

_client: MongoClient | None = None
_col: Collection | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_collection() -> Collection:
    if _col is None:
        init_db()
    return _col


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Connect to MongoDB and ensure indexes exist.
    Called once at application startup.
    """
    global _client, _col

    _client = MongoClient(
        settings.MONGO_URI,
        serverSelectionTimeoutMS=settings.MONGO_TIMEOUT_MS,
        maxPoolSize=settings.MONGO_POOL_SIZE,
    )

    # Force a connection check at startup so we fail fast if Mongo is down.
    try:
        _client.admin.command("ping")
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        raise RuntimeError(
            f"Cannot reach MongoDB at {settings.MONGO_URI!r}: {exc}"
        ) from exc

    db = _client[settings.MONGO_DB]
    _col = db["messages"]

    # Indexes
    _col.create_index([("created_at", DESCENDING)])
    _col.create_index("email")

    print(f"[db] Connected to MongoDB  db={settings.MONGO_DB!r}  col=messages")


def close_db() -> None:
    """Gracefully close the MongoDB connection."""
    global _client, _col
    if _client is not None:
        _client.close()
        _client = None
        _col = None
        print("[db] MongoDB connection closed.")


def db_health() -> dict[str, Any]:
    """Return a lightweight health-check payload."""
    if _client is None:
        try:
            init_db()
        except Exception as exc:
            return {"mongo": "error", "detail": str(exc)}
    try:
        _client.admin.command("ping")
        return {"mongo": "ok"}
    except Exception as exc:
        return {"mongo": "error", "detail": str(exc)}


def insert_message(
    *,
    created_at: str,
    ip: str | None,
    user_agent: str | None,
    name: str,
    email: str,
    service: str,
    message: str,
) -> str:
    """Insert a contact submission. Returns the new document's string ID."""
    col = _get_collection()

    doc: dict[str, Any] = {
        "created_at": created_at,
        "ip": ip,
        "user_agent": user_agent,
        "name": name,
        "email": email,
        "service": service,
        "message": message,
    }

    result = col.insert_one(doc)
    return str(result.inserted_id)


def list_messages(*, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    """Return messages newest-first, with pagination."""
    col = _get_collection()

    cursor = (
        col.find(
            {},
            {
                "_id": 1,
                "created_at": 1,
                "name": 1,
                "email": 1,
                "service": 1,
                "message": 1,
                "ip": 1,
                "user_agent": 1,
            },
        )
        .sort("created_at", DESCENDING)
        .skip(offset)
        .limit(limit)
    )

    rows = []
    for doc in cursor:
        doc["id"] = str(doc.pop("_id"))  # expose ObjectId as plain string "id"
        rows.append(doc)

    return rows
