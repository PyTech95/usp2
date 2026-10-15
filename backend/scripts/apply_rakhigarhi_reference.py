"""Explicit one-off PDF/reference migration. Preserves both old CMS revisions.

Run manually against the configured environment; never imported by server startup.
Selects only already-public, approved library images. Does not modify permissions.
"""
import asyncio
import copy
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import db, now, new_id, media_public_ok

KEY = "rakhigarhi"
VERSION = "rakhigarhi-reference-2026-10-15"


async def photograph(filename, label):
    candidates = await db.media.find({"filename": {"$regex": f"^{re.escape(filename)}$", "$options": "i"}}, {"_id": 0}).to_list(50)
    approved = next((m for m in candidates if media_public_ok(m)), None)
    return {"media_id": approved["id"] if approved else "", "caption": "", "placeholder": not bool(approved), "placeholder_label": label}


async def main():
    page = await db.pages.find_one({"key": KEY}, {"_id": 0})
    if not page:
        raise RuntimeError("Rakhigarhi page not found")
    if page.get("design_migration") == VERSION:
        print("Already applied; no changes")
        return
    template = json.loads((ROOT / "content/rakhigarhi_reference.json").read_text())
    for section in template["sections"]:
        section.update(id=new_id(), hidden=False)
        if section["data"].get("layout") == "haveli-reference":
            section["data"]["image"] = await photograph("haveli.png", "Haveli facade")
            section["data"]["collage"] = [await photograph("brick.webp", "Haveli brick arches"), await photograph("door.webp", "Carved wooden door")]
    stamp = now()
    update = {}
    for field in ("published", "draft"):
        previous = copy.deepcopy(page[field])
        await db.revisions.insert_one({"id": new_id(), "entity_type": "page", "entity_id": KEY, "content": previous,
                                       "action": f"before Rakhigarhi reference ({field})", "by": "approved-content-migration", "note": VERSION, "created_at": stamp})
        update[field] = {**copy.deepcopy(page[field]), **copy.deepcopy(template)}
    update.update(design_migration=VERSION, updated_at=stamp, published_at=stamp)
    await db.pages.update_one({"key": KEY}, {"$set": update})
    print("Rakhigarhi PDF applied with 9 sections and approved library photo references; other pages unchanged")


if __name__ == "__main__":
    asyncio.run(main())