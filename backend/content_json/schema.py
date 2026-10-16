"""Supported content-only JSON formats and validation before any database writes."""
import json
import re
from urllib.parse import urlsplit
from fastapi import HTTPException
from core import PAGE_PATHS, sanitize_tree
from routes_admin import SECTION_TYPES
from content_sync.schema import COLLECTION_KEYS, SITE_FIELDS, MAX_BYTES, normalise
from header_settings import clean_header_styles
from text_styles import clean_text_style, text_style_key


def invalid(message):
    raise HTTPException(400, message)


def safe_link(value):
    if not isinstance(value, str) or not value or re.search(r"[\\\x00-\x1f]", value):
        return False
    if value.startswith("//") or "%5c" in value.lower():
        return False
    try:
        return value.startswith(("/", "#")) or urlsplit(value).scheme in {"https", "http", "mailto", "tel"}
    except ValueError:
        return False


def walk(value, depth=0):
    if depth > 35:
        invalid("JSON content is nested too deeply")
    if isinstance(value, dict):
        for key, child in value.items():
            if key.startswith("$"):
                invalid("JSON contains unsupported database operators")
            if key in {"href", "link_href"} and child and not safe_link(child):
                invalid(f"Invalid link in {key}. Use a website path or an http/https address.")
            walk(child, depth + 1)
    elif isinstance(value, list):
        for child in value:
            walk(child, depth + 1)


def parse(raw):
    if len(raw) > MAX_BYTES:
        raise HTTPException(413, "JSON file exceeds the 12 MB limit")
    def reject_constant(value):
        raise ValueError(value)
    try:
        data = json.loads(raw.decode("utf-8-sig"), parse_constant=reject_constant)
    except (UnicodeDecodeError, ValueError, RecursionError):
        invalid("This is not valid JSON. Choose a content JSON export, not a ZIP or PDF.")
    if not isinstance(data, dict):
        invalid("Expected a USP content export object, not a list or plain text")
    if data.get("version", 1) != 1 or data.get("schema", 1) != 1:
        invalid("This export version is not supported")
    source = data.get("collections", data)
    if not isinstance(source, dict):
        invalid("The collections field must be an object")
    collections = {}
    for name, identity in COLLECTION_KEYS.items():
        docs = source.get(name, [])
        if not isinstance(docs, list) or len(docs) > 100000:
            invalid(f"{name} must be an array of content records")
        keys = [doc.get(identity) for doc in docs if isinstance(doc, dict)]
        if len(keys) != len(docs) or any(not isinstance(key, str) or not key.strip() or len(key) > 500 for key in keys) or len(set(keys)) != len(keys):
            invalid(f"{name} has missing or duplicate {identity} values")
        collections[name] = normalise(docs)
        for document in collections[name]:
            if "id" in document and (not isinstance(document["id"], str) or not document["id"]):
                invalid(f"Invalid ID in {name}")
    settings = source.get("settings", [])
    if not isinstance(settings, list) or any(not isinstance(s, dict) for s in settings):
        invalid("settings must be an array of setting records")
    site = data.get("site", next((s for s in settings if s.get("key") == "site"), {}))
    if not isinstance(site, dict):
        invalid("Site content settings must be an object")
    site = normalise({key: value for key, value in site.items() if key in SITE_FIELDS})
    if not any(collections.values()) and not site:
        invalid("No importable content found. Choose a USP content JSON or metadata backup.")
    content = {"collections": collections, "site": site}
    walk(content)
    for key in ("theme", "ui_text", "contact", "menus", "taxonomy"):
        if key in site and not isinstance(site[key], dict):
            invalid(f"Site {key} must be an object")
    for key in ("site_name", "full_name", "brand_label", "tagline", "footer_text", "privacy_html", "logo_media_id", "favicon_media_id", "default_share_media_id"):
        if key in site and not isinstance(site[key], str):
            invalid(f"Site {key} must be text")
    if any(not isinstance(text, str) for text in site.get("ui_text", {}).values()):
        invalid("Shared text values must be strings")
    if "social" in site and (not isinstance(site["social"], list) or any(not isinstance(v, dict) for v in site["social"])):
        invalid("Social links must be an array of objects")
    def menus(items):
        if not isinstance(items, list):
            invalid("Each navigation menu must be an array")
        for item in items:
            if not isinstance(item, dict) or not all(isinstance(item.get(k), str) and item[k] for k in ("id", "label", "href")):
                invalid("Each menu item needs an ID, label and link")
            menus(item.get("children", []))
    for items in site.get("menus", {}).values():
        menus(items)
    for page in collections["pages"]:
        if not re.fullmatch(r"[a-z0-9_-]{1,80}", page["key"]):
            invalid("Page keys must use lowercase letters, numbers, hyphens or underscores")
        if not isinstance(page.get("path"), str) or not page["path"].startswith("/") or not safe_link(page["path"]):
            invalid(f"Missing or invalid path for page {page['key']}")
        if page["key"] in PAGE_PATHS and page["path"] != PAGE_PATHS[page["key"]]:
            invalid(f"The required path for {page['key']} is {PAGE_PATHS[page['key']]}")
        for version in ("published", "draft"):
            value = page.get(version)
            if not isinstance(value, dict) or not isinstance(value.get("title"), str) or not isinstance(value.get("sections"), list):
                invalid(f"Page {page['key']} is missing complete {version} content")
            if not isinstance(value.get("seo", {}), dict):
                invalid(f"Page {page['key']} has invalid SEO content")
            ids = set()
            for section in value["sections"]:
                if not isinstance(section, dict) or not isinstance(section.get("id"), str) or not section["id"] or section["id"] in ids:
                    invalid(f"Page {page['key']} has a missing or duplicate section ID")
                ids.add(section["id"])
                if section.get("type") not in SECTION_TYPES or not isinstance(section.get("data"), dict):
                    invalid(f"Page {page['key']} contains an unsupported section")
                if not isinstance(section.get("styles", {}), dict):
                    invalid(f"Page {page['key']} has invalid section styles")
                if any(not isinstance(style, dict) for style in section.get("styles", {}).values()):
                    invalid(f"Page {page['key']} has invalid field styles")
                for key in ("items", "buttons", "values"):
                    if key in section["data"] and (not isinstance(section["data"][key], list) or any(not isinstance(item, dict) for item in section["data"][key])):
                        invalid(f"Page {page['key']} has invalid {key} content")
    for note in collections["notes"]:
        if not re.fullmatch(r"[a-z0-9_-]{1,200}", note["slug"]):
            invalid("Field Note slugs must use lowercase letters, numbers, hyphens or underscores")
        if note.get("status") not in {"draft", "published"}:
            invalid(f"Invalid status for note {note['slug']}")
        for version in ("draft", "published"):
            if version == "published" and note["status"] == "draft" and note.get(version) is None:
                continue
            if not isinstance(note.get(version), dict) or not isinstance(note[version].get("title"), str):
                invalid(f"Note {note['slug']} is missing {version} content")
    for media in collections["media"]:
        if media.get("kind") not in {"image", "document", "video", "file"}:
            invalid(f"Invalid media kind: {media['id']}")
        if not isinstance(media.get("derivs", []), list) or any(not isinstance(d, dict) for d in media.get("derivs", [])):
            invalid(f"Invalid derivatives for media {media['id']}")
        paths = [media.get("original_path")] + [d.get("path") for d in media.get("derivs", [])]
        if any(not isinstance(p, str) or not p.startswith("uspindia/") or ".." in p.split("/") or "\\" in p for p in paths):
            invalid(f"Invalid object-storage path for media {media['id']}")
    for redirect in collections["redirects"]:
        if not redirect["from_path"].startswith("/") or not safe_link(redirect["from_path"]) or not safe_link(redirect.get("to_path")) or redirect.get("code", 301) not in {301, 302, 307, 308}:
            invalid("Invalid redirect path, destination or status")
    if "header_styles" in site:
        if not isinstance(site["header_styles"], dict):
            invalid("Header styles must be an object")
        site["header_styles"] = clean_header_styles(site["header_styles"])
    if "text_styles" in site:
        if not isinstance(site["text_styles"], dict):
            invalid("Text styles must be an object")
        clean = {}
        for entry in site["text_styles"].values():
            if not isinstance(entry, dict) or entry.get("area") not in {"header", "main", "footer"} or not isinstance(entry.get("path"), str) or not isinstance(entry.get("styles"), dict):
                invalid("Invalid shared-text style entry")
            clean[text_style_key(entry["area"], entry["path"])] = {**entry, "styles": clean_text_style(entry["styles"])}
        site["text_styles"] = clean
    return sanitize_tree(content)