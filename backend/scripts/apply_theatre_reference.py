"""Manual, source-only Theatre redesign; backup first and never run on startup.

Usage: python scripts/apply_theatre_reference.py /app/assets/theatre
Uses supplied originals unchanged, existing storage/media helpers, stable section IDs,
existing style overrides and established navigation anchors. Running twice is a no-op.
"""
import asyncio
import copy
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import db, now, new_id, media_public_ok
from routes_media import store_file
from content_sync.schema import config
from content_sync.state import is_source
from content_sync.source import capture

VERSION = "theatre-reference-2026-10-16"
PHOTOS = {
    "hero": ("joyful-dance.png", "Joyful Dance on a Warm Theater Stage.png", "Performers in white costumes sharing a joyful moment on a theatre stage."),
    "archive": ("dramatic-trio.png", "Dramatic Trio Under Stage Lights.png", "Three performers in red, grey and green costumes, with a newspaper and walking stick on stage."),
}


async def import_photo(folder, key):
    local, filename, alt = PHOTOS[key]
    data = (folder / local).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    old = await db.media.find_one({"sha256": sha, "is_deleted": False}, {"_id": 0})
    if old:
        if not media_public_ok(old):
            raise RuntimeError(f"Existing {filename} is not approved; do not silently override its restrictions")
        return old["id"]
    mid, stamp = new_id(), now()
    stored = await store_file(mid, data, filename, 1)
    approval = "Supplied by site owner with explicit instruction to use these photographs for the Theatre redesign. Original bytes preserved; no generative editing."
    await db.media.insert_one({"id": mid, "filename": filename, "title": filename.rsplit(".", 1)[0], "sha256": sha,
        "size": len(data), "category": "Theatre", "alt": alt, "caption": "", "credit": "", "permitted_use": "USP Theatre webpage",
        "authenticity": "original", "permission": "approved", "edit_approval": "approved", "permission_notes": approval,
        "permission_expiry": "", "evidence_ref": VERSION, "may_include_minors": False, "minor_approval_documented": False,
        "focal_desktop": {"x": 50, "y": 60 if key == "hero" else 50}, "focal_mobile": {"x": 50, "y": 50},
        "version": 1, "versions": [], "derived_from": "", "archived_sources": [], "is_deleted": False,
        "uploaded_by": "owner-approved-theatre-redesign", "created_at": stamp, "updated_at": stamp,
        "approval_log": [{"at": stamp, "by": "owner-approved-theatre-redesign", "changes": {"permission": "approved", "note": approval}}], **stored})
    return mid


def redesigned(content, templates, images, added_ids):
    original = content["sections"]
    used, result = set(), []
    for template in templates:
        match = template["match"]
        previous = next((s for s in original if s["type"] == match or s.get("data", {}).get("eyebrow") == match), None)
        section = copy.deepcopy(previous or {"id": added_ids[match], "hidden": False})
        used.add(section["id"])
        section["type"] = template["type"]
        # Keep editor styles and custom data; replace only approved reference-copy fields.
        section["data"] = {**section.get("data", {}), **copy.deepcopy(template["data"])}
        for link in ("link_href", "href"):
            if previous and previous.get("data", {}).get(link):
                section["data"][link] = previous["data"][link]
        if template.get("photo"):
            section["data"]["image"] = {"media_id": images[template["photo"]], "caption": "", "credit": ""}
        result.append(section)
    for old in original:
        if old["id"] not in used:
            retained = copy.deepcopy(old)
            if retained["type"] == "notes_feed":
                retained["hidden"] = True
            result.append(retained)
    return {**copy.deepcopy(content), "sections": result}


async def main(folder):
    cfg = config()
    if not cfg or not await is_source(db, cfg):
        raise RuntimeError("This manual redesign is restricted to the configured Preview content source")
    page = await db.pages.find_one({"key": "theatre"}, {"_id": 0})
    if not page:
        raise RuntimeError("Theatre page not found")
    if page.get("design_migration") == VERSION:
        print("Already applied; saved edits unchanged")
        return
    backup_path = ROOT.parent / "memory/backups" / f"{VERSION}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if not backup_path.exists():
        backup = {"pages": await db.pages.find({}, {"_id": 0}).to_list(100),
                  "settings": await db.settings.find_one({"key": "site"}, {"_id": 0}),
                  "media_ids": [m["id"] async for m in db.media.find({}, {"_id": 0, "id": 1})]}
        backup_path.write_text(json.dumps(backup, indent=2))
    images = {key: await import_photo(folder, key) for key in PHOTOS}
    templates = json.loads((ROOT / "content/theatre_reference.json").read_text())["sections"]
    added_ids = {t["match"]: new_id() for t in templates}
    stamp, updates = now(), {}
    for field in ("published", "draft"):
        await db.revisions.insert_one({"id": new_id(), "entity_type": "page", "entity_id": "theatre", "content": copy.deepcopy(page[field]),
            "action": f"before Theatre reference ({field})", "by": "owner-approved-theatre-redesign", "note": VERSION, "created_at": stamp})
        updates[field] = redesigned(page[field], templates, images, added_ids)
    updates.update(design_migration=VERSION, updated_at=stamp, published_at=stamp)
    result = await db.pages.update_one({"key": "theatre", "updated_at": page["updated_at"]}, {"$set": updates})
    if result.matched_count != 1:
        raise RuntimeError("Theatre was edited during migration. No page content overwritten; inspect and retry.")
    release = await capture(db, force=True)
    print(json.dumps({"page": "theatre", "photos": images, "sections": len(updates["published"]["sections"]), "release_state": release["state"]}))


if __name__ == "__main__":
    asyncio.run(main(Path(sys.argv[1])))