import asyncio
import copy
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

import requests
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorCollection

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from content_sync import runtime, schema, source, state, target
import seed as seed_module


# Content release sync regression tests for backup/apply/restore/validation/state behavior
ROOT = Path(__file__).resolve().parents[1]
PACKAGE_PATH = ROOT / "content_release.json"
REACT_APP_BACKEND_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
OWNER_EMAIL = os.environ.get("ADMIN_EMAIL", "").lower()
OWNER_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")
MONGO_URL = os.environ.get("MONGO_URL")


def _run(coro):
    return asyncio.run(coro)


def _load_package():
    package = json.loads(PACKAGE_PATH.read_text())
    return package["content"], package["manifest"]


def _json_digest(value):
    raw = json.dumps(value, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


async def _new_temp_db(prefix="content_sync_it14"):
    if not MONGO_URL:
        raise AssertionError("MONGO_URL env var is required")
    client = AsyncIOMotorClient(MONGO_URL)
    db_name = f"{prefix}_{uuid.uuid4().hex[:10]}"
    db = client[db_name]
    await state.ensure_indexes(db)
    return client, db


async def _drop_db(client, db):
    await client.drop_database(db.name)
    client.close()


async def _seed_stale_target(db):
    await db.settings.insert_one({
        "key": "site",
        "site_name": "Target Placeholder",
        "menus": {"main": [], "footer": []},
        "theme": {"colors": {}},
        "ui_text": {},
        "email_notifications": {"status": "configured", "provider": "smtp"},
        "indexing_enabled": False,
        "operational_key": "KEEP_ME",
    })
    await db.pages.insert_one({
        "id": "placeholder-page",
        "key": "rakhigarhi",
        "path": "/our-work/rakhigarhi",
        "required": True,
        "status": "published",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "published_at": "2026-01-01T00:00:00+00:00",
        "has_unpublished_changes": False,
        "draft": {"title": "Rakhigarhi", "sections": [{"id": "1", "type": "text", "hidden": False, "data": {"heading": "Draft placeholder"}}], "seo": {}},
        "published": {"title": "Rakhigarhi", "sections": [{"id": "1", "type": "text", "hidden": False, "data": {"heading": "Draft placeholder"}}], "seo": {}},
    })
    await db.notes.insert_one({"id": "old-note", "slug": "workshops-old", "draft": {"title": "old", "sections": []}, "published": {"title": "old", "sections": []}, "status": "published"})
    await db.redirects.insert_one({"from_path": "/old", "to_path": "/new", "code": 301})

    await db.users.insert_one({"id": "u1", "email": "owner@example.com", "password_hash": "$2b$12$abc", "role": "owner", "active": True})
    await db.enquiries.insert_one({"id": "e1", "message": "hello", "status": "new"})
    await db.register.insert_one({"id": "r1", "subject": "legacy", "status": "awaiting upload"})
    await db.login_attempts.insert_one({"identifier": "ip:a@b.c", "count": 3})
    await db.tokens.insert_one({"hash": "tok", "kind": "reset", "user_id": "u1", "used": False})


def test_release_bundle_shape_and_key_counts_match_expected_scope():
    bundle, manifest = _load_package()
    assert bundle["schema"] == 1
    assert manifest["release_id"] == schema.digest(schema.encoded(bundle))
    assert len(bundle["collections"]["pages"]) == 10
    assert len(bundle["collections"]["notes"]) == 3
    # The two owner-supplied Theatre photographs extend the original 63 records.
    assert len(bundle["collections"]["media"]) >= 65
    pages = {p["key"]: p for p in bundle["collections"]["pages"]}
    assert len(pages["rakhigarhi"]["published"]["sections"]) == 9
    assert len(pages["workshops-learning"]["published"]["sections"]) == 9


def test_apply_to_isolated_target_imports_content_and_preserves_sentinels_byte_for_byte():
    async def _case():
        bundle, pointer = _load_package()
        client, db = await _new_temp_db()
        try:
            await _seed_stale_target(db)
            sentinels_before = {}
            for col in ("users", "enquiries", "register", "login_attempts", "tokens"):
                sentinels_before[col] = _json_digest(await db[col].find({}, {"_id": 0}).to_list(1000))

            result = await target.apply(db, bundle, pointer)
            assert result["state"] == "applied"
            assert result["counts"]["pages"] == 10
            assert result["counts"]["notes"] == 3
            assert result["counts"]["media"] == len(bundle["collections"]["media"])
            assert result["counts"]["page_sections"]["rakhigarhi"] == 9
            assert result["counts"]["page_sections"]["workshops-learning"] == 9

            for col in ("users", "enquiries", "register", "login_attempts", "tokens"):
                now_digest = _json_digest(await db[col].find({}, {"_id": 0}).to_list(1000))
                assert now_digest == sentinels_before[col]

            site = await db.settings.find_one({"key": "site"}, {"_id": 0})
            assert site["email_notifications"] == {"status": "configured", "provider": "smtp"}
            assert site["operational_key"] == "KEEP_ME"

            rakhigarhi = await db.pages.find_one({"key": "rakhigarhi"}, {"_id": 0})
            assert len(rakhigarhi["published"]["sections"]) == 9
            workshops = await db.pages.find_one({"key": "workshops-learning"}, {"_id": 0})
            assert len(workshops["published"]["sections"]) == 9
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_second_identical_apply_is_noop_while_force_apply_creates_new_backup():
    async def _case():
        bundle, pointer = _load_package()
        client, db = await _new_temp_db()
        try:
            await _seed_stale_target(db)
            first = await target.apply(db, bundle, pointer, force=False)
            backups_after_first = await db.content_backups.count_documents({})
            second = await target.apply(db, bundle, pointer, force=False)
            backups_after_second = await db.content_backups.count_documents({})
            third = await target.apply(db, bundle, pointer, force=True)
            backups_after_third = await db.content_backups.count_documents({})

            assert first["state"] == "applied"
            assert second.get("unchanged") is True
            assert backups_after_second == backups_after_first
            assert third["state"] == "applied"
            assert backups_after_third == backups_after_first + 1
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_backup_is_created_before_first_write_and_failed_apply_rolls_back_exact_content(monkeypatch):
    async def _case():
        bundle, pointer = _load_package()
        client, db = await _new_temp_db()
        try:
            await _seed_stale_target(db)
            before_pages = await db.pages.find({}, {"_id": 0}).sort("key", 1).to_list(200)
            before_notes = await db.notes.find({}, {"_id": 0}).sort("slug", 1).to_list(200)
            before_site = await db.settings.find_one({"key": "site"}, {"_id": 0})
            before_users = _json_digest(await db.users.find({}, {"_id": 0}).to_list(100))
            before_enquiries = _json_digest(await db.enquiries.find({}, {"_id": 0}).to_list(100))

            original_replace_one = AsyncIOMotorCollection.replace_one
            state_once = {"done": False}

            async def fail_once(self, *args, **kwargs):
                if (
                    not state_once["done"]
                    and self.database.name == db.name
                    and self.name == "pages"
                ):
                    state_once["done"] = True
                    raise RuntimeError("injected one-shot write error")
                return await original_replace_one(self, *args, **kwargs)

            monkeypatch.setattr(AsyncIOMotorCollection, "replace_one", fail_once)
            try:
                await target.apply(db, bundle, pointer, force=True)
                raise AssertionError("apply should fail with injected error")
            except RuntimeError:
                pass

            backups = await db.content_backups.find({}, {"_id": 0}).to_list(20)
            assert len(backups) >= 1
            assert backups[0]["state"] == "ready"

            after_pages = await db.pages.find({}, {"_id": 0}).sort("key", 1).to_list(200)
            after_notes = await db.notes.find({}, {"_id": 0}).sort("slug", 1).to_list(200)
            after_site = await db.settings.find_one({"key": "site"}, {"_id": 0})
            after_users = _json_digest(await db.users.find({}, {"_id": 0}).to_list(100))
            after_enquiries = _json_digest(await db.enquiries.find({}, {"_id": 0}).to_list(100))

            assert after_pages == before_pages
            assert after_notes == before_notes
            assert after_site == before_site
            assert after_users == before_users
            assert after_enquiries == before_enquiries
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_manual_restore_creates_safety_backup_and_invalid_restore_rejected_without_mutation():
    async def _case():
        bundle, pointer = _load_package()
        client, db = await _new_temp_db()
        try:
            await _seed_stale_target(db)
            first = await target.apply(db, bundle, pointer, force=True)
            applied_backup_id = first["backup_id"]

            await db.pages.update_one({"key": "rakhigarhi"}, {"$set": {"published.title": "BROKEN TEST TITLE"}})
            restored = await target.restore(db, applied_backup_id)
            assert restored["restored"] == applied_backup_id
            assert restored["safety_backup_id"]

            page = await db.pages.find_one({"key": "rakhigarhi"}, {"_id": 0})
            assert "BROKEN TEST TITLE" not in json.dumps(page)

            before_count = await db.content_backups.count_documents({})
            try:
                await target.restore(db, "bad-backup-id")
                raise AssertionError("invalid backup should fail")
            except ValueError:
                pass
            after_count = await db.content_backups.count_documents({})
            assert after_count == before_count
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_schema_validation_rejects_invalid_release_before_any_content_write():
    async def _case():
        bundle, pointer = _load_package()
        client, db = await _new_temp_db()
        try:
            await _seed_stale_target(db)
            baseline_pages = await db.pages.count_documents({})

            broken = copy.deepcopy(bundle)
            broken["collections"]["pages"] = [p for p in broken["collections"]["pages"] if p["key"] != "home"]
            try:
                await target.apply(db, broken, pointer, force=True)
                raise AssertionError("apply must fail validation")
            except ValueError:
                pass

            assert await db.content_backups.count_documents({}) == 0
            assert await db.pages.count_documents({}) == baseline_pages

            duplicate = copy.deepcopy(bundle)
            duplicate["collections"]["pages"][1]["key"] = duplicate["collections"]["pages"][0]["key"]
            try:
                schema.validate(duplicate, schema.config())
                raise AssertionError("duplicate identities must fail")
            except ValueError:
                pass
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_source_identity_clone_in_target_db_still_classifies_as_target_not_source():
    async def _case():
        cfg = schema.config()
        client, db = await _new_temp_db()
        try:
            await db.content_runtime.insert_one({"key": "identity", "environment_id": cfg["source_id"]})
            assert await state.environment_id(db) == cfg["source_id"]
            assert await state.is_source(db, cfg) is False
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_source_database_cannot_import_its_own_release_when_classified_as_source(monkeypatch):
    async def _case():
        bundle, pointer = _load_package()
        client, db = await _new_temp_db()
        try:
            monkeypatch.setattr(target, "is_source", lambda *_args, **_kwargs: asyncio.sleep(0, result=True))
            try:
                await target.apply(db, bundle, pointer, force=True)
                raise AssertionError("source should not import its own release")
            except ValueError as e:
                assert "cannot import its own deployment release" in str(e)
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_runtime_startup_uses_baked_snapshot_not_runtime_latest_pointer(monkeypatch):
    async def _case():
        bundle, pointer = _load_package()
        client, db = await _new_temp_db(prefix="content_sync_startup")
        try:
            await _seed_stale_target(db)
            await db.content_releases.insert_one({
                "release_id": "f" * 64,
                "manifest": {"release_id": "f" * 64},
                "content": {"schema": 1},
            })
            captured = {}

            async def fake_apply(database, b, p):
                captured["db"] = database.name
                captured["release_id"] = p["release_id"]
                return {"state": "applied", "release_id": p["release_id"], "counts": {"pages": len(b["collections"]["pages"])}}

            monkeypatch.setattr(runtime, "db", db)
            monkeypatch.setattr(runtime, "prepare", lambda: asyncio.sleep(0, result={"state": "ready"}))
            monkeypatch.setattr(runtime, "apply", fake_apply)
            monkeypatch.setattr(runtime, "baked", lambda: (bundle, pointer))
            await runtime.startup()

            assert captured["db"] == db.name
            assert captured["release_id"] == pointer["release_id"]
            assert captured["release_id"] != ("f" * 64)
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_seed_create_only_preserves_existing_owner_hash_role_and_does_not_resurrect_empty_notes_register(monkeypatch):
    async def _case():
        client, db = await _new_temp_db(prefix="seed_create_only")
        try:
            existing_hash = "$2b$12$existinghashvalue"
            await db.users.insert_one({"id": "owner-1", "email": "owner@existing.test", "name": "Owner", "role": "owner", "active": True, "password_hash": existing_hash, "created_at": "2026-01-01T00:00:00+00:00"})
            await db.settings.insert_one({"key": "site", "site_name": "Existing"})
            monkeypatch.setattr(seed_module, "db", db)
            monkeypatch.setenv("ADMIN_EMAIL", "changed-owner@example.com")
            monkeypatch.setenv("ADMIN_PASSWORD", "Completely-Different-Password-123")

            await seed_module.seed()
            user = await db.users.find_one({"id": "owner-1"}, {"_id": 0})
            assert user["email"] == "owner@existing.test"
            assert user["role"] == "owner"
            assert user["password_hash"] == existing_hash
            assert await db.notes.count_documents({}) == 0
            assert await db.register.count_documents({}) == 0
        finally:
            await _drop_db(client, db)

    _run(_case())


def test_seed_initial_empty_install_creates_owner_in_isolated_db(monkeypatch):
    async def _case():
        client, db = await _new_temp_db(prefix="seed_initial_owner")
        try:
            monkeypatch.setattr(seed_module, "db", db)
            monkeypatch.setenv("ADMIN_EMAIL", "isolated-owner@example.com")
            monkeypatch.setenv("ADMIN_PASSWORD", "Owner-Pass-For-Isolated-Install-123")
            await seed_module.seed()
            owners = await db.users.find({"email": "isolated-owner@example.com"}, {"_id": 0}).to_list(10)
            assert len(owners) == 1
            assert owners[0]["role"] == "owner"
            assert owners[0]["password_hash"].startswith("$2b$")
        finally:
            await _drop_db(client, db)

    _run(_case())


# Real preview API checks for content-release auth/permissions and middleware auto-capture
def test_content_release_endpoints_reject_anonymous_requests():
    if not REACT_APP_BACKEND_URL:
        raise AssertionError("REACT_APP_BACKEND_URL is required")
    anon = requests.Session()
    for method, path in [
        ("get", "/api/admin/content-release"),
        ("post", "/api/admin/content-release/prepare"),
        ("post", "/api/admin/content-release/apply"),
        ("post", "/api/admin/content-release/restore/invalid"),
    ]:
        kwargs = {"timeout": 30}
        if path.endswith("/invalid"):
            kwargs["json"] = {"confirm": False}
        response = getattr(anon, method)(f"{REACT_APP_BACKEND_URL}{path}", **kwargs)
        assert response.status_code == 401


def test_preview_source_apply_endpoint_rejects_source_self_import():
    if not (REACT_APP_BACKEND_URL and OWNER_EMAIL and OWNER_PASSWORD):
        raise AssertionError("Preview URL and owner credentials are required")
    s = requests.Session()
    login = s.post(f"{REACT_APP_BACKEND_URL}/api/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=30)
    assert login.status_code == 200
    csrf = s.cookies.get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})

    response = s.post(f"{REACT_APP_BACKEND_URL}/api/admin/content-release/apply", timeout=60)
    assert response.status_code == 409
    assert "cannot import" in response.text.lower()


def test_mutating_preview_draft_auto_updates_baked_release_without_changing_published_and_then_restores():
    if not (REACT_APP_BACKEND_URL and OWNER_EMAIL and OWNER_PASSWORD):
        raise AssertionError("Preview URL and owner credentials are required")

    initial_package = json.loads(PACKAGE_PATH.read_text())
    initial_release = initial_package["manifest"]["release_id"]

    s = requests.Session()
    login = s.post(f"{REACT_APP_BACKEND_URL}/api/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=30)
    assert login.status_code == 200
    csrf = s.cookies.get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})

    get_home = s.get(f"{REACT_APP_BACKEND_URL}/api/admin/pages/home", timeout=30)
    assert get_home.status_code == 200
    home = get_home.json()
    original_draft = copy.deepcopy(home["draft"])
    original_published = copy.deepcopy(home["published"])
    marker = f" [SYNC_TEST_{uuid.uuid4().hex[:8]}]"

    try:
        changed = copy.deepcopy(original_draft)
        changed["title"] = (changed.get("title") or "Home") + marker
        save = s.put(
            f"{REACT_APP_BACKEND_URL}/api/admin/pages/home/draft",
            json={"title": changed["title"], "sections": changed.get("sections", []), "seo": changed.get("seo", {})},
            timeout=60,
        )
        assert save.status_code == 200
        assert save.headers.get("X-Content-Release-State") in {"ready", "pending"}

        package_after_change = json.loads(PACKAGE_PATH.read_text())
        changed_release = package_after_change["manifest"]["release_id"]
        assert changed_release != initial_release
        pages_after = {p["key"]: p for p in package_after_change["content"]["collections"]["pages"]}
        assert marker in pages_after["home"]["draft"]["title"]
        assert pages_after["home"]["published"]["title"] == original_published["title"]

    finally:
        restore = s.put(
            f"{REACT_APP_BACKEND_URL}/api/admin/pages/home/draft",
            json={
                "title": original_draft.get("title", "Home"),
                "sections": original_draft.get("sections", []),
                "seo": original_draft.get("seo", {}),
            },
            timeout=60,
        )
        assert restore.status_code == 200

    clean_package = json.loads(PACKAGE_PATH.read_text())
    clean_pages = {p["key"]: p for p in clean_package["content"]["collections"]["pages"]}
    assert marker not in json.dumps(clean_pages["home"]) 
    assert clean_pages["home"]["draft"]["title"] == original_draft.get("title", "Home")
    assert clean_pages["home"]["published"]["title"] == original_published["title"]
