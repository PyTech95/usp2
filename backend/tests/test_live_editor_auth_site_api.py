import os
import uuid

import pytest
import requests


# Auth + live-editor API regression coverage for login/session/cors/site-live patching
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
OWNER_EMAIL = os.environ.get("ADMIN_EMAIL")
OWNER_PASSWORD = os.environ.get("ADMIN_PASSWORD")
ALLOWED_ORIGIN = os.environ.get("CORS_ORIGINS", "").split(",")[0].strip()


@pytest.fixture(scope="session")
def api_base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def owner_credentials():
    if not OWNER_EMAIL or not OWNER_PASSWORD:
        pytest.skip("ADMIN_EMAIL / ADMIN_PASSWORD env vars are required for auth tests")
    return {"email": OWNER_EMAIL, "password": OWNER_PASSWORD}


@pytest.fixture
def anon_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture
def auth_client(api_base_url, owner_credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    login = s.post(f"{api_base_url}/api/auth/login", json=owner_credentials, timeout=20)
    if login.status_code != 200:
        pytest.skip(f"Owner login failed: {login.status_code}")
    csrf_token = s.cookies.get("csrf_token")
    if csrf_token:
        s.headers.update({"X-CSRF-Token": csrf_token})
    return s


# Auth basics: health + login + cookie contract + user permission surface
def test_health_ok(anon_client, api_base_url):
    response = anon_client.get(f"{api_base_url}/api/health", timeout=20)
    assert response.status_code == 200
    assert response.json().get("ok") is True


def test_login_sets_http_only_session_cookies(anon_client, api_base_url, owner_credentials):
    response = anon_client.post(f"{api_base_url}/api/auth/login", json=owner_credentials, timeout=20)
    assert response.status_code == 200
    set_cookie = "\n".join(response.raw.headers.get_all("Set-Cookie"))
    assert "access_token=" in set_cookie and "HttpOnly" in set_cookie
    assert "refresh_token=" in set_cookie and "HttpOnly" in set_cookie
    assert "csrf_token=" in set_cookie


def test_auth_me_returns_owner_permissions(auth_client, api_base_url):
    response = auth_client.get(f"{api_base_url}/api/auth/me", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data.get("email") == OWNER_EMAIL
    assert data.get("role") == "owner"
    assert "content.publish" in (data.get("permissions") or [])
    assert "config" in (data.get("permissions") or [])


# Session lifecycle: missing access cookie recovers with refresh cookie
def test_refresh_recovers_when_access_cookie_is_missing(auth_client, api_base_url):
    auth_client.cookies.pop("access_token", None)
    before = auth_client.get(f"{api_base_url}/api/auth/me", timeout=20)
    assert before.status_code == 401

    refreshed = auth_client.post(f"{api_base_url}/api/auth/refresh", timeout=20)
    assert refreshed.status_code == 200
    assert refreshed.json().get("ok") is True

    after = auth_client.get(f"{api_base_url}/api/auth/me", timeout=20)
    assert after.status_code == 200
    assert after.json().get("email") == OWNER_EMAIL


# Security behavior: brute-force lockout + CORS credentials
def test_login_lockout_after_five_failed_attempts(anon_client, api_base_url):
    target_email = f"lock-{uuid.uuid4().hex[:8]}@example.com"
    for _ in range(5):
        attempt = anon_client.post(
            f"{api_base_url}/api/auth/login",
            json={"email": target_email, "password": "wrong-pass-123"},
            timeout=20,
        )
        assert attempt.status_code == 401
    locked = anon_client.post(
        f"{api_base_url}/api/auth/login",
        json={"email": target_email, "password": "wrong-pass-123"},
        timeout=20,
    )
    assert locked.status_code == 429


def test_cors_preflight_allows_credentials_for_configured_origin(anon_client, api_base_url):
    if not ALLOWED_ORIGIN:
        pytest.skip("CORS_ORIGINS is not set")
    response = anon_client.options(
        f"{api_base_url}/api/auth/login",
        headers={
            "Origin": ALLOWED_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=20,
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN
    assert response.headers.get("access-control-allow-credentials") == "true"


# Live-site API constraints: auth, allowlist paths, invalid paths and menu path guards
def test_site_live_requires_auth(anon_client, api_base_url):
    response = anon_client.put(
        f"{api_base_url}/api/admin/site-live",
        json={"path": "tagline", "value": "Should fail"},
        timeout=20,
    )
    assert response.status_code == 401


def test_site_live_rejects_non_allowlisted_path(auth_client, api_base_url):
    response = auth_client.put(
        f"{api_base_url}/api/admin/site-live",
        json={"path": "settings.theme.colors.text", "value": "#000000"},
        timeout=20,
    )
    assert response.status_code == 400


def test_site_live_rejects_missing_menu_path(auth_client, api_base_url):
    response = auth_client.put(
        f"{api_base_url}/api/admin/site-live",
        json={"path": "menus.main.999.label", "value": "Nope"},
        timeout=20,
    )
    assert response.status_code == 400


def test_site_live_allows_public_copy_path_and_restores_original(auth_client, api_base_url):
    site = auth_client.get(f"{api_base_url}/api/public/site", timeout=20)
    assert site.status_code == 200
    original = site.json().get("tagline") or ""

    patch_value = f"TEST_TAGLINE_{uuid.uuid4().hex[:8]}"
    save = auth_client.put(
        f"{api_base_url}/api/admin/site-live",
        json={"path": "tagline", "value": patch_value},
        timeout=20,
    )
    assert save.status_code == 200
    assert save.json().get("path") == "tagline"
    assert save.json().get("value") == patch_value

    changed = auth_client.get(f"{api_base_url}/api/public/site", timeout=20)
    assert changed.status_code == 200
    assert changed.json().get("tagline") == patch_value

    restore = auth_client.put(
        f"{api_base_url}/api/admin/site-live",
        json={"path": "tagline", "value": original},
        timeout=20,
    )
    assert restore.status_code == 200

    final_site = auth_client.get(f"{api_base_url}/api/public/site", timeout=20)
    assert final_site.status_code == 200
    assert final_site.json().get("tagline") == original


def test_public_site_ui_text_is_never_null(anon_client, api_base_url):
    response = anon_client.get(f"{api_base_url}/api/public/site", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data.get("ui_text"), dict)


# Seed/auth storage checks: bcrypt format for seeded owner hash
def test_seeded_owner_hash_uses_bcrypt_2b_prefix():
    try:
        from pymongo import MongoClient
    except Exception:
        pytest.skip("pymongo not installed")

    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name or not OWNER_EMAIL:
        pytest.skip("MONGO_URL / DB_NAME / ADMIN_EMAIL env vars are required")

    client = MongoClient(mongo_url)
    try:
        user = client[db_name]["users"].find_one({"email": OWNER_EMAIL.lower()})
        assert user is not None
        password_hash = user.get("password_hash", "")
        assert isinstance(password_hash, str)
        assert password_hash.startswith("$2b$")
    finally:
        client.close()
