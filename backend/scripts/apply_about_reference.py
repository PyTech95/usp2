"""Explicit source-only Who We Are layout/PDF migration; never run on startup."""
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import db, now, new_id
from content_sync.schema import config
from content_sync.state import is_source
from content_sync.source import capture

VERSION = "about-reference-2026-10-16"


def redesign(content, templates, added_ids):
    sections, used = [], set()
    for template in templates:
        match = template["match"]
        old = next((s for s in content["sections"] if s["type"] == match or s.get("data", {}).get("heading") == match), None)
        section = copy.deepcopy(old or {"id": added_ids[match]})
        used.add(section["id"])
        section.update(type=template["type"], hidden=False)
        section["data"] = {**section.get("data", {}), **copy.deepcopy(template["data"])}
        if match == "hero":
            section["data"].pop("image", None)
        sections.append(section)
    for old in content["sections"]:
        if old["id"] not in used:
            sections.append({**copy.deepcopy(old), "hidden": True})
    return {**copy.deepcopy(content), "title": "Who We Are", "sections": sections}


async def main():
    cfg = config()
    if not cfg or not await is_source(db, cfg):
        raise RuntimeError("This redesign can only be applied to the configured Preview content source")
    page = await db.pages.find_one({"key": "about"}, {"_id": 0})
    if not page:
        raise RuntimeError("Who We Are page not found")
    if page.get("design_migration") == VERSION:
        print("Already applied; saved edits unchanged")
        return
    backup = ROOT.parent / "memory/backups" / f"{VERSION}.json"
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        backup.write_text(json.dumps({"pages": await db.pages.find({}, {"_id": 0}).to_list(100),
            "settings": await db.settings.find_one({"key": "site"}, {"_id": 0})}, indent=2))
    templates = json.loads((ROOT / "content/about_reference.json").read_text())["sections"]
    added_ids = {t["match"]: new_id() for t in templates}
    stamp, updates = now(), {}
    for field in ("published", "draft"):
        await db.revisions.insert_one({"id": new_id(), "entity_type": "page", "entity_id": "about", "content": copy.deepcopy(page[field]),
            "action": f"before Who We Are reference ({field})", "by": "owner-approved-layout", "note": VERSION, "created_at": stamp})
        updates[field] = redesign(page[field], templates, added_ids)
    updates.update(design_migration=VERSION, updated_at=stamp, published_at=stamp)
    result = await db.pages.update_one({"key": "about", "updated_at": page["updated_at"]}, {"$set": updates})
    if result.matched_count != 1:
        raise RuntimeError("About was edited during migration; no content overwritten")
    release = await capture(db, force=True)
    print(json.dumps({"page": "about", "total_sections": len(updates["published"]["sections"]), "visible_sections": 5, "portraits": "five editable placeholders", "release_state": release["state"]}))


if __name__ == "__main__":
    asyncio.run(main())