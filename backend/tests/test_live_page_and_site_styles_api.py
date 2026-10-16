import re
import os

import pytest
import requests


# Live page + site-live validation tests: auth boundaries, hidden sections retention, optional styles handling
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


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


@pytest.fixture(scope="module")
def api_base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="module")
def owner_client(api_base_url):
    creds = _read_owner_credentials()
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    login = s.post(f"{api_base_url}/api/auth/login", json=creds, timeout=30)
    if login.status_code != 200:
        pytest.skip(f"Owner login failed: {login.status_code} {login.text}")
    csrf = s.cookies.get("csrf_token")
    if csrf:
        s.headers.update({"X-CSRF-Token": csrf})
    return s


def test_pages_live_requires_auth_with_fresh_anonymous_client(api_base_url):
    anon = requests.Session()
    anon.headers.update({"Content-Type": "application/json"})
    response = anon.get(f"{api_base_url}/api/admin/pages/workshops-learning/live", timeout=30)
    assert response.status_code == 401


def test_pages_live_contains_full_published_sections_including_hidden(owner_client, api_base_url):
    admin_page = owner_client.get(f"{api_base_url}/api/admin/pages/workshops-learning", timeout=30)
    assert admin_page.status_code == 200
    published_sections = admin_page.json().get("published", {}).get("sections", [])
    expected_len = len(published_sections)
    expected_hidden = sum(1 for s in published_sections if s.get("hidden"))

    live = owner_client.get(f"{api_base_url}/api/admin/pages/workshops-learning/live", timeout=30)
    assert live.status_code == 200
    sections = live.json().get("content", {}).get("sections", [])

    assert len(sections) == expected_len
    assert len(sections) == 9
    assert sum(1 for s in sections if s.get("hidden")) == expected_hidden


def test_site_live_accepts_optional_styles_field(owner_client, api_base_url):
    before = owner_client.get(f"{api_base_url}/api/public/site", timeout=30)
    assert before.status_code == 200
    original_tagline = before.json().get("tagline", "")

    value = f"{original_tagline}"
    response = owner_client.put(
        f"{api_base_url}/api/admin/site-live",
        json={"path": "tagline", "value": value, "area": "main"},
        timeout=30,
    )
    assert response.status_code == 200
    assert response.json().get("path") == "tagline"


def test_site_live_rejects_invalid_area(owner_client, api_base_url):
    response = owner_client.put(
        f"{api_base_url}/api/admin/site-live",
        json={"path": "tagline", "value": "TEST", "area": "sidebar"},
        timeout=30,
    )
    assert response.status_code == 422


def test_minor_site_text_save_does_not_drop_hidden_sections_in_live_pages(owner_client, api_base_url):
    before = owner_client.get(f"{api_base_url}/api/admin/pages/workshops-learning/live", timeout=30)
    assert before.status_code == 200
    before_sections = before.json().get("content", {}).get("sections", [])
    before_hidden = sum(1 for s in before_sections if s.get("hidden"))

    site = owner_client.get(f"{api_base_url}/api/public/site", timeout=30)
    assert site.status_code == 200
    original = site.json().get("tagline", "")

    save = owner_client.put(
        f"{api_base_url}/api/admin/site-live",
        json={"path": "tagline", "value": original, "area": "footer"},
        timeout=30,
    )
    assert save.status_code == 200

    after = owner_client.get(f"{api_base_url}/api/admin/pages/workshops-learning/live", timeout=30)
    assert after.status_code == 200
    after_sections = after.json().get("content", {}).get("sections", [])
    after_hidden = sum(1 for s in after_sections if s.get("hidden"))

    assert len(after_sections) == len(before_sections)
    assert after_hidden == before_hidden
