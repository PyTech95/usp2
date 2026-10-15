import csv
import io
import os
import re
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, EmailStr, Field
from core import (db, now, new_id, require, current_user, can, sanitize_tree, resolve_media_tree, public_user,
                  PAGE_PATHS, SITE_URL, media_public_ok)
from seed import DEFAULT_THEME
from routes_auth import issue_token

router = APIRouter(prefix="/api/admin")
SECTION_TYPES = {"hero", "text", "image_text", "image", "gallery", "quote", "video", "related_work", "notes_feed", "download", "contact_invite", "contact_form"}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NOTE_KINDS = {"article", "photo_essay", "interview", "workshop_reflection", "resource"}


async def snapshot(etype, eid, content, action, user, note=""):
    await db.revisions.insert_one({"id": new_id(), "entity_type": etype, "entity_id": eid, "content": content, "action": action,
                                   "note": note, "by": user["email"], "created_at": now()})


def clean_seo(seo):
    seo = {k: (seo or {}).get(k, d) for k, d in (("title", ""), ("description", ""), ("canonical", ""), ("noindex", False), ("share_media_id", ""))}
    if seo["canonical"] and not seo["canonical"].startswith(SITE_URL + "/"):
        raise HTTPException(400, f"Canonical URL must start with {SITE_URL}/")
    seo["title"] = str(seo["title"])[:200]
    seo["description"] = str(seo["description"])[:400]
    return seo


# ---------------- Pages ----------------
class PageDraft(BaseModel):
    title: str
    sections: list
    seo: dict = {}


@router.get("/pages")
async def list_pages(user=Depends(current_user)):
    return await db.pages.find({}, {"_id": 0, "draft.sections": 0, "published.sections": 0}).to_list(50)


async def get_page(key):
    p = await db.pages.find_one({"key": key}, {"_id": 0})
    if not p:
        raise HTTPException(404, "Page not found")
    return p


@router.get("/pages/{key}")
async def page_detail(key: str, user=Depends(current_user)):
    return await get_page(key)


@router.get("/pages/{key}/preview")
async def page_preview(key: str, user=Depends(current_user)):
    p = await get_page(key)
    return {"key": key, "path": p["path"], "content": await resolve_media_tree(p["draft"], admin=True), "is_preview": True}


@router.put("/pages/{key}/draft")
async def save_page(key: str, body: PageDraft, user=Depends(require("content.edit"))):
    await get_page(key)
    for s in body.sections:
        if s.get("type") not in SECTION_TYPES:
            raise HTTPException(400, f"Unknown section type {s.get('type')}")
        s.setdefault("id", new_id())
        s["hidden"] = bool(s.get("hidden"))
    content = sanitize_tree({"title": body.title.strip()[:200] or "Untitled", "sections": body.sections, "seo": clean_seo(body.seo)})
    await db.pages.update_one({"key": key}, {"$set": {"draft": content, "updated_at": now(), "has_unpublished_changes": True}})
    await snapshot("page", key, content, "draft saved", user)
    return await get_page(key)


@router.post("/pages/{key}/publish")
async def publish_page(key: str, user=Depends(require("content.publish"))):
    p = await get_page(key)
    await db.pages.update_one({"key": key}, {"$set": {"published": p["draft"], "status": "published", "published_at": now(), "updated_at": now(), "has_unpublished_changes": False}})
    await snapshot("page", key, p["draft"], "published", user)
    return await get_page(key)


STYLE_KEYS = {"fontFamily", "fontSize", "fontWeight", "fontStyle", "color", "backgroundColor", "textAlign", "textTransform",
              "width", "height", "maxWidth", "lineHeight", "letterSpacing", "borderRadius", "opacity",
              "paddingTop", "paddingBottom", "paddingLeft", "paddingRight", "marginTop", "marginBottom", "marginLeft", "marginRight", "objectPosition",
              "translateX", "translateY"}


def clean_styles(styles):
    out = {}
    for field, st in (styles or {}).items():
        if isinstance(st, dict):
            f = {k: str(v)[:80] for k, v in st.items() if k in STYLE_KEYS and v not in ("", None) and not re.search(r"[;{}<>]|url\(", str(v))}
            if f:
                out[str(field)[:40]] = f
    return out


def strip_resolved(obj):
    """Remove server-resolved fields (media/notes) so they are not persisted; they are re-attached on read."""
    if isinstance(obj, dict):
        return {k: strip_resolved(v) for k, v in obj.items() if k not in ("media", "original", "edit_note")}
    if isinstance(obj, list):
        return [strip_resolved(x) for x in obj]
    return obj


@router.put("/pages/{key}/live")
async def live_save(key: str, body: dict, user=Depends(require("content.publish"))):
    """Advanced live editor: accepts the full ordered section list and publishes it immediately."""
    p = await get_page(key)
    sections = body.get("sections")
    if not isinstance(sections, list):
        raise HTTPException(400, "No sections provided")
    clean = []
    for s in sections:
        if s.get("type") not in SECTION_TYPES:
            raise HTTPException(400, f"Unknown section type {s.get('type')}")
        clean.append({
            "id": s.get("id") or new_id(),
            "type": s["type"],
            "hidden": bool(s.get("hidden")),
            "data": strip_resolved(s.get("data") or {}),
            "styles": clean_styles(s.get("styles")),
        })
    pub = {**p["published"], "sections": clean}
    if body.get("title"):
        pub["title"] = str(body["title"]).strip()[:200] or pub.get("title", "Untitled")
    pub = sanitize_tree(pub)
    await db.pages.update_one({"key": key}, {"$set": {"published": pub, "draft": pub, "published_at": now(), "updated_at": now(), "has_unpublished_changes": False}})
    await snapshot("page", key, pub, "live edit published", user)
    return {"key": key, "content": await resolve_media_tree(pub)}


@router.post("/pages/{key}/discard")
async def discard_page(key: str, user=Depends(require("content.edit"))):
    p = await get_page(key)
    await db.pages.update_one({"key": key}, {"$set": {"draft": p["published"], "has_unpublished_changes": False}})
    return await get_page(key)


# ---------------- Revisions & comments ----------------
@router.get("/revisions")
async def list_revisions(entity_type: str, entity_id: str, user=Depends(current_user)):
    return await db.revisions.find({"entity_type": entity_type, "entity_id": entity_id}, {"_id": 0, "content": 0}).sort("created_at", -1).to_list(100)


@router.post("/revisions/{rid}/restore")
async def restore_revision(rid: str, user=Depends(require("notes.draft"))):
    r = await db.revisions.find_one({"id": rid}, {"_id": 0})
    if not r:
        raise HTTPException(404, "Revision not found")
    if r["entity_type"] == "page":
        if not can(user, "content.edit"):
            raise HTTPException(403, "Your role does not allow this action")
        await db.pages.update_one({"key": r["entity_id"]}, {"$set": {"draft": r["content"], "has_unpublished_changes": True, "updated_at": now()}})
    else:
        n = await get_note(r["entity_id"])
        check_note_owner(n, user)
        await db.notes.update_one({"id": r["entity_id"]}, {"$set": {"draft": r["content"], "has_unpublished_changes": True, "updated_at": now()}})
    await snapshot(r["entity_type"], r["entity_id"], r["content"], f"restored revision from {r['created_at'][:16]}", user)
    return {"ok": True}


class CommentIn(BaseModel):
    entity_type: str
    entity_id: str
    text: str
    verdict: str = "comment"


@router.get("/comments")
async def list_comments(entity_type: str = "", entity_id: str = "", user=Depends(current_user)):
    f = {k: v for k, v in (("entity_type", entity_type), ("entity_id", entity_id)) if v}
    return await db.comments.find(f, {"_id": 0}).sort("created_at", -1).to_list(200)


@router.post("/comments")
async def add_comment(body: CommentIn, user=Depends(current_user)):
    if body.verdict not in ("comment", "approve", "changes"):
        raise HTTPException(400, "Invalid verdict")
    if not body.text.strip() and body.verdict == "comment":
        raise HTTPException(400, "Comment is empty")
    doc = {"id": new_id(), **body.model_dump(), "text": body.text[:4000], "by": user["email"], "by_name": user.get("name"), "role": user["role"], "created_at": now()}
    await db.comments.insert_one(doc)
    doc.pop("_id", None)
    return doc


# ---------------- Field Notes ----------------
def check_note_owner(n, user):
    if not can(user, "content.edit") and n.get("created_by") != user["email"]:
        raise HTTPException(403, "Contributors can only edit their own drafts")


async def get_note(nid):
    n = await db.notes.find_one({"id": nid}, {"_id": 0})
    if not n:
        raise HTTPException(404, "Field Note not found")
    return n


class NoteDraft(BaseModel):
    title: str
    slug: str
    standfirst: str = ""
    kind: str = "article"
    author: str = ""
    category: str = ""
    tags: list[str] = []
    body_html: str = ""
    cover: dict = {}
    credits: str = ""
    references: list = []
    downloads: list = []
    related: list[str] = []
    seo: dict = {}


async def validate_note(body: NoteDraft, nid=None):
    slug = body.slug.strip().lower()
    if not SLUG_RE.match(slug):
        raise HTTPException(400, "Address (slug) may contain only lowercase letters, numbers and hyphens")
    clash = await db.notes.find_one({"$or": [{"slug": slug}, {"draft.slug": slug}], "id": {"$ne": nid}})
    if clash:
        raise HTTPException(409, "Another Field Note already uses this address")
    if body.kind not in NOTE_KINDS:
        raise HTTPException(400, "Invalid note type")
    d = body.model_dump()
    d["slug"] = slug
    d["title"] = d["title"].strip()[:200] or "Untitled"
    d["seo"] = clean_seo(body.seo)
    return sanitize_tree(d)


@router.get("/notes")
async def list_notes(user=Depends(current_user)):
    return await db.notes.find({}, {"_id": 0, "draft.body_html": 0, "published": 0}).sort("updated_at", -1).to_list(500)


@router.post("/notes")
async def create_note(body: NoteDraft, user=Depends(require("notes.draft"))):
    nid = new_id()
    d = await validate_note(body, nid)
    doc = {"id": nid, "slug": d["slug"], "draft": d, "published": None, "status": "draft", "created_by": user["email"],
           "created_at": now(), "updated_at": now(), "published_at": None, "has_unpublished_changes": True}
    await db.notes.insert_one(doc)
    await snapshot("note", nid, d, "created", user)
    return await get_note(nid)


@router.get("/notes/{nid}")
async def note_detail(nid: str, user=Depends(current_user)):
    return await get_note(nid)


@router.get("/notes/{nid}/preview")
async def note_preview(nid: str, user=Depends(current_user)):
    n = await get_note(nid)
    return {"note": await resolve_media_tree(n["draft"], admin=True), "published_at": n.get("published_at"), "updated_at": n["updated_at"], "is_preview": True}


@router.put("/notes/{nid}")
async def save_note(nid: str, body: NoteDraft, user=Depends(require("notes.draft"))):
    n = await get_note(nid)
    check_note_owner(n, user)
    d = await validate_note(body, nid)
    upd = {"draft": d, "updated_at": now(), "has_unpublished_changes": True}
    if n["status"] != "published":
        upd["slug"] = d["slug"]
    await db.notes.update_one({"id": nid}, {"$set": upd})
    await snapshot("note", nid, d, "draft saved", user)
    return await get_note(nid)


class PublishIn(BaseModel):
    create_redirect: bool = True


@router.post("/notes/{nid}/publish")
async def publish_note(nid: str, body: PublishIn = PublishIn(), user=Depends(require("content.publish"))):
    n = await get_note(nid)
    d = n["draft"]
    old = n.get("published", {}) and n["published"].get("slug")
    if old and old != d["slug"] and body.create_redirect:
        await db.redirects.update_one({"from_path": f"/field-notes/{old}"}, {"$set": {"to_path": f"/field-notes/{d['slug']}", "code": 301, "created_at": now(), "by": user["email"]}}, upsert=True)
    await db.redirects.delete_many({"from_path": f"/field-notes/{d['slug']}"})
    await db.notes.update_one({"id": nid}, {"$set": {"published": d, "slug": d["slug"], "status": "published", "published_at": n.get("published_at") or now(),
                                                      "updated_at": now(), "has_unpublished_changes": False}})
    await snapshot("note", nid, d, "published", user)
    return await get_note(nid)


NOTE_LIVE_FIELDS = {"title", "standfirst", "author", "credits", "body_html", "cover", "category", "kind", "references", "downloads", "styles"}


@router.put("/notes/{nid}/live")
async def note_live_save(nid: str, body: dict, user=Depends(require("content.publish"))):
    """Advanced live editor for a Field Note: patch allowed fields and publish immediately."""
    n = await get_note(nid)
    base = dict(n.get("published") or n.get("draft") or {})
    for k, v in (body or {}).items():
        if k in NOTE_LIVE_FIELDS:
            base[k] = v
    base["title"] = str(base.get("title", "")).strip()[:200] or "Untitled"
    base["cover"] = strip_resolved(base.get("cover") or {})
    base["references"] = strip_resolved(base.get("references") or [])
    base["downloads"] = strip_resolved(base.get("downloads") or [])
    base["styles"] = clean_styles(base.get("styles"))
    if base.get("kind", "article") not in NOTE_KINDS:
        raise HTTPException(400, "Choose a valid Field Note type")
    base["seo"] = clean_seo(base.get("seo") or {})
    d = sanitize_tree(base)
    await db.notes.update_one({"id": nid}, {"$set": {"draft": d, "published": d, "status": "published",
                                                      "published_at": n.get("published_at") or now(), "updated_at": now(), "has_unpublished_changes": False}})
    await snapshot("note", nid, d, "live edit published", user)
    return {"id": nid, "note": await resolve_media_tree(d)}


@router.post("/notes/{nid}/unpublish")
async def unpublish_note(nid: str, user=Depends(require("content.publish"))):
    n = await get_note(nid)
    await db.notes.update_one({"id": nid}, {"$set": {"status": "draft", "published": None, "updated_at": now(), "has_unpublished_changes": True}})
    await snapshot("note", nid, n["draft"], "unpublished", user)
    return await get_note(nid)


@router.delete("/notes/{nid}")
async def delete_note(nid: str, user=Depends(require("content.publish"))):
    n = await get_note(nid)
    if n["status"] == "published":
        raise HTTPException(409, "Unpublish this Field Note before deleting it")
    await db.notes.delete_one({"id": nid})
    return {"ok": True}


# ---------------- Redirects ----------------
class RedirectIn(BaseModel):
    from_path: str
    to_path: str


@router.get("/redirects")
async def list_redirects(user=Depends(current_user)):
    return await db.redirects.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)


@router.post("/redirects")
async def add_redirect(body: RedirectIn, user=Depends(require("content.publish"))):
    f, t = body.from_path.strip(), body.to_path.strip()
    if not f.startswith("/") or not t.startswith("/") or f == t:
        raise HTTPException(400, "Both addresses must start with / and be different")
    if f in PAGE_PATHS.values() or f.startswith("/admin") or f.startswith("/api"):
        raise HTTPException(400, "This address belongs to a live page and cannot be redirected")
    await db.redirects.update_one({"from_path": f}, {"$set": {"to_path": t, "code": 301, "created_at": now(), "by": user["email"]}}, upsert=True)
    return {"ok": True}


@router.delete("/redirects")
async def delete_redirect(from_path: str, user=Depends(require("content.publish"))):
    await db.redirects.delete_one({"from_path": from_path})
    return {"ok": True}


# ---------------- Settings, appearance, menus ----------------
def _lum(hexc):
    hexc = hexc.lstrip("#")
    rgb = [int(hexc[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in rgb]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contrast(a, b):
    la, lb = sorted([_lum(a), _lum(b)], reverse=True)
    return round((la + 0.05) / (lb + 0.05), 2)


def check_theme(theme):
    c = theme.get("colors", {})
    for k in ("background", "surface", "text", "green", "terracotta", "ochre"):
        if not re.match(r"^#[0-9A-Fa-f]{6}$", c.get(k, "")):
            raise HTTPException(400, f"Colour '{k}' must be a 6-digit hex value like #2D302B")
    pairs = [("text", "background"), ("text", "surface"), ("green", "background"), ("terracotta", "background")]
    report = [{"pair": f"{a} on {b}", "ratio": contrast(c[a], c[b]), "min": 4.5} for a, b in pairs]
    report.append({"pair": "ochre on background", "ratio": contrast(c["ochre"], c["background"]), "min": 3.0, "note": "Ochre is for decorative accents only unless it reaches 4.5"})
    failing = [r for r in report if r["ratio"] < r["min"]]
    return report, failing


FONTS = {"heading": ["Public Sans", "Lora", "Source Serif 4", "Libre Baskerville"], "body": ["Public Sans", "Source Sans 3", "Noto Sans", "Atkinson Hyperlegible"]}
SETTINGS_FIELDS = {"site_name", "full_name", "tagline", "logo_media_id", "favicon_media_id", "theme", "footer_text", "privacy_html",
                   "contact", "social", "preview_banner", "indexing_enabled", "default_share_media_id", "live_editor_enabled"}


class SiteLivePatch(BaseModel):
    path: str = Field(min_length=1, max_length=180)
    value: str = Field(max_length=20000)


@router.put("/site-live")
async def site_live_patch(body: SiteLivePatch, user=Depends(require("config"))):
    """Patch public copy only; never accept arbitrary settings or Mongo paths."""
    path = body.path
    plain = {"brand_label", "site_name", "full_name", "tagline", "privacy_html", "logo_media_id", "contact.email", "contact.phone"}
    menu = re.fullmatch(r"menus\.(main|footer)\.\d+(?:\.children\.\d+){0,2}\.label", path)
    ui = re.fullmatch(r"ui_text\.[a-z][a-z0-9_]{0,79}", path)
    social = re.fullmatch(r"social\.\d+\.label", path)
    if path not in plain and not (menu or ui or social):
        raise HTTPException(400, "This setting is not editable as public copy")
    s = await db.settings.find_one({"key": "site"}, {"_id": 0})
    if menu or social:
        current = s
        try:
            for part in path.split("."):
                current = current[int(part)] if isinstance(current, list) else current[part]
        except (KeyError, IndexError, ValueError, TypeError):
            raise HTTPException(400, "That menu or social item no longer exists")
        if not body.value.strip():
            raise HTTPException(400, "Link labels cannot be empty")
    if path == "logo_media_id" and body.value:
        logo = await db.media.find_one({"id": body.value}, {"_id": 0})
        if not logo or not media_public_ok(logo):
            raise HTTPException(400, "Choose an approved public logo image")
    value = sanitize_tree({path.split(".")[-1]: body.value})[path.split(".")[-1]]
    await db.settings.update_one({"key": "site"}, {"$set": {path: value, "updated_at": now()}})
    await snapshot("settings", "site", {"path": path, "value": value}, "public copy live edit", user)
    return {"path": path, "value": value}


HEADER_STYLE_KEYS = {"backgroundColor", "color", "fontFamily", "paddingTop", "paddingBottom"}
_css_value = re.compile(r"^[#0-9a-zA-Z .,%()\-'\"]{1,80}$")


class SiteStylesPatch(BaseModel):
    styles: dict


@router.put("/site-styles")
async def site_styles_patch(body: SiteStylesPatch, user=Depends(require("config"))):
    """Store whitelisted header presentation styles only; reject any CSS injection."""
    clean = {}
    for key, raw in (body.styles or {}).items():
        if key not in HEADER_STYLE_KEYS:
            continue
        val = ("" if raw is None else str(raw)).strip()
        if not val:
            continue
        if not _css_value.fullmatch(val):
            raise HTTPException(400, f"Invalid value for {key}")
        clean[key] = val
    await db.settings.update_one({"key": "site"}, {"$set": {"header_styles": clean, "updated_at": now()}})
    await snapshot("settings", "site", {"header_styles": clean}, "header style live edit", user)
    return {"header_styles": clean}


@router.get("/settings")
async def get_settings(user=Depends(current_user)):
    s = await db.settings.find_one({"key": "site"}, {"_id": 0})
    report, failing = check_theme(s["theme"])
    return s | {"contrast": report, "font_choices": FONTS, "default_theme": DEFAULT_THEME}


@router.post("/settings/contrast")
async def contrast_check(theme: dict, user=Depends(current_user)):
    report, failing = check_theme(theme)
    return {"report": report, "ok": not failing}


@router.put("/settings")
async def update_settings(body: dict, user=Depends(require("config"))):
    upd = {k: v for k, v in body.items() if k in SETTINGS_FIELDS}
    if "theme" in upd:
        _, failing = check_theme(upd["theme"])
        if failing:
            raise HTTPException(400, "Readability check failed: " + ", ".join(f"{f['pair']} is {f['ratio']}:1 (needs {f['min']}:1)" for f in failing))
        fonts = upd["theme"].get("fonts", {})
        if fonts.get("heading") not in FONTS["heading"] or fonts.get("body") not in FONTS["body"]:
            raise HTTPException(400, "Please choose one of the approved fonts")
        upd["theme"]["base_size"] = min(22, max(16, int(upd["theme"].get("base_size", 18))))
    if "social" in upd:
        upd["social"] = [{"label": str(x.get("label", ""))[:60], "url": str(x.get("url", ""))[:300]} for x in upd["social"] if str(x.get("url", "")).startswith("https://")]
    upd = sanitize_tree(upd)
    upd["updated_at"] = now()
    await db.settings.update_one({"key": "site"}, {"$set": upd})
    return await get_settings(user)


@router.put("/menus")
async def update_menus(body: dict, user=Depends(require("config"))):
    s = await db.settings.find_one({"key": "site"}, {"_id": 0})
    required = {i["id"] for i in s["menus"]["main"] if i.get("required")} | {c["id"] for i in s["menus"]["main"] for c in i.get("children", []) if c.get("required")}
    main = body.get("main", [])
    present = {i.get("id") for i in main} | {c.get("id") for i in main for c in i.get("children", [])}
    if required - present:
        raise HTTPException(400, "Required navigation items cannot be removed")
    for i in main + [c for i in main for c in i.get("children", [])] + body.get("footer", []):
        if not str(i.get("label", "")).strip() or not str(i.get("href", "")).startswith(("/", "https://")):
            raise HTTPException(400, "Every menu item needs a label and an address starting with / or https://")
    await db.settings.update_one({"key": "site"}, {"$set": {"menus": {"main": main, "footer": body.get("footer", [])}, "updated_at": now()}})
    return {"ok": True}


@router.put("/checklist")
async def update_checklist(body: list[dict], user=Depends(require("content.edit"))):
    items = [{"id": i.get("id") or new_id(), "label": str(i.get("label", ""))[:200], "done": bool(i.get("done"))} for i in body if i.get("label")]
    await db.settings.update_one({"key": "site"}, {"$set": {"checklist": items}})
    return items


@router.put("/taxonomy")
async def update_taxonomy(body: dict, user=Depends(require("content.edit"))):
    t = {"authors": [{"name": str(a.get("name", ""))[:120], "bio": str(a.get("bio", ""))[:1000]} for a in body.get("authors", []) if a.get("name")],
         "categories": [str(c)[:60] for c in body.get("categories", []) if c], "tags": [str(c)[:60] for c in body.get("tags", []) if c]}
    await db.settings.update_one({"key": "site"}, {"$set": {"taxonomy": t}})
    return t


# ---------------- Register ----------------
@router.get("/register")
async def list_register(user=Depends(current_user)):
    return await db.register.find({}, {"_id": 0}).to_list(500)


@router.put("/register/{rid}")
async def update_register(rid: str, body: dict, user=Depends(require("media.approve"))):
    upd = {k: str(v)[:2000] for k, v in body.items() if k in ("subject", "source", "direction", "status", "permission", "notes")}
    if "media_ids" in body:
        upd["media_ids"] = [str(x) for x in body["media_ids"]][:20]
    await db.register.update_one({"id": rid}, {"$set": upd})
    return await db.register.find_one({"id": rid}, {"_id": 0})


@router.post("/register")
async def add_register(body: dict, user=Depends(require("media.approve"))):
    doc = {"id": new_id(), "subject": str(body.get("subject", "New item"))[:200], "source": "", "direction": "", "status": "awaiting upload", "permission": "pending", "notes": "", "media_ids": []}
    await db.register.insert_one(doc)
    doc.pop("_id")
    return doc


# ---------------- Enquiries ----------------
@router.get("/enquiries")
async def list_enquiries(status: str = "", user=Depends(require("enquiries"))):
    f = {"status": status} if status else {}
    return await db.enquiries.find(f, {"_id": 0, "ip_hash": 0}).sort("created_at", -1).to_list(1000)


@router.put("/enquiries/{eid}")
async def update_enquiry(eid: str, body: dict, user=Depends(require("enquiries"))):
    upd = {}
    if body.get("status") in ("new", "read", "replied", "archived"):
        upd["status"] = body["status"]
    if "private_notes" in body:
        upd["private_notes"] = str(body["private_notes"])[:4000]
    upd["updated_at"] = now()
    await db.enquiries.update_one({"id": eid}, {"$set": upd})
    return await db.enquiries.find_one({"id": eid}, {"_id": 0, "ip_hash": 0})


@router.delete("/enquiries/{eid}")
async def delete_enquiry(eid: str, user=Depends(require("enquiries"))):
    await db.enquiries.delete_one({"id": eid})
    return {"ok": True}


@router.get("/enquiries-export.csv")
async def export_enquiries(user=Depends(require("config"))):
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = ["created_at", "name", "email", "phone", "organisation", "topic", "message", "status", "email_status"]
    w.writerow(cols)
    async for e in db.enquiries.find({}, {"_id": 0}).sort("created_at", -1):
        w.writerow([str(e.get(c, "")).replace("\n", " ") if not str(e.get(c, "")).startswith(("=", "+", "-", "@")) else "'" + str(e.get(c, "")) for c in cols])
    return Response(buf.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="usp-enquiries.csv"', "Cache-Control": "no-store"})


# ---------------- Users ----------------
class InviteIn(BaseModel):
    email: EmailStr
    name: str = ""
    role: str


@router.get("/users")
async def list_users(user=Depends(require("users"))):
    return [public_user(u) for u in await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(200)]


def invite_url(kind, token):
    return f"{os.environ['PREVIEW_URL']}/admin/{'accept-invite' if kind == 'invite' else 'reset-password'}?token={token}"


@router.post("/users/invite")
async def invite(body: InviteIn, user=Depends(require("users"))):
    if body.role not in ("owner", "editor", "contributor", "reviewer"):
        raise HTTPException(400, "Invalid role")
    email = body.email.lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(409, "A user with this email already exists")
    uid = new_id()
    await db.users.insert_one({"id": uid, "email": email, "name": body.name[:120] or email, "role": body.role, "active": False, "password_hash": "", "created_at": now(), "invited_by": user["email"]})
    t = await issue_token(uid, "invite", 72)
    return {"ok": True, "invite_url": invite_url("invite", t), "expires_in_hours": 72, "email_status": "not_configured"}


@router.post("/users/{uid}/reset-link")
async def reset_link(uid: str, user=Depends(require("users"))):
    if not await db.users.find_one({"id": uid}):
        raise HTTPException(404, "User not found")
    return {"reset_url": invite_url("reset", await issue_token(uid, "reset", 1)), "expires_in_hours": 1}


@router.put("/users/{uid}")
async def update_user(uid: str, body: dict, user=Depends(require("users"))):
    target = await db.users.find_one({"id": uid}, {"_id": 0})
    if not target:
        raise HTTPException(404, "User not found")
    upd = {}
    if "role" in body:
        if body["role"] not in ("owner", "editor", "contributor", "reviewer"):
            raise HTTPException(400, "Invalid role")
        upd["role"] = body["role"]
    if "active" in body:
        upd["active"] = bool(body["active"])
    if "name" in body:
        upd["name"] = str(body["name"])[:120]
    demoting = target["role"] == "owner" and (upd.get("role", "owner") != "owner" or upd.get("active") is False)
    if demoting and await db.users.count_documents({"role": "owner", "active": True}) <= 1:
        raise HTTPException(400, "At least one active owner is required")
    await db.users.update_one({"id": uid}, {"$set": upd})
    return public_user(await db.users.find_one({"id": uid}, {"_id": 0}))


@router.delete("/users/{uid}")
async def delete_user(uid: str, user=Depends(require("users"))):
    if uid == user["id"]:
        raise HTTPException(400, "You cannot delete your own account")
    t = await db.users.find_one({"id": uid})
    if t and t["role"] == "owner" and await db.users.count_documents({"role": "owner", "active": True}) <= 1:
        raise HTTPException(400, "At least one active owner is required")
    await db.users.delete_one({"id": uid})
    return {"ok": True}


# ---------------- Dashboard, SEO audit, backup ----------------
@router.get("/dashboard")
async def dashboard(user=Depends(current_user)):
    s = await db.settings.find_one({"key": "site"}, {"_id": 0, "checklist": 1, "email_notifications": 1})
    return {
        "pages_with_changes": await db.pages.count_documents({"has_unpublished_changes": True}),
        "notes_published": await db.notes.count_documents({"status": "published"}),
        "notes_draft": await db.notes.count_documents({"status": "draft"}),
        "enquiries_new": await db.enquiries.count_documents({"status": "new"}) if can(user, "enquiries") else None,
        "media_total": await db.media.count_documents({"is_deleted": False}),
        "media_pending": await db.media.count_documents({"is_deleted": False, "permission": "pending"}),
        "checklist": s["checklist"], "email_notifications": s["email_notifications"],
        "recent_comments": await db.comments.find({}, {"_id": 0}).sort("created_at", -1).to_list(5),
    }


def has_placeholder(obj):
    return "Draft placeholder" in str(obj)


@router.get("/seo/audit")
async def seo_audit(user=Depends(current_user)):
    s = await db.settings.find_one({"key": "site"}, {"_id": 0})
    rows = []
    for p in await db.pages.find({}, {"_id": 0}).to_list(50):
        rows.append(await audit_item("page", p["key"], p["path"], p["published"], s))
    for n in await db.notes.find({"status": "published"}, {"_id": 0}).to_list(500):
        rows.append(await audit_item("note", n["id"], f"/field-notes/{n['slug']}", n["published"], s))
    site_issues = [] if s.get("indexing_enabled") else ["Search indexing is switched off for the whole preview (robots noindex). Enable only after launch approval."]
    return {"items": rows, "site_issues": site_issues, "site_url": SITE_URL}


async def audit_item(etype, key, path, content, s):
    seo = content.get("seo", {})
    title = seo.get("title") or content.get("title", "")
    issues = []
    if not seo.get("description"):
        issues.append("No search description")
    elif not 50 <= len(seo["description"]) <= 160:
        issues.append(f"Description is {len(seo['description'])} characters (aim for 50–160)")
    if len(title) > 60:
        issues.append(f"Title is {len(title)} characters (may be shortened in results above ~60)")
    share = seo.get("share_media_id") or s.get("default_share_media_id")
    m = await db.media.find_one({"id": share}, {"_id": 0}) if share else None
    if not media_public_ok(m):
        issues.append("No approved sharing image")
    if seo.get("noindex"):
        issues.append("Set to noindex (excluded from search and sitemap)")
    if has_placeholder(content):
        issues.append("Contains draft placeholder text")
    return {"type": etype, "key": key, "path": path, "title": title, "description": seo.get("description", ""), "issues": issues}


@router.get("/backup")
async def backup(user=Depends(require("config"))):
    import json
    out = {"exported_at": now(), "note": "Metadata export. Media files remain in object storage at the recorded paths. Password hashes are excluded."}
    for c in ("settings", "pages", "notes", "media", "redirects", "register", "revisions", "comments", "enquiries"):
        out[c] = await db[c].find({}, {"_id": 0}).to_list(100000)
    out["users"] = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(1000)
    return Response(json.dumps(out, default=str, indent=1), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="usp-backup-{now()[:10]}.json"', "Cache-Control": "no-store"})


def _collect_media_paths(media_docs):
    paths, ctypes = set(), {}

    def walk(o):
        if isinstance(o, str):
            if o.startswith("uspindia/"):
                paths.add(o)
        elif isinstance(o, dict):
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for m in media_docs:
        walk(m)
        if m.get("original_path"):
            ctypes[m["original_path"]] = m.get("content_type") or "application/octet-stream"
        for d in m.get("derivs") or []:
            if d.get("path"):
                ctypes[d["path"]] = d.get("ctype") or "image/jpeg"
    return paths, ctypes


EXPORT_COLLECTIONS = ("settings", "pages", "notes", "media", "redirects")


@router.get("/site-export")
async def site_export(user=Depends(require("config"))):
    """Export the whole site (all content + media files) as a portable .zip to import elsewhere."""
    import json
    import zipfile
    import tempfile
    import asyncio
    import core
    content = {"version": 1, "exported_at": now(), "collections": {}}
    for c in EXPORT_COLLECTIONS:
        content["collections"][c] = await db[c].find({}, {"_id": 0}).to_list(100000)
    paths, ctypes = _collect_media_paths(content["collections"]["media"])
    sem = asyncio.Semaphore(16)

    async def fetch(p):
        async with sem:
            try:
                return p, await core.get_object(p)
            except Exception:
                return p, None
    fetched = await asyncio.gather(*[fetch(p) for p in sorted(paths)])
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    saved = 0
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("content.json", json.dumps(content, default=str))
        for p, data in fetched:
            if data:
                z.writestr(f"media/{p}", data)
                saved += 1
        z.writestr("manifest.json", json.dumps({
            "version": 1, "exported_at": now(), "ctypes": ctypes,
            "counts": {c: len(v) for c, v in content["collections"].items()},
            "media_paths": len(paths), "media_saved": saved,
        }, default=str))
    tmp.flush()
    tmp.close()
    return FileResponse(tmp.name, media_type="application/zip", filename=f"usp-site-export-{now()[:10]}.zip",
                        headers={"Cache-Control": "no-store"})


@router.post("/site-import")
async def site_import(file: UploadFile = File(...), user=Depends(require("config"))):
    """Import a site-export .zip: restores all content and re-uploads media to this environment's storage."""
    import json
    import io as _io
    import zipfile
    import core
    raw = await file.read()
    try:
        z = zipfile.ZipFile(_io.BytesIO(raw))
        content = json.loads(z.read("content.json"))
    except Exception:
        raise HTTPException(400, "Invalid export file. Upload a .zip produced by Export.")
    ctypes = {}
    try:
        ctypes = json.loads(z.read("manifest.json")).get("ctypes", {})
    except Exception:
        pass
    media_ok = 0
    for name in z.namelist():
        if name.startswith("media/") and not name.endswith("/"):
            path = name[len("media/"):]
            data = z.read(name)
            if data:
                try:
                    await core.put_object(path, data, ctypes.get(path, "application/octet-stream"))
                    media_ok += 1
                except Exception:
                    pass
    summary = {}
    for c, docs in (content.get("collections") or {}).items():
        if c not in EXPORT_COLLECTIONS:
            continue
        n = 0
        for d in docs:
            kf = next((k for k in ("key", "id", "from", "slug") if d.get(k) is not None), None)
            if not kf:
                continue
            await db[c].replace_one({kf: d[kf]}, d, upsert=True)
            n += 1
        summary[c] = n
    await snapshot("site", "import", {"counts": summary, "media": media_ok}, "site imported", user)
    return {"ok": True, "imported": summary, "media_restored": media_ok}
