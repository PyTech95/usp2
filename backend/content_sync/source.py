import asyncio
import json
import os
from core import get_object, put_object, now, log
from .schema import BUNDLE_FILE, collect, config, counts, digest, encoded, object_prefix, MAX_BYTES, validate
from .state import is_source, lease

_capture_lock = asyncio.Lock()


async def capture(database, *, force=False, archive=False):
    cfg = config()
    if not await is_source(database, cfg):
        return {"state": "target"}
    async with _capture_lock, lease(database, "capture"):
        bundle = await collect(database, cfg)
        raw = encoded(bundle)
        release_id = digest(raw)
        previous = await database.content_runtime.find_one({"key": "source"}, {"_id": 0}) or {}
        if not force and previous.get("release_id") == release_id and previous.get("state") == "ready":
            return previous
        prefix = object_prefix(cfg)
        expected = f"{prefix}/releases/{release_id}.json"
        pointer = {"schema": 1, "source_id": cfg["source_id"], "channel": cfg["channel"], "release_id": release_id,
                   "path": expected, "captured_at": now(), "counts": counts(bundle)}
        # Deployment packages this PREVIEW working-tree file, including runtime
        # writes. Bind a deployment to this exact snapshot, not a moving pointer:
        # a cold start must never publish newer preview edits before republish.
        temporary = BUNDLE_FILE.with_suffix(".tmp")
        temporary.write_bytes(encoded({"manifest": pointer, "content": bundle}))
        os.replace(temporary, BUNDLE_FILE)
        await database.content_releases.replace_one({"release_id": release_id}, {"release_id": release_id, "manifest": pointer, "content": bundle}, upsert=True)
        status = {**pointer, "state": "ready", "archive_state": "not_required"}
        # Optional durable object-store archive. Ordinary editor saves never wait
        # for object-storage uploads; the DB + atomic baked snapshot are complete.
        if archive:
            try:
                path = await put_object(expected, raw, "application/json")
                if path != expected:
                    raise ValueError("Storage returned an unexpected release path")
                await put_object(f"{prefix}/latest.json", encoded(pointer), "application/json")
                status["archive_state"] = "ready"
            except Exception as error:
                log.warning("Content is packaged, but optional remote archive failed: %s", error)
                status["archive_state"] = "pending"
        await database.content_runtime.update_one({"key": "source"}, {"$set": status, "$unset": {"error": ""}}, upsert=True)
        return status


def baked():
    """Read only the content snapshot packaged with this deployment image."""
    if not BUNDLE_FILE.exists():
        raise ValueError("The deployment has no prepared preview content snapshot")
    raw = BUNDLE_FILE.read_bytes()
    if len(raw) > MAX_BYTES + 200000:
        raise ValueError("Oversized deployment snapshot")
    package = json.loads(raw)
    bundle, pointer = package["content"], package["manifest"]
    if digest(encoded(bundle)) != pointer.get("release_id"):
        raise ValueError("Packaged content checksum mismatch; nothing was imported")
    cfg = config()
    if pointer.get("source_id") != cfg["source_id"] or pointer.get("channel") != cfg["channel"]:
        raise ValueError("Packaged content belongs to another source")
    return validate(bundle, cfg), pointer


async def latest():
    cfg = config()
    if not cfg:
        raise ValueError("Content promotion has not been configured")
    prefix = object_prefix(cfg)
    pointer_raw = await get_object(f"{prefix}/latest.json")
    if len(pointer_raw) > 200000:
        raise ValueError("Invalid content release pointer")
    pointer = json.loads(pointer_raw)
    release_id = pointer.get("release_id", "")
    if len(release_id) != 64 or any(c not in "0123456789abcdef" for c in release_id):
        raise ValueError("Invalid release identity")
    if pointer.get("channel") != cfg["channel"] or pointer.get("source_id") != cfg["source_id"]:
        raise ValueError("Release pointer belongs to another source")
    expected = f"{prefix}/releases/{release_id}.json"
    if pointer.get("path") != expected:
        raise ValueError("Unexpected release object path")
    raw = await get_object(expected)
    if len(raw) > MAX_BYTES or digest(raw) != release_id:
        raise ValueError("Content release checksum mismatch; nothing was imported")
    return validate(json.loads(raw), cfg), pointer