import os
from urllib.parse import urlparse

import pytest
import requests


# Public API regression tests for Rakhigarhi page and cross-page stability
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")
OWNER_EMAIL = os.environ.get("TEST_OWNER_EMAIL")
OWNER_PASSWORD = os.environ.get("TEST_OWNER_PASSWORD")


@pytest.fixture(scope="session")
def api_base_url():
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is not set")
    return BASE_URL.rstrip("/")


@pytest.fixture(scope="session")
def client():
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


@pytest.fixture(scope="session")
def auth_client(api_base_url):
    if not OWNER_EMAIL or not OWNER_PASSWORD:
        pytest.skip("TEST_OWNER_EMAIL and TEST_OWNER_PASSWORD are required for admin checks")
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    login = s.post(
        f"{api_base_url}/api/auth/login",
        json={"email": OWNER_EMAIL, "password": OWNER_PASSWORD},
        timeout=20,
    )
    if login.status_code != 200:
        pytest.skip(f"Owner login failed for admin verification: {login.status_code}")
    return s


def _section_by_anchor(sections, anchor):
    return next((s for s in sections if s.get("data", {}).get("anchor") == anchor), None)


def _path_from_url(url):
    parsed = urlparse(url)
    return parsed.path if parsed.scheme else url


def test_rakhigarhi_page_has_expected_section_set(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/pages/rakhigarhi", timeout=20)
    assert response.status_code == 200

    body = response.json()
    assert body["key"] == "rakhigarhi"

    sections = body["content"]["sections"]
    assert len(sections) == 9
    assert sections[0]["type"] == "hero"

    anchors = [s.get("data", {}).get("anchor") for s in sections if s.get("data", {}).get("anchor")]
    assert anchors == [
        "archaeology",
        "haveli-chaupal",
        "haveli-in-use",
        "craft-centre",
        "place-to-arrive",
        "place-to-pause",
        "active-use-summary",
        "the-ambition",
    ]


def test_rakhigarhi_hero_and_copy_constraints(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/pages/rakhigarhi", timeout=20)
    assert response.status_code == 200

    sections = response.json()["content"]["sections"]
    hero = sections[0]
    hero_data = hero["data"]

    assert hero_data.get("eyebrow") == "Rakhigarhi"
    assert hero_data.get("heading") == "5,000 Years of History.\nA Place Still Evolving."
    all_text = " ".join(
        [
            (s.get("data", {}).get("heading") or "") + " " + (s.get("data", {}).get("body_html") or "")
            for s in sections
        ]
    )
    assert "Draft placeholder" not in all_text
    assert "Local accounts" not in all_text


def test_haveli_collage_has_expected_images_and_media(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/pages/rakhigarhi", timeout=20)
    assert response.status_code == 200
    sections = response.json()["content"]["sections"]

    haveli = _section_by_anchor(sections, "haveli-chaupal")
    assert haveli is not None
    data = haveli["data"]
    assert data.get("layout") == "haveli-reference-aligned"

    facade = data.get("image", {})
    assert facade.get("media")
    assert not facade.get("placeholder", False)

    collage = data.get("collage", [])
    assert len(collage) == 2
    for item in collage:
        assert item.get("media")
        assert not item.get("placeholder", False)


def test_rakhigarhi_uses_grid_content_and_link(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/pages/rakhigarhi", timeout=20)
    assert response.status_code == 200
    sections = response.json()["content"]["sections"]

    craft = _section_by_anchor(sections, "craft-centre")
    arrive = _section_by_anchor(sections, "place-to-arrive")
    pause = _section_by_anchor(sections, "place-to-pause")

    assert craft is not None and arrive is not None and pause is not None
    assert craft["data"].get("link_label") == "Explore Craft & Livelihood"
    assert craft["data"].get("link_href") == "/our-work/craft-livelihood"


def test_public_media_urls_for_haveli_assets_are_fetchable(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/pages/rakhigarhi", timeout=20)
    assert response.status_code == 200
    data = response.json()["content"]["sections"]
    haveli = _section_by_anchor(data, "haveli-chaupal")
    assert haveli is not None

    urls = [
        haveli["data"]["image"]["media"]["src"],
        haveli["data"]["collage"][0]["media"]["src"],
        haveli["data"]["collage"][1]["media"]["src"],
    ]
    for media_url in urls:
        media_path = _path_from_url(media_url)
        media_response = client.get(f"{api_base_url}{media_path}", timeout=20)
        assert media_response.status_code == 200
        assert media_response.headers.get("content-type", "").startswith("image/")


def test_home_craft_workshops_still_available(client, api_base_url):
    home = client.get(f"{api_base_url}/api/public/pages/home", timeout=20)
    craft = client.get(f"{api_base_url}/api/public/pages/craft-livelihood", timeout=20)
    workshops = client.get(f"{api_base_url}/api/public/pages/workshops-learning", timeout=20)

    assert home.status_code == 200
    assert craft.status_code == 200
    assert workshops.status_code == 200

    assert home.json()["key"] == "home"
    assert craft.json()["key"] == "craft-livelihood"
    assert workshops.json()["key"] == "workshops-learning"


def test_anonymous_auth_me_is_unauthorized(client, api_base_url):
    response = client.get(f"{api_base_url}/api/auth/me", timeout=20)
    assert response.status_code == 401


def test_public_menu_has_exactly_four_work_links_without_nested_submenus(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/site", timeout=20)
    assert response.status_code == 200
    site = response.json()
    main_menu = site.get("menus", {}).get("main", [])

    our_work = next((item for item in main_menu if item.get("href") == "/our-work"), None)
    assert our_work is not None

    # Updated user contract: only the four work areas, never third-level menus.
    children = our_work.get("children", [])
    assert [child.get("href") for child in children] == [
        "/our-work/rakhigarhi", "/our-work/theatre", "/our-work/craft-livelihood", "/our-work/workshops-learning"
    ]
    assert all(not child.get("children") for child in children)


def test_admin_rakhigarhi_page_contains_design_migration_flag(auth_client, api_base_url):
    response = auth_client.get(f"{api_base_url}/api/admin/pages/rakhigarhi", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data.get("key") == "rakhigarhi"
    assert data.get("design_migration") == "four-page-reference-2026-10-16"


def test_admin_revisions_include_pre_migration_backups(auth_client, api_base_url):
    response = auth_client.get(
        f"{api_base_url}/api/admin/revisions",
        params={"entity_type": "page", "entity_id": "rakhigarhi"},
        timeout=20,
    )
    assert response.status_code == 200
    revs = response.json()
    assert isinstance(revs, list)
    assert len(revs) > 0

    before_actions = [
        r for r in revs if "before Rakhigarhi reference" in (r.get("action") or "")
    ]
    assert len(before_actions) >= 2

