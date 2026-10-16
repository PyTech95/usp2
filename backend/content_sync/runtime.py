from contextlib import asynccontextmanager
from core import db, log, now
from .schema import config
from .state import ensure_indexes, is_source, lease
from .source import capture, baked
from .target import apply


async def startup():
    if not config():
        return
    await ensure_indexes(db)
    if await is_source(db, config()):
        await prepare()
    else:
        try:
            bundle, pointer = baked()
            result = await apply(db, bundle, pointer)
            log.info("Content release %s: %s; pages=%s", result["release_id"][:12], result["state"], result["counts"]["pages"])
        except Exception as error:
            log.error("Content promotion failed; existing content retained: %s", error)
            await db.content_runtime.update_one({"key": "target"}, {"$set": {"state": "failed", "error": "Content promotion did not complete; existing content/backup retained.", "failed_at": now()}}, upsert=True)


async def readiness():
    if not config() or await is_source(db, config()):
        return True
    status = await db.content_runtime.find_one({"key": "target"}, {"_id": 0, "state": 1})
    return bool(status and status.get("state") == "applied")


async def prepare():
    try:
        return await capture(db)
    except Exception as error:
        log.error("Content release could not be prepared: %s", error)
        await db.content_runtime.update_one({"key": "source"}, {"$set": {"state": "pending", "error": "Content release upload failed. Retry preparation before republishing.", "failed_at": now()}}, upsert=True)
        return {"state": "pending"}


def is_content_mutation(path):
    return any(path.startswith(f"/api/admin/{part}") for part in ("pages", "notes", "media", "menus", "settings", "site-live", "site-styles", "header-live", "site-import", "content-import", "revisions")) or path == "/api/admin/restore"


@asynccontextmanager
async def write_guard(path, method):
    # Coordinate saves in old/new pods with release application, so neither can
    # overwrite a successful concurrent save between reading and importing data.
    if method in {"POST", "PUT", "PATCH", "DELETE"} and is_content_mutation(path):
        async with lease(db, "promotion"):
            yield
    else:
        yield


async def after_mutation(path, method, status_code):
    if path.endswith("/content-import/preview") or method not in {"POST", "PUT", "PATCH", "DELETE"} or not 200 <= status_code < 300 or not is_content_mutation(path) or not config():
        return None
    if not await is_source(db, config()):
        return None
    return await prepare()