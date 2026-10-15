import os
import io
import time
import uuid
import logging
import hashlib
import threading
from datetime import datetime, timezone, date
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

import bcrypt
import jwt
import nh3
import requests
from fastapi import Request, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from starlette.concurrency import run_in_threadpool

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]
SITE_URL = os.environ["SITE_URL"].rstrip("/")
JWT_SECRET = os.environ["JWT_SECRET"]
APP_NAME = "uspindia"
log = logging.getLogger("usp")

PAGE_PATHS = {
    "home": "/", "about": "/about", "our-work": "/our-work",
    "rakhigarhi": "/our-work/rakhigarhi", "theatre": "/our-work/theatre",
    "craft-livelihood": "/our-work/craft-livelihood",
    "workshops-learning": "/our-work/workshops-learning",
    "field-notes": "/field-notes", "connect": "/connect",
}
PATH_TO_PAGE = {v: k for k, v in PAGE_PATHS.items()}

PERMS = {
    "owner": {"content.edit", "content.publish", "media.edit", "media.approve", "enquiries", "config", "users", "review", "notes.draft"},
    "editor": {"content.edit", "content.publish", "media.edit", "media.approve", "enquiries", "review", "notes.draft"},
    "contributor": {"notes.draft", "media.edit"},
    "reviewer": {"review"},
}


def now():
    return datetime.now(timezone.utc).isoformat()


def new_id():
    return uuid.uuid4().hex


def hash_password(p):
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()


def verify_password(p, h):
    try:
        return bcrypt.checkpw(p.encode(), h.encode())
    except ValueError:
        return False


def make_token(user_id, kind, minutes):
    from datetime import timedelta
    exp = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    return jwt.encode({"sub": user_id, "type": kind, "exp": exp}, JWT_SECRET, algorithm="HS256")


def public_user(u):
    return {k: u.get(k) for k in ("id", "email", "name", "role", "active", "created_at")}


async def current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        h = request.headers.get("Authorization", "")
        token = h[7:] if h.startswith("Bearer ") else None
    if not token:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Session expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid session")
    if payload.get("type") != "access":
        raise HTTPException(401, "Invalid session")
    u = await db.users.find_one({"id": payload["sub"], "active": True}, {"_id": 0, "password_hash": 0})
    if not u:
        raise HTTPException(401, "User not found")
    return u


def can(user, perm):
    return perm in PERMS.get(user["role"], set())


def require(perm):
    async def dep(request: Request):
        u = await current_user(request)
        if not can(u, perm):
            raise HTTPException(403, "Your role does not allow this action")
        return u
    return dep


ALLOWED_TAGS = {"p", "h2", "h3", "h4", "strong", "em", "b", "i", "a", "ul", "ol", "li", "blockquote", "br", "cite", "sup", "sub"}


def sanitize(htmltext):
    return nh3.clean(htmltext or "", tags=ALLOWED_TAGS, attributes={"a": {"href", "title"}},
                     url_schemes={"http", "https", "mailto"}, link_rel="noopener noreferrer")


def sanitize_tree(obj):
    if isinstance(obj, dict):
        return {k: (sanitize(v) if k.endswith("_html") and isinstance(v, str) else sanitize_tree(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_tree(x) for x in obj]
    return obj


def ip_hash(request: Request):
    ip = (request.headers.get("x-forwarded-for") or (request.client.host if request.client else "")).split(",")[0].strip()
    return hashlib.sha256((ip + JWT_SECRET[:8]).encode()).hexdigest()[:24]


# ---------- Object storage ----------
_STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = _STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
_storage_key = None
_storage_lock = threading.Lock()


def _req(method, url, **kwargs):
    """HTTP call that retries on 429/transient 5xx with exponential backoff (honours Retry-After)."""
    delay = 0.5
    r = None
    for attempt in range(5):
        r = requests.request(method, url, **kwargs)
        if r.status_code in (429, 502, 503, 504):
            ra = r.headers.get("Retry-After")
            try:
                wait = float(ra) if ra else delay
            except ValueError:
                wait = delay
            time.sleep(min(max(wait, 0.1), 8))
            delay = min(delay * 2, 8)
            continue
        return r
    return r  # exhausted; caller's raise_for_status surfaces it


def init_storage(force=False):
    global _storage_key
    if _storage_key and not force:
        return _storage_key
    # Share a single /init across a cold-start burst instead of each image racing it.
    with _storage_lock:
        if _storage_key and not force:
            return _storage_key
        r = _req("POST", f"{STORAGE_URL}/init", json={"emergent_key": os.environ["EMERGENT_LLM_KEY"]}, timeout=30)
        r.raise_for_status()
        _storage_key = r.json()["storage_key"]
        return _storage_key


def _put(path, data, ctype):
    for attempt in range(2):
        r = _req("PUT", f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(attempt == 1), "Content-Type": ctype}, data=data, timeout=120)
        if r.status_code == 404 and attempt == 0:
            continue
        r.raise_for_status()
        return r.json()["path"]


def _get(path):
    for attempt in range(2):
        r = _req("GET", f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": init_storage(attempt == 1)}, timeout=60)
        if r.status_code == 404 and attempt == 0:
            continue
        r.raise_for_status()
        return r.content


async def put_object(path, data, ctype):
    return await run_in_threadpool(_put, path, data, ctype)


async def get_object(path):
    return await run_in_threadpool(_get, path)


# ---------- Images ----------
MAX_UPLOAD = 20 * 1024 * 1024


def process_image(data: bytes):
    """Validate by content; return original format info and EXIF/GPS-free display derivatives (never upscaled)."""
    from PIL import Image, ImageOps
    try:
        Image.open(io.BytesIO(data)).verify()
        img = Image.open(io.BytesIO(data))
    except Exception:
        raise HTTPException(400, "File is not a valid image")
    fmt = img.format
    if fmt not in ("JPEG", "PNG", "WEBP"):
        raise HTTPException(400, "Only JPEG, PNG or WebP images are accepted")
    img = ImageOps.exif_transpose(img)
    has_alpha = img.mode in ("RGBA", "LA", "P") and fmt == "PNG"
    w, h = img.size
    derivs = []
    for target in (800, 1600):
        if derivs and derivs[-1]["w"] >= w:
            break
        im = img.copy()
        if im.width > target:
            im.thumbnail((target, 100000), Image.LANCZOS)
        buf = io.BytesIO()
        if has_alpha:
            im.convert("RGBA").save(buf, "PNG", optimize=True)
        else:
            im.convert("RGB").save(buf, "JPEG", quality=86, optimize=True, progressive=True)
        derivs.append({"w": im.width, "h": im.height, "bytes": buf.getvalue(), "ctype": "image/png" if has_alpha else "image/jpeg"})
    return {"format": fmt, "width": w, "height": h, "derivs": derivs}


def media_public_ok(m):
    if not m or m.get("is_deleted") or m.get("kind") != "image" and m.get("kind") != "file":
        return False
    if m.get("authenticity") not in ("original", "edited_original"):
        return False
    if m.get("permission") != "approved":
        return False
    if m.get("edit_approval") == "rejected":
        return False
    if m.get("authenticity") == "edited_original" and m.get("edit_approval") != "approved":
        return False
    if m.get("may_include_minors") and not m.get("minor_approval_documented"):
        return False
    exp = m.get("permission_expiry")
    if exp and exp < date.today().isoformat():
        return False
    return True


def media_public_view(m, override=None):
    override = override or {}
    srcs = [{"w": d["w"], "url": f"/api/media/{m['id']}/{d['w']}?v={m.get('version', 1)}"} for d in m.get("derivs", [])]
    largest = m["derivs"][-1] if m.get("derivs") else {"w": m.get("width"), "h": m.get("height")}
    return {
        "id": m["id"], "kind": m.get("kind"), "width": largest["w"], "height": largest["h"], "srcs": srcs,
        "src": srcs[-1]["url"] if srcs else f"/api/media/{m['id']}/file",
        "alt": override.get("alt") or m.get("alt", ""), "caption": m.get("caption", ""), "credit": m.get("credit", ""),
        "focal_desktop": override.get("focal_desktop") or m.get("focal_desktop") or {"x": 50, "y": 50},
        "focal_mobile": override.get("focal_mobile") or m.get("focal_mobile") or {"x": 50, "y": 50},
        "filename": m.get("filename"), "public_ok": True,
    }


def collect_media_ids(obj, acc):
    if isinstance(obj, dict):
        if obj.get("media_id"):
            acc.add(obj["media_id"])
        for v in obj.values():
            collect_media_ids(v, acc)
    elif isinstance(obj, list):
        for v in obj:
            collect_media_ids(v, acc)
    return acc


async def resolve_media_tree(obj, admin=False):
    """Attach `media` to every {media_id} ref. Public mode only exposes eligible media."""
    ids = collect_media_ids(obj, set())
    docs = {m["id"]: m async for m in db.media.find({"id": {"$in": list(ids)}}, {"_id": 0})}
    orig_ids = [m["derived_from"] for m in docs.values() if m.get("derived_from")]
    originals = {m["id"]: m async for m in db.media.find({"id": {"$in": orig_ids}}, {"_id": 0})} if orig_ids else {}

    def attach_original(view, m, o):
        orig = originals.get(m.get("derived_from"))
        if orig and not o.get("hide_original") and orig.get("authenticity") == "original" and media_public_ok(orig):
            ov = media_public_view(orig)
            view["original"] = {k: ov[k] for k in ("id", "src", "srcs", "width", "height", "alt")}
            view["edit_note"] = (m.get("edit_log") or "")[:300]
        return view

    def walk(o):
        if isinstance(o, dict):
            o = {k: walk(v) for k, v in o.items()}
            if "media_id" in o:
                m = docs.get(o.get("media_id"))
                if m and media_public_ok(m):
                    o["media"] = attach_original(media_public_view(m, o), m, o)
                elif m and admin:
                    v = media_public_view(m, o)
                    v.update(public_ok=False, srcs=[{"w": d["w"], "url": f"/api/admin/media/{m['id']}/view/{d['w']}"} for d in m.get("derivs", [])])
                    v["src"] = v["srcs"][-1]["url"] if v["srcs"] else ""
                    o["media"] = v
                else:
                    o["media"] = None
            return o
        if isinstance(o, list):
            return [walk(v) for v in o]
        return o
    return walk(obj)
