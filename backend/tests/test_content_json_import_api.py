import asyncio
import copy
import json
import os
import sys
import uuid
from pathlib import Path

import pytest
import requests
from fastapi import HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from motor.motor_asyncio import AsyncIOMotorCollection

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from content_json import service
from content_sync.state import ensure_indexes


# Content JSON parsing/import/service/API regression coverage
ROOT = Path(__file__).resolve().parents[1]
FRONTEND_ENV = Path("/app/frontend/.env")
CONTENT_RELEASE = ROOT / "content_release.json"


def _frontend_url():
    for line in FRONTEND_ENV.read_text(encoding="utf-8").splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().strip('"').rstrip("/")
    return ""


BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or _frontend_url()).rstrip("/")
OWNER_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()
OWNER_PASSWORD = os.environ.get("ADMIN_PASSWORD", "").strip()
MONGO_URL = os.environ.get("MONGO_URL")


def _load_release_content():
    payload = json.loads(CONTENT_RELEASE.read_text(encoding="utf-8"))
    return payload["content"]


def _load_import_doc():
    content = _load_release_content()
    return {
        "format": "usp-content-json",
        "version": 1,
        "schema": 1,
        "collections": {
            "pages": copy.deepcopy(content["collections"]["pages"]),
            "notes": copy.deepcopy(content["collections"]["notes"]),
            "media": copy.deepcopy(content["collections"]["media"]),
            "redirects": copy.deepcopy(content["collections"]["redirects"]),
        },
        "site": copy.deepcopy(content["site"]),
    }


def _encoded_doc(doc):
    return json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def _run(coro):
    return asyncio.run(coro)


async def _new_temp_db():
    if not MONGO_URL:
        raise AssertionError("MONGO_URL env var is required")
    client = AsyncIOMotorClient(MONGO_URL)
    db_name = f"content_json_it20_{uuid.uuid4().hex[:10]}"
    db = client[db_name]
    await ensure_indexes(db)
    return client, db


async def _drop_temp_db(client, db):
    await client.drop_database(db.name)
    client.close()


async def _seed_from_release(db):
    doc = _load_import_doc()
    for name, rows in doc["collections"].items():
        if rows:
            await db[name].insert_many(copy.deepcopy(rows))
    await db.settings.update_one({"key": "site"}, {"$set": copy.deepcopy(doc["site"])}, upsert=True)
    return doc


def _owner_client():
    if not BASE_URL or not OWNER_EMAIL or not OWNER_PASSWORD:
        pytest.skip("Preview URL and owner credentials are required")
    session = requests.Session()
    login = session.post(f"{BASE_URL}/api/auth/login", json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD}, timeout=30)
    if login.status_code != 200:
        pytest.skip(f"Owner login failed: {login.status_code}")
    csrf = session.cookies.get("csrf_token")
    if csrf:
        session.headers.update({"X-CSRF-Token": csrf})
    return session


# Schema parser validation: accept legacy shape, reject malformed payloads before writes
def test_parse_rejects_non_object_root_and_bad_version():
    with pytest.raises(HTTPException) as root_error:
        service.parse(b"[]")
    assert root_error.value.status_code == 400

    bad_version = {"version": 2, "schema": 1, "collections": {"pages": [], "notes": [], "media": [], "redirects": []}}
    with pytest.raises(HTTPException) as version_error:
        service.parse(_encoded_doc(bad_version))
    assert version_error.value.status_code == 400
    assert "not supported" in str(version_error.value.detail).lower()


def test_parse_allows_legacy_backup_shape_and_ignores_non_content_collections():
    doc = _load_import_doc()
    legacy = {
        "version": 1,
        "schema": 1,
        "collections": {
            **doc["collections"],
            "settings": [{"key": "site", "site_name": doc["site"].get("site_name", "")}, {"key": "email_notifications", "status": "configured"}],
            "users": [{"email": "ignore@example.com"}],
            "enquiries": [{"id": "ignore-me"}],
        },
    }
    parsed = service.parse(_encoded_doc(legacy))
    assert parsed["site"].get("site_name") == doc["site"].get("site_name", "")
    assert set(parsed["collections"].keys()) == {"pages", "notes", "media", "redirects"}


def test_parse_rejects_duplicate_page_keys_and_invalid_media_paths():
    doc = _load_import_doc()
    bad = copy.deepcopy(doc)
    bad["collections"]["pages"][0]["key"] = bad["collections"]["pages"][1]["key"]
    with pytest.raises(HTTPException) as duplicate:
        service.parse(_encoded_doc(bad))
    assert duplicate.value.status_code == 400

    bad_path = _load_import_doc()
    bad_path["collections"]["media"][0]["original_path"] = "../outside"
    with pytest.raises(HTTPException) as path_error:
        service.parse(_encoded_doc(bad_path))
    assert path_error.value.status_code == 400


# Service-level import behavior: merge, validation, optimistic-locking and rollback
def test_plan_import_detects_missing_media_reference_before_apply():
    async def _case():
        client, db = await _new_temp_db()
        try:
            doc = await _seed_from_release(db)
            target = copy.deepcopy(doc)
            target["collections"]["pages"][0]["published"]["sections"][0]["data"]["image"] = {"media_id": "missing-media-id"}
            with pytest.raises(HTTPException) as missing:
                await service.plan_import(db, _encoded_doc(target))
            assert missing.value.status_code == 400
            assert "missing" in str(missing.value.detail).lower()
        finally:
            await _drop_temp_db(client, db)

    _run(_case())


def test_apply_import_rejects_sha_or_state_mismatch_without_writing():
    async def _case():
        client, db = await _new_temp_db()
        try:
            baseline = await _seed_from_release(db)
            payload = copy.deepcopy(baseline)
            payload["collections"]["pages"][0]["published"]["title"] = "TEST_TITLE_FOR_MISMATCH"
            raw = _encoded_doc(payload)
            plan = await service.plan_import(db, raw)
            with pytest.raises(HTTPException) as sha_error:
                await service.apply_import(db, raw, "0" * 64, plan["state"], "tester@example.com")
            assert sha_error.value.status_code == 409

            with pytest.raises(HTTPException) as state_error:
                await service.apply_import(db, raw, plan["sha256"], "f" * 64, "tester@example.com")
            assert state_error.value.status_code == 409

            page = await db.pages.find_one({"key": payload["collections"]["pages"][0]["key"]}, {"_id": 0})
            assert page["published"]["title"] != "TEST_TITLE_FOR_MISMATCH"
        finally:
            await _drop_temp_db(client, db)

    _run(_case())


def test_apply_import_rolls_back_after_mid_write_failure_and_keeps_backup(monkeypatch):
    async def _case():
        client, db = await _new_temp_db()
        try:
            baseline = await _seed_from_release(db)
            payload = copy.deepcopy(baseline)
            payload["collections"]["pages"][0]["published"]["title"] = "TEST_ROLLBACK_TITLE"
            raw = _encoded_doc(payload)
            plan = await service.plan_import(db, raw)

            original_replace = AsyncIOMotorCollection.replace_one
            hit = {"done": False}

            async def fail_once(self, *args, **kwargs):
                if self.database.name == db.name and self.name == "pages" and not hit["done"]:
                    hit["done"] = True
                    raise RuntimeError("injected import write failure")
                return await original_replace(self, *args, **kwargs)

            monkeypatch.setattr(AsyncIOMotorCollection, "replace_one", fail_once)

            with pytest.raises(HTTPException) as failed:
                await service.apply_import(db, raw, plan["sha256"], plan["state"], "tester@example.com")
            assert failed.value.status_code == 500
            assert "restored" in str(failed.value.detail).lower()

            restored = await db.pages.find_one({"key": baseline["collections"]["pages"][0]["key"]}, {"_id": 0})
            assert restored["published"]["title"] == baseline["collections"]["pages"][0]["published"]["title"]

            backups = await db.content_backups.find({}, {"_id": 0}).to_list(20)
            assert backups and backups[0]["state"] == "ready"
        finally:
            await _drop_temp_db(client, db)

    _run(_case())


def test_apply_import_partial_payload_preserves_unlisted_records_and_ignores_users_enquiries():
    async def _case():
        client, db = await _new_temp_db()
        try:
            baseline = await _seed_from_release(db)
            sentinel_note = {
                "id": "sentinel-note-id",
                "slug": "sentinel-note",
                "status": "draft",
                "draft": {"title": "Sentinel", "sections": []},
                "published": None,
            }
            await db.notes.insert_one(copy.deepcopy(sentinel_note))
            await db.users.insert_one({"id": "user-1", "email": "keep@domain.com"})
            await db.enquiries.insert_one({"id": "enq-1", "message": "keep"})

            payload = {
                "version": 1,
                "schema": 1,
                "collections": {
                    "pages": [copy.deepcopy(baseline["collections"]["pages"][0])],
                    "notes": [],
                    "media": [],
                    "redirects": [],
                    "users": [{"id": "user-x", "email": "ignore@import.com"}],
                    "enquiries": [{"id": "enq-x"}],
                },
            }
            raw = _encoded_doc(payload)
            plan = await service.plan_import(db, raw)
            result = await service.apply_import(db, raw, plan["sha256"], plan["state"], "tester@example.com")
            assert result["ok"] is True

            untouched = await db.notes.find_one({"slug": "sentinel-note"}, {"_id": 0})
            assert untouched is not None
            assert untouched["draft"]["title"] == "Sentinel"

            users = await db.users.find({}, {"_id": 0}).to_list(20)
            enquiries = await db.enquiries.find({}, {"_id": 0}).to_list(20)
            assert len(users) == 1 and users[0]["email"] == "keep@domain.com"
            assert len(enquiries) == 1 and enquiries[0]["id"] == "enq-1"
        finally:
            await _drop_temp_db(client, db)

    _run(_case())


# Public API regression: auth boundaries + content JSON export/preview/import/backup endpoints
def test_content_json_endpoints_require_auth():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    anon = requests.Session()
    response = anon.get(f"{BASE_URL}/api/admin/content-export", timeout=30)
    assert response.status_code == 401


def test_content_json_export_preview_import_roundtrip_and_backup_download():
    owner = _owner_client()
    export_response = owner.get(f"{BASE_URL}/api/admin/content-export", timeout=120)
    assert export_response.status_code == 200
    exported = export_response.content
    exported_json = json.loads(exported.decode("utf-8"))
    assert exported_json.get("format") == "usp-content-json"
    assert exported_json.get("version") == 1

    files = {"file": ("roundtrip.json", exported, "application/json")}
    preview = owner.post(f"{BASE_URL}/api/admin/content-import/preview", files=files, timeout=120)
    assert preview.status_code == 200
    info = preview.json()
    assert info["counts"]["pages"]["total"] >= 10

    import_response = owner.post(
        f"{BASE_URL}/api/admin/content-import",
        files=files,
        data={"expected_sha256": info["sha256"], "expected_state": info["state"]},
        timeout=180,
    )
    assert import_response.status_code == 200
    body = import_response.json()
    assert body.get("ok") is True
    assert body["counts"]["pages"]["unchanged"] >= 1

    backup = owner.get(f"{BASE_URL}/api/admin/content-import/backups/{body['backup_id']}", timeout=120)
    assert backup.status_code == 200
    backup_doc = json.loads(backup.content.decode("utf-8"))
    assert set(backup_doc["collections"].keys()) == {"pages", "notes", "media", "redirects"}


def test_content_json_api_rejects_wrong_file_type_and_oversize():
    owner = _owner_client()
    wrong = owner.post(
        f"{BASE_URL}/api/admin/content-import/preview",
        files={"file": ("bad.txt", b"not-json", "text/plain")},
        timeout=30,
    )
    assert wrong.status_code == 400

    oversized = owner.post(
        f"{BASE_URL}/api/admin/content-import/preview",
        files={"file": ("too-big.json", b"{" + (b" " * (12 * 1024 * 1024 + 2)) + b"}", "application/json")},
        timeout=60,
    )
    assert oversized.status_code == 413


def test_content_json_api_digest_mismatch_returns_409_without_writing():
    owner = _owner_client()
    export_response = owner.get(f"{BASE_URL}/api/admin/content-export", timeout=120)
    assert export_response.status_code == 200
    payload = json.loads(export_response.content.decode("utf-8"))

    pages = payload.get("collections", {}).get("pages", [])
    about = next((p for p in pages if p.get("key") == "about"), None)
    assert about is not None
    baseline = about["published"]["sections"][0]["data"]["heading"]

    for page in pages:
        if page.get("key") == "about":
            page["published"]["sections"][0]["data"]["heading"] = "TEST_DIGEST_MISMATCH_SHOULD_NOT_SAVE"
            page["draft"]["sections"][0]["data"]["heading"] = "TEST_DIGEST_MISMATCH_SHOULD_NOT_SAVE"

    changed = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    files = {"file": ("changed.json", changed, "application/json")}
    preview = owner.post(f"{BASE_URL}/api/admin/content-import/preview", files=files, timeout=120)
    assert preview.status_code == 200
    plan = preview.json()

    mismatch = owner.post(
        f"{BASE_URL}/api/admin/content-import",
        files=files,
        data={"expected_sha256": "0" * 64, "expected_state": plan["state"]},
        timeout=120,
    )
    assert mismatch.status_code == 409

    public_about = owner.get(f"{BASE_URL}/api/public/pages/about", timeout=60)
    assert public_about.status_code == 200
    after_heading = public_about.json()["content"]["sections"][0]["data"]["heading"]
    assert after_heading == baseline
