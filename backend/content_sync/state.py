import asyncio
import hashlib
import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from urllib.parse import urlsplit
from core import new_id


def database_binding(database):
    # A copied preview database must not make production a release writer.
    # Exclude username/password; only the connection host(s) and DB namespace
    # identify the environment. This is not an authentication credential.
    authority = urlsplit(os.environ["MONGO_URL"]).netloc.rsplit("@", 1)[-1]
    return hashlib.sha256(f"{authority}/{database.name}".encode()).hexdigest()


async def is_source(database, cfg):
    return bool(cfg and database_binding(database) == cfg.get("source_binding") and await environment_id(database) == cfg["source_id"])


async def environment_id(database):
    doc = await database.content_runtime.find_one_and_update(
        {"key": "identity"}, {"$setOnInsert": {"environment_id": new_id()}},
        upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0})
    return doc["environment_id"]


async def ensure_indexes(database):
    await database.content_runtime.create_index("key", unique=True)
    await database.content_locks.create_index("key", unique=True)
    await database.content_backups.create_index("id", unique=True)
    await database.content_backup_records.create_index([("backup_id", 1), ("collection", 1)])


@asynccontextmanager
async def lease(database, key):
    token = new_id()
    for attempt in range(120):
        instant = datetime.now(timezone.utc)
        try:
            row = await database.content_locks.find_one_and_update(
                {"key": key, "$or": [{"expires_at": {"$lt": instant}}, {"owner": token}]},
                {"$set": {"owner": token, "expires_at": instant + timedelta(minutes=10)}},
                upsert=True, return_document=ReturnDocument.AFTER, projection={"_id": 0})
            if row and row.get("owner") == token:
                break
        except DuplicateKeyError:
            pass
        await asyncio.sleep(.5)
    else:
        raise RuntimeError("Another content operation is still in progress; no content was changed")
    try:
        yield
    finally:
        await database.content_locks.delete_one({"key": key, "owner": token})