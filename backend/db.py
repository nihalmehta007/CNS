"""
backend/db.py  –  MongoDB backend (pymongo, synchronous)

Uses centralised settings from ``backend.config``.

Exports:  init_db()  |  close_db()  |  db_health()
          insert_message(...)  |  list_messages(...)
"""

from __future__ import annotations

import logging
import os
from typing import Any

from pymongo import DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

from backend.config import settings

log = logging.getLogger(__name__)

_client: MongoClient | None = None
_col: Collection | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _is_local_mongo_on_cloud() -> bool:
    """Check if running in a cloud/serverless environment with default localhost Mongo URI."""
    is_cloud = bool(
        os.environ.get("VERCEL")
        or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
    )
    is_local_uri = (
        "localhost" in settings.MONGO_URI or "127.0.0.1" in settings.MONGO_URI
    )
    return is_cloud and is_local_uri


def _get_collection() -> Collection | None:
    if _col is None:
        init_db()
    return _col


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def init_db() -> None:
    """Connect to MongoDB and ensure indexes exist."""
    global _client, _col

    if _is_local_mongo_on_cloud():
        log.info(
            "Detected cloud serverless runtime with localhost MONGO_URI; "
            "skipping local MongoDB connection. Set MONGO_URI to MongoDB Atlas in project settings."
        )
        return

    try:
        _client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=settings.MONGO_TIMEOUT_MS,
            maxPoolSize=settings.MONGO_POOL_SIZE,
        )

        # Force a connection check so we fail fast if Mongo is down.
        _client.admin.command("ping")

        db = _client[settings.MONGO_DB]
        _col = db["messages"]

        # Indexes
        _col.create_index([("created_at", DESCENDING)])
        _col.create_index("email")

        print(f"[db] Connected to MongoDB  db={settings.MONGO_DB!r}  col=messages")
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        _client = None
        _col = None
        log.warning("Cannot reach MongoDB at %r: %s", settings.MONGO_URI, exc)
    except Exception as exc:
        _client = None
        _col = None
        log.warning("MongoDB initialisation error: %s", exc)


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
    if _is_local_mongo_on_cloud():
        return {
            "mongo": "unconfigured",
            "detail": "Localhost Mongo skipped in cloud environment. Configure MONGO_URI for MongoDB Atlas.",
        }
    if _client is None:
        try:
            init_db()
        except Exception as exc:
            return {"mongo": "error", "detail": str(exc)}
    if _client is None:
        return {"mongo": "disconnected"}
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
) -> str | None:
    """Insert a contact submission. Returns the new document's string ID, or None if DB is unavailable."""
    col = None
    try:
        col = _get_collection()
    except Exception as exc:
        log.warning("Could not obtain MongoDB collection: %s", exc)
        return None

    if col is None:
        return None

    doc: dict[str, Any] = {
        "created_at": created_at,
        "ip": ip,
        "user_agent": user_agent,
        "name": name,
        "email": email,
        "service": service,
        "message": message,
    }

    try:
        result = col.insert_one(doc)
        return str(result.inserted_id)
    except Exception as exc:
        log.error("Failed to insert message into MongoDB: %s", exc)
        return None


def list_messages(*, limit: int = 200, offset: int = 0) -> list[dict[str, Any]]:
    """Return messages newest-first, with pagination."""
    try:
        col = _get_collection()
        if col is None:
            return []

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
    except Exception as exc:
        log.error("Failed to list messages: %s", exc)
        return []
