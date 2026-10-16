import copy
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from bson import ObjectId
from core import APP_NAME, PAGE_PATHS, sanitize_tree

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / "content_deployment.json"
BUNDLE_FILE = ROOT / "content_release.json"
COLLECTION_KEYS = {"pages": "key", "notes": "slug", "media": "id", "redirects": "from_path"}
SITE_FIELDS = {"site_name", "full_name", "brand_label", "tagline", "theme", "footer_text", "privacy_html", "ui_text",
               "contact", "social", "menus", "logo_media_id", "favicon_media_id", "default_share_media_id",
               "live_editor_enabled", "preview_banner", "taxonomy", "header_styles", "text_styles"}
MAX_BYTES = 12 * 1024 * 1024


def normalise(value):
    if isinstance(value, dict):
        return {k: normalise(v) for k, v in value.items() if k != "_id"}
    if isinstance(value, list):
        return [normalise(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, ObjectId):
        return str(value)
    return value


def encoded(value):
    return json.dumps(normalise(value), sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def config():
    if not CONFIG_FILE.exists():
        return None
    value = json.loads(CONFIG_FILE.read_text())
    for key in ("channel", "source_id", "source_binding"):
        text = value.get(key)
        if not isinstance(text, str) or not text or not all(c.isalnum() or c in "-_" for c in text):
            raise ValueError("Invalid content deployment configuration")
    return value


def object_prefix(cfg):
    return f"{APP_NAME}/content-releases/{cfg['channel']}"


def media_ids(value):
    out = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if (key == "media_id" or key.endswith("_media_id") or key == "derived_from") and isinstance(child, str) and child:
                out.add(child)
            else:
                out.update(media_ids(child))
    elif isinstance(value, list):
        for child in value:
            out.update(media_ids(child))
    return out


def validate(bundle, cfg):
    if len(encoded(bundle)) > MAX_BYTES or bundle.get("schema") != 1:
        raise ValueError("Invalid or oversized content release")
    if bundle.get("channel") != cfg["channel"] or bundle.get("source_id") != cfg["source_id"]:
        raise ValueError("Content release belongs to another source")
    collections = bundle.get("collections")
    if not isinstance(collections, dict) or set(collections) != set(COLLECTION_KEYS):
        raise ValueError("Only pages, notes, media and redirects may be promoted")
    for name, identity in COLLECTION_KEYS.items():
        docs = collections[name]
        if not isinstance(docs, list) or len(docs) > 100000:
            raise ValueError(f"Invalid {name} collection")
        keys = [d.get(identity) for d in docs if isinstance(d, dict)]
        if len(keys) != len(docs) or any(not isinstance(k, str) or not k for k in keys) or len(set(keys)) != len(keys):
            raise ValueError(f"Missing or duplicate identities in {name}")
    pages = {p["key"]: p for p in collections["pages"]}
    if not set(PAGE_PATHS).issubset(pages):
        raise ValueError("Release is missing required website pages")
    for page in pages.values():
        for version in ("published", "draft"):
            if not isinstance(page.get(version), dict) or not isinstance(page[version].get("sections"), list):
                raise ValueError(f"Incomplete {version} content: {page['key']}")
    site = bundle.get("site")
    if not isinstance(site, dict) or set(site) - SITE_FIELDS:
        raise ValueError("Release contains non-content settings")
    mids = {m["id"] for m in collections["media"]}
    required = media_ids(collections["pages"]) | media_ids(collections["notes"]) | media_ids(site)
    if required - mids:
        raise ValueError(f"Release is missing {len(required - mids)} referenced media records")
    return sanitize_tree(copy.deepcopy(bundle))


async def collect(database, cfg):
    collections = {name: await database[name].find({}, {"_id": 0}).to_list(100000) for name in COLLECTION_KEYS}
    site = await database.settings.find_one({"key": "site"}, {"_id": 0})
    if not site:
        raise ValueError("Site settings missing")
    for name, docs in collections.items():
        docs.sort(key=lambda d: d[COLLECTION_KEYS[name]])
    bundle = normalise({"schema": 1, "channel": cfg["channel"], "source_id": cfg["source_id"],
                        "collections": collections, "site": {k: site[k] for k in SITE_FIELDS if k in site}})
    return validate(bundle, cfg)


def counts(bundle):
    return {**{k: len(v) for k, v in bundle["collections"].items()},
            "page_sections": {p["key"]: len(p["published"]["sections"]) for p in bundle["collections"]["pages"]}}