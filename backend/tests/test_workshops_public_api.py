import os
import re

import pytest
import requests


# Public API smoke + Workshops reference content regression tests
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL")


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


def test_health_ok(client, api_base_url):
    response = client.get(f"{api_base_url}/api/health", timeout=20)
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True


def test_workshops_page_structure_and_sections(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/pages/workshops-learning", timeout=20)
    assert response.status_code == 200

    body = response.json()
    assert body["key"] == "workshops-learning"
    sections = body["content"]["sections"]
    assert isinstance(sections, list)
    assert len(sections) >= 8

    anchors = [s.get("data", {}).get("anchor") for s in sections]
    for required_anchor in [
        "learning-intro",
        "heritage-guide",
        "restoration-skills",
        "creative-exchange",
        "student-projects",
        "ambition",
    ]:
        assert required_anchor in anchors

    types = [s.get("type") for s in sections]
    assert "notes_feed" not in types


def test_workshops_dummy_placeholders_and_restoration_copy(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/pages/workshops-learning", timeout=20)
    assert response.status_code == 200
    sections = response.json()["content"]["sections"]

    by_anchor = {s.get("data", {}).get("anchor"): s for s in sections}
    hero = next((s for s in sections if s.get("type") == "hero"), None)
    assert hero is not None

    expected_placeholder_targets = [
        hero,
        by_anchor["heritage-guide"],
        by_anchor["restoration-skills"],
        by_anchor["creative-exchange"],
    ]
    for sec in expected_placeholder_targets:
        img = sec.get("data", {}).get("image", {})
        assert img.get("placeholder") is True
        assert isinstance(img.get("placeholder_label"), str)
        assert img.get("placeholder_label") != ""
        assert not img.get("media")

    restoration_html = by_anchor["restoration-skills"]["data"].get("body_html", "")
    assert "local workers learn alongside conservation professionals" in restoration_html
    assert "gaining practical skills in traditional building techniques" in restoration_html
    assert "skills that remain with the workers long after the work is complete" in restoration_html
    assert len(re.findall(r"<p>.*?</p>", restoration_html)) == 2


def test_student_projects_film_link_pending_and_connect_link(client, api_base_url):
    response = client.get(f"{api_base_url}/api/public/pages/workshops-learning", timeout=20)
    assert response.status_code == 200
    sections = response.json()["content"]["sections"]

    student = next((s for s in sections if s.get("data", {}).get("anchor") == "student-projects"), None)
    assert student is not None
    student_data = student["data"]
    assert student_data.get("link_label") == "Explore Film"
    assert student_data.get("link_href") == ""

    connect = next((s for s in sections if s.get("type") == "contact_invite"), None)
    assert connect is not None
    connect_data = connect.get("data", {})
    buttons = connect_data.get("buttons", [])
    if buttons:
        assert buttons[0].get("href") == "/connect?topic=Workshops%20%26%20Learning"
    else:
        assert connect_data.get("href") == "/connect?topic=Workshops%20%26%20Learning"


def test_home_and_craft_pages_still_publicly_available(client, api_base_url):
    home_response = client.get(f"{api_base_url}/api/public/pages/home", timeout=20)
    craft_response = client.get(f"{api_base_url}/api/public/pages/craft-livelihood", timeout=20)

    assert home_response.status_code == 200
    assert craft_response.status_code == 200

    home_data = home_response.json()
    craft_data = craft_response.json()
    assert home_data["key"] == "home"
    assert craft_data["key"] == "craft-livelihood"
    assert len(home_data["content"]["sections"]) > 0
    assert len(craft_data["content"]["sections"]) > 0
