"""Manual, backup-first matching of the owner's October 16 screenshots.

Reads the frozen PUBLIC reference data already downloaded to assets/four-page-reference.
Never contacts or modifies Production. Never runs on startup. Unlisted sections are
retained hidden; IDs, existing anchors and unrelated pages/settings are preserved.
"""
import asyncio
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core import db, now, new_id
from routes_admin import strip_resolved
from content_sync.schema import config
from content_sync.state import is_source
from content_sync.source import capture

VERSION = "four-page-reference-2026-10-16"
PAGES = ("craft-livelihood", "theatre", "rakhigarhi", "home")


def matched(content, reference, key):
    current = {section["id"]: section for section in content["sections"]}
    sections, used = [], set()
    for incoming in reference["sections"]:
        section = copy.deepcopy(incoming)
        section.pop("notes", None)
        section["data"] = strip_resolved(section["data"])
        previous = current.get(section["id"], {})
        if not section["data"].get("anchor") and previous.get("data", {}).get("anchor"):
            section["data"]["anchor"] = previous["data"]["anchor"]
        section.setdefault("styles", {})
        if key == "theatre" and section["type"] == "hero":
            section["data"]["layout"] = "theatre-rehearsal-reference"
        if key == "rakhigarhi" and section["data"].get("anchor") == "haveli-chaupal":
            section["data"]["layout"] = "haveli-reference-aligned"
        if key == "rakhigarhi" and section["data"].get("anchor") == "the-ambition":
            section["data"]["layout"] = "rakhigarhi-ambition-aligned"
        used.add(section["id"])
        sections.append(section)
    sections.extend({**copy.deepcopy(s), "hidden": True} for s in content["sections"] if s["id"] not in used)
    return {**copy.deepcopy(content), "sections": sections}


async def main():
    cfg = config()
    if not cfg or not await is_source(db, cfg):
        raise RuntimeError("Reference matching is allowed only on the configured Preview source")
    if await db.content_migrations.find_one({"key": VERSION}, {"_id": 0}):
        print("Already matched; subsequent saved edits preserved")
        return
    backup_path = ROOT.parent / "memory/backups" / f"{VERSION}.json"
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    if not backup_path.exists():
        backup_path.write_text(json.dumps({"pages": await db.pages.find({}, {"_id": 0}).to_list(100),
            "settings": await db.settings.find_one({"key": "site"}, {"_id": 0}),
            "notes": await db.notes.find({}, {"_id": 0}).to_list(100)}, indent=2))
    results, stamp = {}, now()
    for key in PAGES:
        page = await db.pages.find_one({"key": key}, {"_id": 0})
        reference = json.loads((ROOT.parent / "assets/four-page-reference" / f"{key}.json").read_text())["content"]
        # Craft/Home already match the exact reference data and stylesheet. Do
        # not rewrite untouched pages or publish draft-only content unnecessarily.
        if key in {"craft-livelihood", "home"}:
            actual = [s for s in page["published"]["sections"] if not s.get("hidden")]
            for source, target in zip(actual, reference["sections"]):
                if source["id"] != target["id"] or source["data"] != strip_resolved(target["data"]):
                    raise RuntimeError(f"{key} has changed since comparison; review it before applying")
            if len(actual) != len(reference["sections"]):
                raise RuntimeError(f"{key} section count changed during review")
            results[key] = "already matches; unchanged"
            continue
        updates = {field: matched(page[field], reference, key) for field in ("draft", "published")}
        for field in ("draft", "published"):
            await db.revisions.insert_one({"id": new_id(), "entity_type": "page", "entity_id": key,
                "content": copy.deepcopy(page[field]), "action": f"before latest screenshot match ({field})",
                "by": "owner-approved-reference-match", "note": VERSION, "created_at": stamp})
        updates.update(updated_at=stamp, published_at=stamp, design_migration=VERSION)
        result = await db.pages.update_one({"key": key, "updated_at": page["updated_at"]}, {"$set": updates})
        if result.matched_count != 1:
            raise RuntimeError(f"{key} was edited during matching; no content overwritten for that page")
        results[key] = "matched latest reference"
    await db.content_migrations.insert_one({"key": VERSION, "applied_at": stamp, "pages": results})
    release = await capture(db, force=True)
    print(json.dumps({"results": results, "release_state": release["state"]}))


if __name__ == "__main__":
    asyncio.run(main())