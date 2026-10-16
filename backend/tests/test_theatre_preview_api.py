import hashlib
import json
import os
import re
import uuid
from pathlib import Path

import pytest
import requests


# Theatre preview API/auth regressions: media integrity, structure/copy, anchors, SSR, and safety checks.
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
THEATRE_PAGE = "theatre"
THEATRE_HERO_ID = "066851c267384af38915014947dd6e0b"
THEATRE_ARCHIVE_ID = "2ebb2389301f4b2c8375de4c2318181e"
BACKUP_PATH = Path("/app/memory/backups/theatre-reference-2026-10-16.json")
RELEASE_PATH = Path("/app/backend/content_release.json")


def _read_owner_credentials():
    text = Path("/app/memory/test_credentials.md").read_text(encoding="utf-8")
    email_match = re.search(r"Email:\s*([^\s]+)", text)
    pwd_match = re.search(r"Password:\s*(.+)", text)
    if not email_match or not pwd_match:
        pytest.skip("Owner credentials missing in /app/memory/test_credentials.md")
    return {"email": email_match.group(1).strip(), "password": pwd_match.group(1).strip()}


@pytest.fixture(scope="module")
def api_base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="module")
def owner_session(api_base_url):
    creds = _read_owner_credentials()
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    login = s.post(f"{api_base_url}/api/auth/login", json=creds, timeout=30)
    assert login.status_code == 200
    assert "access_token" in s.cookies
    assert "refresh_token" in s.cookies
    assert "csrf_token" in s.cookies
    csrf = s.cookies.get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


def _page_data(api_base_url, key):
    r = requests.get(f"{api_base_url}/api/public/pages/{key}", timeout=30)
    assert r.status_code == 200
    return r.json()


def test_cors_allows_credentials_with_explicit_origin(api_base_url):
    response = requests.options(
        f"{api_base_url}/api/auth/login",
        headers={
            "Origin": api_base_url,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == api_base_url
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_login_sets_http_only_tokens(api_base_url):
    creds = _read_owner_credentials()
    s = requests.Session()
    r = s.post(f"{api_base_url}/api/auth/login", json=creds, timeout=30)
    assert r.status_code == 200
    cookie_header = ",".join(r.raw.headers.get_all("Set-Cookie") if hasattr(r.raw.headers, "get_all") else [r.headers.get("set-cookie", "")])
    assert "access_token" in cookie_header and "HttpOnly" in cookie_header
    assert "refresh_token" in cookie_header and "HttpOnly" in cookie_header
    assert "csrf_token" in cookie_header


def test_brute_force_lockout_after_five_failures(api_base_url):
    client = requests.Session()
    fake_email = f"lockout-{uuid.uuid4().hex[:8]}@example.com"
    statuses = []
    for _ in range(6):
        r = client.post(f"{api_base_url}/api/auth/login", json={"email": fake_email, "password": "wrong-password"}, timeout=30)
        statuses.append(r.status_code)
    assert statuses[:5] == [401, 401, 401, 401, 401]
    assert statuses[5] == 429


def test_theatre_public_sections_and_copy_match_reference(api_base_url):
    payload = _page_data(api_base_url, THEATRE_PAGE)
    sections = payload["content"]["sections"]
    assert len(sections) == 6
    by_eyebrow = {s["data"].get("eyebrow"): s for s in sections}
    assert by_eyebrow["Theatre"]["data"]["heading"] == "Stories Brought to Life. Conversations Opened."
    assert by_eyebrow["Culture in Everyday Life"]["data"]["heading"] == "The Worlds We Live In."
    assert by_eyebrow["Theatre Over Time"]["data"]["heading"] == "More Than a Decade of Original Work."
    assert by_eyebrow["Current Production"]["data"]["subheading"] == "A Familiar Setting. A Contemporary Conversation."
    assert by_eyebrow["The Ambition"]["data"]["heading"] == "Stories That Travel\nBeyond the Stage."
    assert by_eyebrow["Stay Connected with USP Theatre"]["data"]["href"] == "/connect"


def test_theatre_media_ids_and_public_files_are_resolved(api_base_url):
    payload = _page_data(api_base_url, THEATRE_PAGE)
    sections = payload["content"]["sections"]
    hero = next(s for s in sections if s["type"] == "hero")
    archive = next(s for s in sections if s["data"].get("layout") == "theatre-archive")
    assert hero["data"]["image"]["media_id"] == THEATRE_HERO_ID
    assert archive["data"]["image"]["media_id"] == THEATRE_ARCHIVE_ID

    hero_src = hero["data"]["image"]["media"]["src"]
    archive_src = archive["data"]["image"]["media"]["src"]
    hero_file = requests.get(f"{api_base_url}{hero_src}", timeout=30)
    archive_file = requests.get(f"{api_base_url}{archive_src}", timeout=30)
    assert hero_file.status_code == 200 and len(hero_file.content) > 1000
    assert archive_file.status_code == 200 and len(archive_file.content) > 1000


def test_theatre_existing_anchor_links_preserved(api_base_url):
    payload = _page_data(api_base_url, THEATRE_PAGE)
    sections = payload["content"]["sections"]
    archive = next(s for s in sections if s["data"].get("layout") == "theatre-archive")
    production = next(s for s in sections if s["data"].get("layout") == "theatre-production")
    assert archive["data"]["link_href"] == "/our-work/theatre#past-work"
    assert production["data"]["link_href"] == "/our-work/theatre#prayer-meeting"


def test_admin_live_theatre_has_hidden_notes_and_new_connect(owner_session, api_base_url):
    live = owner_session.get(f"{api_base_url}/api/admin/pages/theatre/live", timeout=30)
    assert live.status_code == 200
    sections = live.json()["content"]["sections"]
    assert len(sections) == 7
    assert any(s["type"] == "notes_feed" and s.get("hidden") for s in sections)
    assert any(s["type"] == "contact_invite" and s["data"].get("anchor") == "theatre-connect" for s in sections)


def test_backup_theatre_ids_retained_with_new_connect(owner_session, api_base_url):
    if not BACKUP_PATH.exists():
        pytest.skip("Backup snapshot file missing")
    backup = json.loads(BACKUP_PATH.read_text())
    prev_page = next(p for p in backup["pages"] if p["key"] == "theatre")
    prev_ids = {s["id"] for s in prev_page["published"]["sections"]}
    current = owner_session.get(f"{api_base_url}/api/admin/pages/theatre/live", timeout=30)
    assert current.status_code == 200
    current_sections = current.json()["content"]["sections"]
    current_ids = {s["id"] for s in current_sections}
    assert prev_ids.issubset(current_ids)
    assert len(current_ids - prev_ids) == 1


def test_theatre_release_bundle_counts_and_media_presence():
    if not RELEASE_PATH.exists():
        pytest.skip("content_release.json missing")
    release = json.loads(RELEASE_PATH.read_text())
    content = release["content"]
    pages = {p["key"]: p for p in content["collections"]["pages"]}
    theatre_sections = pages["theatre"]["published"]["sections"]
    assert len(theatre_sections) == 7
    assert len(pages["rakhigarhi"]["published"]["sections"]) == 9
    assert len(pages["workshops-learning"]["published"]["sections"]) == 9
    media_ids = {m["id"] for m in content["collections"]["media"]}
    assert THEATRE_HERO_ID in media_ids
    assert THEATRE_ARCHIVE_ID in media_ids


def test_ssr_contains_theatre_intro_question_and_links(api_base_url):
    r = requests.get(f"{api_base_url}/api/ssr", params={"path": "/our-work/theatre"}, timeout=30)
    assert r.status_code == 200
    html = r.text
    assert "Original stories rooted in the world around us." in html
    assert "Beneath the humour lies a question:" in html
    assert "/our-work/theatre#past-work" in html
    assert "/our-work/theatre#prayer-meeting" in html


def test_apply_theatre_script_second_run_is_noop():
    script = Path("/app/backend/scripts/apply_theatre_reference.py")
    text = script.read_text(encoding="utf-8")
    assert "if page.get(\"design_migration\") == VERSION" in text
    assert "Already applied; saved edits unchanged" in text
    assert "if __name__ == \"__main__\"" in text


def test_our_work_dropdown_stays_four_items_without_grandchildren(api_base_url):
    site = requests.get(f"{api_base_url}/api/public/site", timeout=30)
    assert site.status_code == 200
    main = site.json()["menus"]["main"]
    our_work = next(item for item in main if item.get("href") == "/our-work")
    children = our_work.get("children") or []
    assert len(children) == 4
    assert all(not (child.get("children") or []) for child in children)


def test_local_reference_asset_hash_check_if_assets_exist(owner_session, api_base_url):
    """Environment-dependent asset SHA check against downloaded bytes (fails when local assets are missing)."""
    asset_dir = Path("/app/assets/theatre")
    if not asset_dir.exists():
        pytest.fail("Local reference assets directory missing: /app/assets/theatre")

    payload = _page_data(api_base_url, THEATRE_PAGE)
    sections = payload["content"]["sections"]
    hero = next(s for s in sections if s["type"] == "hero")
    archive = next(s for s in sections if s["data"].get("layout") == "theatre-archive")

    hero_local = (asset_dir / "joyful-dance.png").read_bytes()
    archive_local = (asset_dir / "dramatic-trio.png").read_bytes()

    hero_resp = owner_session.get(f"{api_base_url}/api/admin/media/{hero['data']['image']['media_id']}/original", timeout=30)
    archive_resp = owner_session.get(f"{api_base_url}/api/admin/media/{archive['data']['image']['media_id']}/original", timeout=30)
    assert hero_resp.status_code == 200
    assert archive_resp.status_code == 200
    hero_remote = hero_resp.content
    archive_remote = archive_resp.content

    assert hashlib.sha256(hero_local).hexdigest() == hashlib.sha256(hero_remote).hexdigest()
    assert hashlib.sha256(archive_local).hexdigest() == hashlib.sha256(archive_remote).hexdigest()