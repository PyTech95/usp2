import copy
from core import now, new_id
from .schema import COLLECTION_KEYS, SITE_FIELDS, counts, config, validate
from .state import is_source, lease


async def backup(database, release_id, reason="before content promotion"):
    bid = new_id()
    records = []
    for collection in (*COLLECTION_KEYS, "settings"):
        query = {"key": "site"} if collection == "settings" else {}
        documents = await database[collection].find(query, {"_id": 0}).to_list(100000)
        records.extend({"backup_id": bid, "collection": collection, "document": d} for d in documents)
    await database.content_backups.insert_one({"id": bid, "release_id": release_id, "created_at": now(), "reason": reason, "state": "preparing"})
    if records:
        await database.content_backup_records.insert_many(records)
    await database.content_backups.update_one({"id": bid}, {"$set": {"state": "ready", "records": len(records)}})
    return bid


async def restore_records(database, bid):
    metadata = await database.content_backups.find_one({"id": bid, "state": "ready"}, {"_id": 0})
    if not metadata:
        raise ValueError("A complete backup is required")
    records = await database.content_backup_records.find({"backup_id": bid}, {"_id": 0}).to_list(500000)
    if len(records) != metadata["records"]:
        raise ValueError("Backup is incomplete")
    for collection, identity in {**COLLECTION_KEYS, "settings": "key"}.items():
        docs = [r["document"] for r in records if r["collection"] == collection]
        for doc in docs:
            await database[collection].replace_one({identity: doc[identity]}, copy.deepcopy(doc), upsert=True)
        if collection != "settings":
            await database[collection].delete_many({identity: {"$nin": [d[identity] for d in docs]}})
        elif not docs:
            await database.settings.delete_one({"key": "site"})


async def apply(database, bundle, pointer, *, force=False):
    cfg = config()
    bundle = validate(bundle, cfg)
    if await is_source(database, cfg):
        raise ValueError("The preview source cannot import its own deployment release")
    async with lease(database, "promotion"):
        prior = await database.content_runtime.find_one({"key": "target"}, {"_id": 0}) or {}
        if not force and prior.get("release_id") == pointer["release_id"] and prior.get("state") == "applied":
            return {**prior, "unchanged": True}
        # Complete durable backup BEFORE the first content write. Users, tokens,
        # enquiries, contact submissions and environment secrets are never touched.
        bid = await backup(database, pointer["release_id"])
        await database.content_runtime.update_one({"key": "target"}, {"$set": {"state": "applying", "backup_id": bid}}, upsert=True)
        try:
            # Media first, then pages/notes/settings referencing those exact IDs.
            for collection in ("media", "pages", "notes", "redirects"):
                identity = COLLECTION_KEYS[collection]
                docs = bundle["collections"][collection]
                for doc in docs:
                    await database[collection].replace_one({identity: doc[identity]}, copy.deepcopy(doc), upsert=True)
                if collection != "media":
                    await database[collection].delete_many({identity: {"$nin": [d[identity] for d in docs]}})
            # Merge CONTENT fields only. Keep indexing policy and any local
            # operational/email/auth configuration in the target environment.
            settings_update = {k: copy.deepcopy(v) for k, v in bundle["site"].items()}
            missing = SITE_FIELDS - set(settings_update)
            update = {"$set": {**settings_update, "updated_at": now()}}
            if missing:
                update["$unset"] = {k: "" for k in missing}
            await database.settings.update_one({"key": "site"}, update, upsert=True)
            for collection in ("pages", "notes", "redirects"):
                actual = await database[collection].count_documents({})
                if actual != len(bundle["collections"][collection]):
                    raise RuntimeError(f"{collection} verification failed")
            status = {"state": "applied", "release_id": pointer["release_id"], "captured_at": pointer["captured_at"],
                      "applied_at": now(), "backup_id": bid, "counts": counts(bundle)}
            await database.content_runtime.update_one({"key": "target"}, {"$set": status, "$unset": {"error": ""}}, upsert=True)
            return status
        except Exception:
            await restore_records(database, bid)
            await database.content_runtime.update_one({"key": "target"}, {"$set": {"state": "rolled_back", "backup_id": bid, "failed_at": now()}}, upsert=True)
            raise


async def restore(database, bid):
    async with lease(database, "promotion"):
        if not await database.content_backups.find_one({"id": bid, "state": "ready"}, {"_id": 0, "id": 1}):
            raise ValueError("A complete backup is required")
        safety = await backup(database, "manual-restore", "before restoring a backup")
        await restore_records(database, bid)
        await database.content_runtime.update_one({"key": "target"}, {"$set": {"restored_backup_id": bid, "restored_at": now(), "restore_safety_backup_id": safety}}, upsert=True)
        return {"restored": bid, "safety_backup_id": safety}