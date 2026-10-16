import asyncio
import copy
import hashlib
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path

import pytest
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from content_sync import runtime, schema, source, state, target


# Live-edit preservation regressions: three-way merge, rollback safety, and capture/runtime hooks.
ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "content_release.json"
MONGO_URL = os.environ.get("MONGO_URL")


def _run(coro):
    return asyncio.run(coro)


def _load_package():
    package = json.loads(PACKAGE_PATH.read_text())
    return package["content"], package["manifest"]


def _json_digest(value):
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def _new_temp_db(prefix="live_edit_preservation"):
    if not MONGO_URL:
        raise AssertionError("MONGO_URL env var is required")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[f"{prefix}_{uuid.uuid4().hex[:10]}"]
    await state.ensure_indexes(db)
    return client, db


async def _drop_db(client, db):
    await client.drop_database(db.name)
    client.close()


async def _seed_collections_from_bundle(db, bundle):
    for col in ("pages", "notes", "media", "redirects"):
        docs = copy.deepcopy(bundle["collections"][col])
        if docs:
            await db[col].insert_many(docs)
    await db.settings.insert_one({"key": "site", **copy.deepcopy(bundle["site"])})


async def _seed_sentinels(db):
    await db.users.insert_one({"id": "u-sentinel", "email": "owner@example.com", "password_hash": "$2b$12$abc", "role": "owner", "active": True})
    await db.enquiries.insert_one({"id": "e-sentinel", "message": "hello", "status": "new"})
    await db.register.insert_one({"id": "r-sentinel", "subject": "legacy", "status": "awaiting upload"})
    await db.login_attempts.insert_one({"identifier": "ip:a@b.c", "count": 3})
    await db.tokens.insert_one({"hash": "tok", "kind": "reset", "user_id": "u-sentinel", "used": False})


def _bundle_with_release_id(bundle):
    cloned = copy.deepcopy(bundle)
    release_id = schema.digest(schema.encoded(cloned))
    pointer = {
        "schema": 1,
        "source_id": cloned["source_id"],
        "channel": cloned["channel"],
        "release_id": release_id,
        "path": f"test/releases/{release_id}.json",
        "captured_at": "2026-02-01T00:00:00+00:00",
        "counts": schema.counts(cloned),
    }
    return cloned, pointer


def _find_page(bundle, key):
    return next(p for p in bundle["collections"]["pages"] if p["key"] == key)


def _find_note(bundle, slug):
    return next(n for n in bundle["collections"]["notes"] if n["slug"] == slug)


def _first_published_note_slug(bundle):
    note = next(n for n in bundle["collections"]["notes"] if isinstance(n.get("published"), dict))
    return note["slug"]


def _collect_media_refs(value):
    from content_sync.schema import media_ids

    return media_ids(value)


def test_three_way_merge_preserves_local_conflicts_across_releases_and_same_id_reapply_force():
    async def _case():
        bundle_a, pointer_a = _load_package()
        bundle_b = copy.deepcopy(bundle_a)
        bundle_c = copy.deepcopy(bundle_a)

        # Preview B conflicts + unrelated additions.
        home_b = _find_page(bundle_b, "home")
        home_b["published"]["title"] = "PREVIEW_B_HOME_TITLE"
        home_b["draft"]["title"] = "PREVIEW_B_HOME_TITLE"
        site_b = bundle_b["site"]
        site_b["header_styles"] = {"backgroundColor": "#111111", "brandFontSize": "22px", "fontSize": "17px"}
        site_b["text_styles"] = {
            "preview-display": {"path": "display.notes-title", "area": "main", "styles": {"fontSize": "18px", "color": "#111111"}}
        }
        site_b["menus"]["main"][0]["label"] = "Preview Home Label B"
        note_slug = bundle_b["collections"]["notes"][0]["slug"]
        note_b = _find_note(bundle_b, note_slug)
        note_b["published"]["title"] = "PREVIEW_B_NOTE_TITLE"
        note_b["draft"]["title"] = "PREVIEW_B_NOTE_TITLE"
        craft_b = _find_page(bundle_b, "craft-livelihood")
        craft_b["published"]["sections"].append({"id": "preview-new-b", "type": "text", "hidden": False, "data": {"heading": "Preview B new section", "body": "Incoming from preview B"}, "styles": {}})
        craft_b["draft"]["sections"].append(copy.deepcopy(craft_b["published"]["sections"][-1]))

        # Preview C changes the same fields again and another unrelated addition.
        home_c = _find_page(bundle_c, "home")
        home_c["published"]["title"] = "PREVIEW_C_HOME_TITLE"
        home_c["draft"]["title"] = "PREVIEW_C_HOME_TITLE"
        site_c = bundle_c["site"]
        site_c["header_styles"] = {"backgroundColor": "#222222", "brandFontSize": "24px", "fontSize": "16px"}
        site_c["text_styles"] = {
            "preview-display": {"path": "display.notes-title", "area": "main", "styles": {"fontSize": "19px", "color": "#222222"}}
        }
        site_c["menus"]["main"][0]["label"] = "Preview Home Label C"
        note_c = _find_note(bundle_c, note_slug)
        note_c["published"]["title"] = "PREVIEW_C_NOTE_TITLE"
        note_c["draft"]["title"] = "PREVIEW_C_NOTE_TITLE"
        craft_c = _find_page(bundle_c, "craft-livelihood")
        craft_c["published"]["sections"].append({"id": "preview-new-c", "type": "text", "hidden": False, "data": {"heading": "Preview C new section", "body": "Incoming from preview C"}, "styles": {}})
        craft_c["draft"]["sections"].append(copy.deepcopy(craft_c["published"]["sections"][-1]))

        bundle_b, pointer_b = _bundle_with_release_id(bundle_b)
        bundle_c, pointer_c = _bundle_with_release_id(bundle_c)

        client, db = await _new_temp_db(prefix="live_edit_three_way")
        try:
            await _seed_collections_from_bundle(db, bundle_a)
            await _seed_sentinels(db)
            await target.apply(db, bundle_a, pointer_a, force=True)

            # Local live edits on same fields (must survive B/C and same-ID force apply).
            await db.pages.update_one({"key": "home"}, {"$set": {"published.title": "LOCAL_HOME_TITLE", "draft.title": "LOCAL_HOME_TITLE"}})
            await db.settings.update_one(
                {"key": "site"},
                {
                    "$set": {
                        "header_styles": {"backgroundColor": "#efe6d8", "brandFontSize": "29px", "fontSize": "21px"},
                        "text_styles": {"local-display": {"path": "display.notes-title", "area": "main", "styles": {"fontSize": "25px", "color": "#333333"}}},
                        "menus.main.0.label": "Local Home Label",
                    }
                },
            )
            await db.notes.update_one({"slug": note_slug}, {"$set": {"published.title": "LOCAL_NOTE_TITLE", "draft.title": "LOCAL_NOTE_TITLE"}})

            result_b = await target.apply(db, bundle_b, pointer_b, force=True)
            assert result_b["state"] == "applied"

            home_after_b = await db.pages.find_one({"key": "home"}, {"_id": 0})
            site_after_b = await db.settings.find_one({"key": "site"}, {"_id": 0})
            note_after_b = await db.notes.find_one({"slug": note_slug}, {"_id": 0})
            craft_after_b = await db.pages.find_one({"key": "craft-livelihood"}, {"_id": 0})

            assert home_after_b["published"]["title"] == "LOCAL_HOME_TITLE"
            assert home_after_b["draft"]["title"] == "LOCAL_HOME_TITLE"
            assert site_after_b["header_styles"]["backgroundColor"] == "#efe6d8"
            assert site_after_b["header_styles"]["brandFontSize"] == "29px"
            assert site_after_b["menus"]["main"][0]["label"] == "Local Home Label"
            assert site_after_b["text_styles"]["local-display"]["styles"]["fontSize"] == "25px"
            assert note_after_b["published"]["title"] == "LOCAL_NOTE_TITLE"
            assert note_after_b["draft"]["title"] == "LOCAL_NOTE_TITLE"
            assert any(s["id"] == "preview-new-b" for s in craft_after_b["published"]["sections"])

            result_c = await target.apply(db, bundle_c, pointer_c, force=True)
            assert result_c["state"] == "applied"

            home_after_c = await db.pages.find_one({"key": "home"}, {"_id": 0})
            site_after_c = await db.settings.find_one({"key": "site"}, {"_id": 0})
            note_after_c = await db.notes.find_one({"slug": note_slug}, {"_id": 0})
            craft_after_c = await db.pages.find_one({"key": "craft-livelihood"}, {"_id": 0})

            assert home_after_c["published"]["title"] == "LOCAL_HOME_TITLE"
            assert site_after_c["header_styles"]["backgroundColor"] == "#efe6d8"
            assert site_after_c["menus"]["main"][0]["label"] == "Local Home Label"
            assert note_after_c["published"]["title"] == "LOCAL_NOTE_TITLE"
            assert any(s["id"] == "preview-new-c" for s in craft_after_c["published"]["sections"])

            # Same release ID force-reapply must still preserve latest local values.
            await db.settings.update_one({"key": "site"}, {"$set": {"header_styles.backgroundColor": "#aabbcc"}})
            result_same = await target.apply(db, bundle_c, pointer_c, force=True)
            assert result_same["state"] == "applied"
            site_after_same = await db.settings.find_one({"key": "site"}, {"_id": 0})
            assert site_after_same["header_styles"]["backgroundColor"] == "#aabbcc"
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_local_section_note_changes_and_source_deletes_preserve_live_content_with_valid_media_refs():
    async def _case():
        bundle_a, pointer_a = _load_package()
        bundle_b = copy.deepcopy(bundle_a)

        page_key = "workshops-learning"
        page_b = _find_page(bundle_b, page_key)
        base_ids = [s["id"] for s in page_b["published"]["sections"]]
        deleted_id = base_ids[2]
        page_b["published"]["sections"][2]["data"]["heading"] = "PREVIEW changed deleted candidate"
        page_b["draft"]["sections"][2]["data"]["heading"] = "PREVIEW changed deleted candidate"
        page_b["published"]["sections"].append({"id": "preview-added-section", "type": "text", "hidden": False, "data": {"heading": "Preview added", "body": "preview incoming"}, "styles": {}})
        page_b["draft"]["sections"].append(copy.deepcopy(page_b["published"]["sections"][-1]))

        note_delete_slug = bundle_b["collections"]["notes"][1]["slug"]
        note_keep_slug = _first_published_note_slug(bundle_b)
        note_delete_preview = _find_note(bundle_b, note_delete_slug)
        if isinstance(note_delete_preview.get("published"), dict):
            note_delete_preview["published"]["title"] = "PREVIEW NOTE UPDATED"
        note_delete_preview["draft"]["title"] = "PREVIEW NOTE UPDATED"

        # Source deletes a locally modified document: incoming removes one note.
        bundle_b["collections"]["notes"] = [n for n in bundle_b["collections"]["notes"] if n["slug"] != note_keep_slug]

        bundle_b, pointer_b = _bundle_with_release_id(bundle_b)

        client, db = await _new_temp_db(prefix="live_edit_sections")
        try:
            await _seed_collections_from_bundle(db, bundle_a)
            await _seed_sentinels(db)
            await target.apply(db, bundle_a, pointer_a, force=True)

            # Local edits: delete/add/reorder sections and note additions/deletions.
            workshops = await db.pages.find_one({"key": page_key}, {"_id": 0})
            local_sections = [s for s in workshops["published"]["sections"] if s["id"] != deleted_id]
            local_sections = [local_sections[1], local_sections[0], *local_sections[2:]]
            local_sections.append({"id": "local-added-section", "type": "text", "hidden": False, "data": {"heading": "Local added", "body": "live local"}, "styles": {}})
            await db.pages.update_one({"key": page_key}, {"$set": {"published.sections": copy.deepcopy(local_sections), "draft.sections": copy.deepcopy(local_sections)}})

            await db.notes.delete_one({"slug": note_delete_slug})
            await db.notes.update_one({"slug": note_keep_slug}, {"$set": {"published.title": "LOCAL KEEP NOTE", "draft.title": "LOCAL KEEP NOTE"}})
            local_note = {
                "id": "local-note-id",
                "slug": "local-live-note",
                "draft": {"title": "Local Live Note", "slug": "local-live-note", "kind": "article", "category": "", "body_html": "<p>local</p>", "seo": {}, "references": [], "downloads": [], "related": [], "tags": [], "author": "", "cover": {}, "credits": "", "standfirst": ""},
                "published": {"title": "Local Live Note", "slug": "local-live-note", "kind": "article", "category": "", "body_html": "<p>local</p>", "seo": {}, "references": [], "downloads": [], "related": [], "tags": [], "author": "", "cover": {}, "credits": "", "standfirst": ""},
                "status": "published",
                "updated_at": "2026-02-01T00:00:00+00:00",
                "published_at": "2026-02-01T00:00:00+00:00",
                "has_unpublished_changes": False,
            }
            await db.notes.insert_one(local_note)

            # Locally edited note should survive even if removed in incoming bundle.
            await db.notes.update_one({"slug": note_keep_slug}, {"$set": {"published.title": "LOCAL KEEP NOTE", "draft.title": "LOCAL KEEP NOTE"}})

            sentinels_before = {
                col: _json_digest(await db[col].find({}, {"_id": 0}).to_list(2000))
                for col in ("users", "enquiries", "register", "login_attempts", "tokens")
            }

            result = await target.apply(db, bundle_b, pointer_b, force=True)
            assert result["state"] == "applied"

            after_workshops = await db.pages.find_one({"key": page_key}, {"_id": 0})
            after_ids = [s["id"] for s in after_workshops["published"]["sections"]]
            assert deleted_id not in after_ids
            assert after_ids[:2] == [local_sections[0]["id"], local_sections[1]["id"]]
            assert "local-added-section" in after_ids
            assert "preview-added-section" in after_ids

            assert await db.notes.find_one({"slug": note_delete_slug}, {"_id": 0}) is None
            keep_note = await db.notes.find_one({"slug": note_keep_slug}, {"_id": 0})
            assert keep_note["published"]["title"] == "LOCAL KEEP NOTE"
            assert await db.notes.find_one({"slug": "local-live-note"}, {"_id": 0}) is not None

            kept_note = await db.notes.find_one({"slug": note_keep_slug}, {"_id": 0})
            assert kept_note is not None
            assert kept_note["published"]["title"] == "LOCAL KEEP NOTE"

            media_ids = {m["id"] for m in await db.media.find({}, {"_id": 0, "id": 1}).to_list(200000)}
            refs = set()
            for page in await db.pages.find({}, {"_id": 0}).to_list(1000):
                refs |= _collect_media_refs(page)
            for note in await db.notes.find({}, {"_id": 0}).to_list(1000):
                refs |= _collect_media_refs(note)
            site = await db.settings.find_one({"key": "site"}, {"_id": 0})
            refs |= _collect_media_refs(site)
            assert refs <= media_ids

            for col in ("users", "enquiries", "register", "login_attempts", "tokens"):
                now_digest = _json_digest(await db[col].find({}, {"_id": 0}).to_list(2000))
                assert now_digest == sentinels_before[col]
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_legacy_without_baseline_and_first_release_with_revisions_preserve_local_text():
    async def _legacy_without_baseline_case():
        bundle_a, pointer_a = _load_package()
        bundle_b = copy.deepcopy(bundle_a)
        _find_page(bundle_b, "home")["published"]["title"] = "PREVIEW LEGACY TITLE"
        _find_page(bundle_b, "home")["draft"]["title"] = "PREVIEW LEGACY TITLE"
        bundle_b, pointer_b = _bundle_with_release_id(bundle_b)

        client, db = await _new_temp_db(prefix="legacy_no_baseline")
        try:
            await _seed_collections_from_bundle(db, bundle_a)
            await db.content_runtime.insert_one({"key": "target", "state": "applied", "release_id": "old_release_id", "backup_id": "old"})
            await db.pages.update_one({"key": "home"}, {"$set": {"published.title": "LOCAL LEGACY TITLE", "draft.title": "LOCAL LEGACY TITLE"}})

            result = await target.apply(db, bundle_b, pointer_b, force=True)
            assert result["state"] == "applied"
            home = await db.pages.find_one({"key": "home"}, {"_id": 0})
            assert home["published"]["title"] == "LOCAL LEGACY TITLE"
        finally:
            await _drop_db(client, db)

    async def _first_release_with_revisions_case():
        bundle_a, _pointer_a = _load_package()
        bundle_b = copy.deepcopy(bundle_a)
        _find_page(bundle_b, "home")["published"]["title"] = "PREVIEW FIRST RELEASE TITLE"
        _find_page(bundle_b, "home")["draft"]["title"] = "PREVIEW FIRST RELEASE TITLE"
        bundle_b, pointer_b = _bundle_with_release_id(bundle_b)

        client, db = await _new_temp_db(prefix="first_release_revisions")
        try:
            await _seed_collections_from_bundle(db, bundle_a)
            await db.revisions.insert_one({"id": "rev-1", "entity_type": "page", "entity_id": "home", "content": {"title": "x"}, "action": "draft saved", "by": "owner@example.com", "created_at": "2026-02-01T00:00:00+00:00"})
            await db.pages.update_one({"key": "home"}, {"$set": {"published.title": "LOCAL FIRST RELEASE TITLE", "draft.title": "LOCAL FIRST RELEASE TITLE"}})

            result = await target.apply(db, bundle_b, pointer_b, force=True)
            assert result["state"] == "applied"
            home = await db.pages.find_one({"key": "home"}, {"_id": 0})
            assert home["published"]["title"] == "LOCAL FIRST RELEASE TITLE"
        finally:
            await _drop_db(client, db)

    _run(_legacy_without_baseline_case())
    _run(_first_release_with_revisions_case())


def test_injected_failure_rolls_back_byte_exact_and_restore_keeps_baseline_intact(monkeypatch):
    async def _case():
        bundle_a, pointer_a = _load_package()
        bundle_b = copy.deepcopy(bundle_a)
        _find_page(bundle_b, "home")["published"]["title"] = "PREVIEW FAILURE TITLE"
        _find_page(bundle_b, "home")["draft"]["title"] = "PREVIEW FAILURE TITLE"
        bundle_b, pointer_b = _bundle_with_release_id(bundle_b)

        client, db = await _new_temp_db(prefix="rollback_exact")
        try:
            await _seed_collections_from_bundle(db, bundle_a)
            await _seed_sentinels(db)
            await target.apply(db, bundle_a, pointer_a, force=True)

            baseline = {
                "pages": _json_digest(await db.pages.find({}, {"_id": 0}).sort("key", 1).to_list(1000)),
                "notes": _json_digest(await db.notes.find({}, {"_id": 0}).sort("slug", 1).to_list(1000)),
                "settings": _json_digest(await db.settings.find({}, {"_id": 0}).sort("key", 1).to_list(10)),
                "content_baselines": _json_digest(await db.content_baselines.find({}, {"_id": 0}).to_list(10)),
                "users": _json_digest(await db.users.find({}, {"_id": 0}).to_list(100)),
                "enquiries": _json_digest(await db.enquiries.find({}, {"_id": 0}).to_list(100)),
                "register": _json_digest(await db.register.find({}, {"_id": 0}).to_list(100)),
            }

            original_replace_one = AsyncIOMotorCollection.replace_one
            state_once = {"done": False}

            async def fail_once(self, *args, **kwargs):
                if not state_once["done"] and self.database.name == db.name and self.name == "pages":
                    state_once["done"] = True
                    raise RuntimeError("injected live-edit failure")
                return await original_replace_one(self, *args, **kwargs)

            monkeypatch.setattr(AsyncIOMotorCollection, "replace_one", fail_once)
            with pytest.raises(RuntimeError):
                await target.apply(db, bundle_b, pointer_b, force=True)

            assert _json_digest(await db.pages.find({}, {"_id": 0}).sort("key", 1).to_list(1000)) == baseline["pages"]
            assert _json_digest(await db.notes.find({}, {"_id": 0}).sort("slug", 1).to_list(1000)) == baseline["notes"]
            assert _json_digest(await db.settings.find({}, {"_id": 0}).sort("key", 1).to_list(10)) == baseline["settings"]
            assert _json_digest(await db.content_baselines.find({}, {"_id": 0}).to_list(10)) == baseline["content_baselines"]
            assert _json_digest(await db.users.find({}, {"_id": 0}).to_list(100)) == baseline["users"]
            assert _json_digest(await db.enquiries.find({}, {"_id": 0}).to_list(100)) == baseline["enquiries"]
            assert _json_digest(await db.register.find({}, {"_id": 0}).to_list(100)) == baseline["register"]
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_runtime_mutation_paths_and_capture_snapshot_include_header_and_text_styles(monkeypatch):
    async def _runtime_case():
        assert runtime.is_content_mutation("/api/admin/header-live") is True
        assert runtime.is_content_mutation("/api/admin/site-live") is True
        assert runtime.is_content_mutation("/api/admin/site-styles") is True

        called = []

        async def fake_prepare():
            called.append("prepare")
            return {"state": "ready"}

        async def fake_is_source(_db, _cfg):
            return True

        monkeypatch.setattr(runtime, "prepare", fake_prepare)
        monkeypatch.setattr(runtime, "config", lambda: {"channel": "x"})
        monkeypatch.setattr(runtime, "is_source", fake_is_source)

        for path in ("/api/admin/header-live", "/api/admin/site-live", "/api/admin/site-styles"):
            out = await runtime.after_mutation(path, "PUT", 200)
            assert out == {"state": "ready"}
        assert len(called) == 3

    async def _capture_case():
        bundle_a, _pointer_a = _load_package()
        client, db = await _new_temp_db(prefix="capture_styles")
        tmp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        tmp_file.close()
        try:
            await _seed_collections_from_bundle(db, bundle_a)
            await db.settings.update_one(
                {"key": "site"},
                {
                    "$set": {
                        "header_styles": {"backgroundColor": "#ffeecc", "brandFontSize": "31px", "fontSize": "19px"},
                        "text_styles": {"display-notes": {"path": "display.notes-title", "area": "main", "styles": {"fontSize": "23px", "color": "#221100"}}},
                    }
                },
            )

            async def fake_is_source(_db, _cfg):
                return True

            monkeypatch.setattr(source, "is_source", fake_is_source)
            monkeypatch.setattr(source, "BUNDLE_FILE", Path(tmp_file.name))

            status = await source.capture(db, force=True, archive=False)
            assert status["state"] == "ready"

            package = json.loads(Path(tmp_file.name).read_text())
            site = package["content"]["site"]
            assert site["header_styles"]["backgroundColor"] == "#ffeecc"
            assert site["header_styles"]["brandFontSize"] == "31px"
            assert site["text_styles"]["display-notes"]["styles"]["fontSize"] == "23px"
        finally:
            Path(tmp_file.name).unlink(missing_ok=True)
            await _drop_db(client, db)

    _run(_runtime_case())
    _run(_capture_case())
