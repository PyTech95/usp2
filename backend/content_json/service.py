import copy
from fastapi import HTTPException
from core import now, new_id, log
from content_sync.schema import COLLECTION_KEYS, SITE_FIELDS, encoded, digest, media_ids, normalise
from content_sync.target import backup, restore_records
from .schema import parse, invalid


def export_document(collections, site):
    return {"format": "usp-content-json", "version": 1, "exported_at": now(),
            "note": "Content and media metadata only. Referenced media files must already be available in object storage.",
            "collections": normalise(collections), "site": normalise({k: v for k, v in site.items() if k in SITE_FIELDS})}


async def current_content(database):
    collections = {name: await database[name].find({}, {"_id": 0}).sort(identity, 1).to_list(100000) for name, identity in COLLECTION_KEYS.items()}
    site = await database.settings.find_one({"key": "site"}, {"_id": 0}) or {}
    return {"collections": collections, "site": {k: v for k, v in site.items() if k in SITE_FIELDS}}


async def plan_import(database, raw):
    content = parse(raw)
    current = await current_content(database)
    counts = {}
    for name, identity in COLLECTION_KEYS.items():
        existing = {doc[identity]: doc for doc in current["collections"][name]}
        identifiers = {doc.get("id"): doc[identity] for doc in existing.values() if doc.get("id")}
        counts[name] = {"total": len(content["collections"][name]), "created": 0, "updated": 0, "unchanged": 0}
        merged = []
        for item in content["collections"][name]:
            old = existing.get(item[identity])
            if item.get("id") in identifiers and identifiers[item["id"]] != item[identity]:
                invalid(f"A {name} ID already belongs to another record. Change its key/slug in the editor, not through this import.")
            item = {**copy.deepcopy(old or {}), **item}
            if name != "redirects":
                item["id"] = old["id"] if old else item.get("id") or new_id()
                if not isinstance(item["id"], str) or not item["id"]:
                    invalid(f"Invalid ID in {name}")
            if old and old.get("required"):
                item["required"] = True
            category = "created" if old is None else "unchanged" if item == old else "updated"
            counts[name][category] += 1
            merged.append(item)
        if name in {"pages", "notes", "media"} and len({d["id"] for d in merged}) != len(merged):
            invalid(f"Duplicate IDs in {name}")
        content["collections"][name] = merged
    mids = {m["id"] for m in current["collections"]["media"] + content["collections"]["media"]}
    missing = media_ids({"pages": content["collections"]["pages"], "notes": content["collections"]["notes"], "site": content["site"]}) - mids
    if missing:
        invalid(f"Missing {len(missing)} referenced media records. Include their metadata or import the full site ZIP.")
    site_changed = any(current["site"].get(key) != value for key, value in content["site"].items())
    counts["settings"] = {"total": int(bool(content["site"])), "created": 0, "updated": int(site_changed), "unchanged": int(bool(content["site"]) and not site_changed)}
    return {"content": content, "sha256": digest(raw), "state": digest(encoded(current)), "counts": counts,
            "warnings": ["Media files are not uploaded by JSON import; the referenced files must already exist.",
                         "Matching content is updated. Unlisted records, accounts, passwords, enquiries and security configuration are not removed or imported."]}


async def apply_import(database, raw, expected_sha256, expected_state, actor):
    # HTTP content-write middleware holds the shared promotion lease throughout.
    plan = await plan_import(database, raw)
    if plan["sha256"] != expected_sha256 or plan["state"] != expected_state:
        raise HTTPException(409, "The file or site content changed after review. Choose the file again to review the latest changes.")
    bid = await backup(database, plan["sha256"], "before content JSON import")
    try:
        for name in ("media", "pages", "notes", "redirects"):
            identity = COLLECTION_KEYS[name]
            for document in plan["content"]["collections"][name]:
                await database[name].replace_one({identity: document[identity]}, copy.deepcopy(document), upsert=True)
        if plan["content"]["site"]:
            await database.settings.update_one({"key": "site"}, {"$set": copy.deepcopy(plan["content"]["site"])}, upsert=True)
        await database.content_backups.update_one({"id": bid}, {"$set": {"imported_at": now(), "imported_by": actor}})
    except Exception:
        log.exception("Content JSON import failed; restoring backup %s", bid)
        try:
            await restore_records(database, bid)
        except Exception:
            log.exception("Automatic content restore failed for backup %s", bid)
            raise HTTPException(500, f"Import failed and automatic restoration could not complete. Keep backup ID {bid} for recovery.")
        raise HTTPException(500, f"Import failed. Existing content was restored. Backup ID: {bid}")
    return {"ok": True, "backup_id": bid, "counts": plan["counts"], "media_files_restored": 0}


async def backup_document(database, bid):
    meta = await database.content_backups.find_one({"id": bid, "state": "ready"}, {"_id": 0})
    if not meta:
        raise HTTPException(404, "Backup not found")
    rows = await database.content_backup_records.find({"backup_id": bid}, {"_id": 0}).to_list(500000)
    if len(rows) != meta["records"]:
        raise HTTPException(409, "Backup is incomplete")
    collections = {name: [r["document"] for r in rows if r["collection"] == name] for name in COLLECTION_KEYS}
    site = next((r["document"] for r in rows if r["collection"] == "settings"), {})
    return export_document(collections, site)