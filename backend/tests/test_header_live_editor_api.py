import os
import re
import sys
from pathlib import Path

import pytest
import requests


# Header live editor API regression tests: auth, validation, atomic updates, and release schema fields
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _read_owner_credentials():
    path = "/app/memory/test_credentials.md"
    try:
        text = open(path, "r", encoding="utf-8").read()
    except FileNotFoundError:
        pytest.skip("/app/memory/test_credentials.md is missing")
    email_match = re.search(r"Email:\s*([^\s]+)", text)
    pwd_match = re.search(r"Password:\s*(.+)", text)
    if not email_match or not pwd_match:
        pytest.skip("Owner credentials missing in /app/memory/test_credentials.md")
    return {"email": email_match.group(1).strip(), "password": pwd_match.group(1).strip()}


def _flatten_menu(items, prefix="menus.main"):
    out = []
    for idx, item in enumerate(items or []):
        path = f"{prefix}.{idx}"
        out.append({"path": path, "id": item["id"], "label": item["label"], "href": item["href"]})
        out.extend(_flatten_menu(item.get("children") or [], f"{path}.children"))
    return out


@pytest.fixture(scope="module")
def api_base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="module")
def owner_credentials():
    return _read_owner_credentials()


@pytest.fixture(scope="module")
def anon_client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="module")
def owner_client(api_base_url, owner_credentials):
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    login = s.post(f"{api_base_url}/api/auth/login", json=owner_credentials, timeout=30)
    if login.status_code != 200:
        pytest.skip(f"Owner login failed: {login.status_code} {login.text}")
    csrf = s.cookies.get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


@pytest.fixture(scope="module")
def baseline_site(owner_client, api_base_url):
    response = owner_client.get(f"{api_base_url}/api/public/site", timeout=30)
    assert response.status_code == 200
    site = response.json()
    baseline = {
        "brand_label": site.get("brand_label", "USP"),
        "full_name": site.get("full_name", ""),
        "mobile_menu_label": (site.get("ui_text") or {}).get("menu", "Menu"),
        "logo_media_id": (site.get("logo") or {}).get("id", ""),
        "styles": site.get("header_styles") or {},
        "menus_main": site.get("menus", {}).get("main", []),
    }
    yield baseline

    restore = {
        "brand_label": baseline["brand_label"],
        "full_name": baseline["full_name"],
        "mobile_menu_label": baseline["mobile_menu_label"],
        "logo_media_id": baseline["logo_media_id"],
        "menu_items": _flatten_menu(baseline["menus_main"]),
        "styles": baseline["styles"],
    }
    r = owner_client.put(f"{api_base_url}/api/admin/header-live", json=restore, timeout=30)
    assert r.status_code == 200, f"Baseline restore failed: {r.status_code} {r.text}"


def _snapshot(site):
    our_work = next((x for x in site.get("menus", {}).get("main", []) if x.get("id") == "m-work"), None)
    children = our_work.get("children", []) if our_work else []
    return {
        "brand_label": site.get("brand_label"),
        "full_name": site.get("full_name"),
        "mobile_menu_label": (site.get("ui_text") or {}).get("menu"),
        "header_styles": site.get("header_styles") or {},
        "logo_id": (site.get("logo") or {}).get("id"),
        "our_work_count": len(children),
        "our_work_grandchildren": [len(c.get("children") or []) for c in children],
        "our_work_ids": [c.get("id") for c in children],
    }


# Auth contract checks around owner session and cookie behavior.
def test_owner_login_sets_http_only_cookies(anon_client, api_base_url, owner_credentials):
    response = anon_client.post(f"{api_base_url}/api/auth/login", json=owner_credentials, timeout=30)
    assert response.status_code == 200
    set_cookie = "\n".join(response.raw.headers.get_all("Set-Cookie"))
    assert "access_token=" in set_cookie
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "csrf_token=" in set_cookie


# Header endpoint permission checks.
def test_header_live_rejects_anonymous(anon_client, api_base_url):
    response = requests.put(
        f"{api_base_url}/api/admin/header-live",
        json={"brand_label": "USP", "full_name": "", "logo_media_id": "", "mobile_menu_label": "Menu", "menu_items": [], "styles": {}},
        timeout=30,
    )
    assert response.status_code == 401


# Core header save workflow and persistence checks.
def test_header_live_updates_and_persists_with_structure_intact(owner_client, api_base_url, baseline_site):
    current = owner_client.get(f"{api_base_url}/api/public/site", timeout=30)
    assert current.status_code == 200
    site = current.json()

    updated_brand = "USP TEST"
    updated_full_name = "Urban Suburban Perspectives Test"
    updated_menu_label = "Menu Test"
    menu_items = _flatten_menu(site.get("menus", {}).get("main", []))
    target = next((m for m in menu_items if m["id"] == "m-connect"), None)
    assert target is not None
    target["label"] = "Connect Test"
    target["href"] = "/connect"

    payload = {
        "brand_label": updated_brand,
        "full_name": updated_full_name,
        "mobile_menu_label": updated_menu_label,
        "logo_media_id": (site.get("logo") or {}).get("id", ""),
        "menu_items": menu_items,
        "styles": site.get("header_styles") or {},
    }
    save = owner_client.put(f"{api_base_url}/api/admin/header-live", json=payload, timeout=30)
    assert save.status_code == 200
    assert save.json().get("ok") is True

    changed = owner_client.get(f"{api_base_url}/api/public/site", timeout=30)
    assert changed.status_code == 200
    changed_site = changed.json()
    assert changed_site.get("brand_label") == updated_brand
    assert changed_site.get("full_name") == updated_full_name
    assert (changed_site.get("ui_text") or {}).get("menu") == updated_menu_label

    connect_item = next((m for m in changed_site.get("menus", {}).get("main", []) if m.get("id") == "m-connect"), None)
    assert connect_item is not None
    assert connect_item.get("label") == "Connect Test"
    assert connect_item.get("href") == "/connect"

    our_work = next((m for m in changed_site.get("menus", {}).get("main", []) if m.get("id") == "m-work"), None)
    assert our_work is not None
    assert [c.get("id") for c in our_work.get("children", [])] == ["m-rak", "m-the", "m-cra", "m-wor"]
    assert len(our_work.get("children", [])) == 4
    assert all(len(c.get("children", [])) == 0 for c in our_work.get("children", []))


# Validation and atomicity checks for invalid payloads.
@pytest.mark.parametrize(
    "mutator,expected_status",
    [
        (lambda p: p.update({"styles": {"backgroundColor": "url(javascript:alert(1))"}}), 400),
        (lambda p: p.update({"styles": {"unsupportedStyle": "10px"}}), 400),
        (lambda p: p.update({"styles": {"fontSize": "-2px"}}), 400),
        (lambda p: p["menu_items"].__setitem__(0, {**p["menu_items"][0], "href": "javascript:alert(1)"}), 400),
        (lambda p: p["menu_items"].__setitem__(0, {**p["menu_items"][0], "href": "//evil.test"}), 400),
        (lambda p: p["menu_items"].__setitem__(0, {**p["menu_items"][0], "path": "menus.main.999", "id": "m-home"}), 409),
        (lambda p: p["menu_items"].__setitem__(0, {**p["menu_items"][0], "id": "forged-id"}), 409),
        (lambda p: p.update({"logo_media_id": "non-existent-logo-id"}), 400),
    ],
)
def test_header_live_rejects_invalid_payloads_without_partial_update(owner_client, api_base_url, mutator, expected_status):
    before_response = owner_client.get(f"{api_base_url}/api/public/site", timeout=30)
    assert before_response.status_code == 200
    before_site = before_response.json()
    before_snapshot = _snapshot(before_site)

    payload = {
        "brand_label": before_site.get("brand_label") or "USP",
        "full_name": before_site.get("full_name") or "",
        "mobile_menu_label": (before_site.get("ui_text") or {}).get("menu") or "Menu",
        "logo_media_id": (before_site.get("logo") or {}).get("id", ""),
        "menu_items": _flatten_menu(before_site.get("menus", {}).get("main", [])),
        "styles": before_site.get("header_styles") or {},
    }
    mutator(payload)
    bad = owner_client.put(f"{api_base_url}/api/admin/header-live", json=payload, timeout=30)
    assert bad.status_code == expected_status

    after_response = owner_client.get(f"{api_base_url}/api/public/site", timeout=30)
    assert after_response.status_code == 200
    after_snapshot = _snapshot(after_response.json())
    assert after_snapshot == before_snapshot


# Shared validator behavior on legacy endpoint compatibility.
def test_site_styles_uses_shared_validator(owner_client, api_base_url):
    valid = owner_client.put(
        f"{api_base_url}/api/admin/site-styles",
        json={"styles": {"backgroundColor": "#dcefed", "color": "#143322", "fontFamily": "Public Sans", "paddingTop": "8px"}},
        timeout=30,
    )
    assert valid.status_code == 200
    data = valid.json()
    assert data["header_styles"]["backgroundColor"] == "#dcefed"
    assert data["header_styles"]["color"] == "#143322"

    invalid = owner_client.put(
        f"{api_base_url}/api/admin/site-styles",
        json={"styles": {"paddingTop": "-4px"}},
        timeout=30,
    )
    assert invalid.status_code == 400


# Content release schema scope check for header styles inclusion.
def test_content_release_site_fields_include_header_styles():
    from content_sync.schema import SITE_FIELDS

    assert "header_styles" in SITE_FIELDS
