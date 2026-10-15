import io
import hashlib
from fastapi import APIRouter, Request, HTTPException, Depends, UploadFile, File, Form
from fastapi.responses import Response
from core import (db, now, new_id, require, current_user, can, process_image, put_object, get_object,
                  media_public_ok, collect_media_ids, MAX_UPLOAD, APP_NAME)

router = APIRouter(prefix="/api")
_cache = {}

AUTH_VALUES = {"original", "edited_original", "ai_reference", "unverified"}
PERM_VALUES = {"pending", "approved", "restricted", "withdrawn"}
EDIT_VALUES = {"pending", "approved", "rejected"}
EDITABLE = {"alt", "caption", "credit", "category", "focal_desktop", "focal_mobile", "permitted_use", "title", "description"}
APPROVAL_FIELDS = {"authenticity", "permission", "edit_approval", "permission_notes", "permission_expiry", "evidence_ref",
                   "may_include_minors", "minor_approval_documented"}


async def fetch(path):
    if path in _cache:
        return _cache[path]
    data = await get_object(path)
    if len(_cache) > 150:
        _cache.pop(next(iter(_cache)))
    _cache[path] = data
    return data


async def store_file(media_id, data, filename, version):
    ext = (filename.rsplit(".", 1)[-1] if "." in filename else "bin").lower()[:5]
    if data[:5] == b"%PDF-":
        path = await put_object(f"{APP_NAME}/files/{media_id}/v{version}.pdf", data, "application/pdf")
        return {"kind": "file", "original_path": path, "content_type": "application/pdf", "width": None, "height": None, "derivs": [], "format": "PDF"}
    info = process_image(data)
    ctype = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[info["format"]]
    orig = await put_object(f"{APP_NAME}/originals/{media_id}/v{version}.{ext}", data, ctype)
    derivs = []
    for d in info["derivs"]:
        p = await put_object(f"{APP_NAME}/display/{media_id}/v{version}-{d['w']}", d["bytes"], d["ctype"])
        derivs.append({"w": d["w"], "h": d["h"], "path": p, "ctype": d["ctype"]})
    return {"kind": "image", "original_path": orig, "content_type": ctype, "width": info["width"], "height": info["height"], "derivs": derivs, "format": info["format"]}


async def read_upload(file: UploadFile):
    data = await file.read()
    if not data:
        raise HTTPException(400, "Empty file")
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "File is larger than 20 MB")
    return data


async def usage_of(media_id):
    out = []
    async for p in db.pages.find({}, {"_id": 0, "key": 1, "path": 1, "draft": 1, "published": 1}):
        where = [s for s in ("draft", "published") if media_id in collect_media_ids(p.get(s), set())]
        if where:
            out.append({"type": "page", "key": p["key"], "label": p["path"], "versions": where})
    async for n in db.notes.find({}, {"_id": 0, "id": 1, "draft": 1, "published": 1}):
        where = [s for s in ("draft", "published") if media_id in collect_media_ids(n.get(s), set())]
        if where:
            out.append({"type": "note", "key": n["id"], "label": (n.get("draft") or {}).get("title"), "versions": where})
    s = await db.settings.find_one({"key": "site"}, {"_id": 0})
    for f in ("logo_media_id", "favicon_media_id", "default_share_media_id"):
        if s and s.get(f) == media_id:
            out.append({"type": "settings", "key": f, "label": f.replace("_media_id", "").replace("_", " "), "versions": ["published"]})
    return out


def admin_view(m):
    m = {k: v for k, v in m.items() if k not in ("_id",)}
    m["thumb"] = f"/api/admin/media/{m['id']}/view/{m['derivs'][0]['w']}?v={m.get('version', 1)}" if m.get("derivs") else ""
    m["preview"] = f"/api/admin/media/{m['id']}/view/{m['derivs'][-1]['w']}?v={m.get('version', 1)}" if m.get("derivs") else ""
    m["public_ok"] = media_public_ok(m)
    return m


@router.get("/admin/media")
async def list_media(q: str = "", category: str = "", permission: str = "", kind: str = "", user=Depends(current_user)):
    f = {"is_deleted": False}
    if q:
        f["$or"] = [{k: {"$regex": q, "$options": "i"}} for k in ("filename", "alt", "caption", "credit", "title")]
    if category:
        f["category"] = category
    if permission:
        f["permission"] = permission
    if kind:
        f["kind"] = kind
    items = await db.media.find(f, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [admin_view(m) for m in items]


@router.post("/admin/media")
async def upload_media(file: UploadFile = File(...), category: str = Form("uncategorised"), user=Depends(require("media.edit"))):
    data = await read_upload(file)
    sha = hashlib.sha256(data).hexdigest()
    dup = await db.media.find_one({"sha256": sha, "is_deleted": False}, {"_id": 0})
    if dup:
        await db.media.update_one({"id": dup["id"]}, {"$push": {"archived_sources": {"filename": file.filename, "uploaded_at": now(), "by": user["email"]}}})
        return admin_view(dup) | {"duplicate": True}
    mid = new_id()
    stored = await store_file(mid, data, file.filename or "upload", 1)
    doc = {"id": mid, "filename": file.filename, "sha256": sha, "size": len(data), "category": category[:60], "title": "",
           "alt": "", "caption": "", "credit": "", "permitted_use": "", "authenticity": "unverified", "permission": "pending",
           "edit_approval": "pending", "permission_notes": "", "permission_expiry": "", "evidence_ref": "",
           "may_include_minors": False, "minor_approval_documented": False, "focal_desktop": {"x": 50, "y": 50},
           "focal_mobile": {"x": 50, "y": 50}, "version": 1, "versions": [], "derived_from": "", "archived_sources": [],
           "is_deleted": False, "uploaded_by": user["email"], "created_at": now(), "updated_at": now(), **stored}
    await db.media.insert_one(doc)
    return admin_view(doc)


async def get_media(mid):
    m = await db.media.find_one({"id": mid, "is_deleted": False}, {"_id": 0})
    if not m:
        raise HTTPException(404, "Media not found")
    return m


@router.get("/admin/media/{mid}")
async def media_detail(mid: str, user=Depends(current_user)):
    m = await get_media(mid)
    derived = await db.media.find({"derived_from": mid, "is_deleted": False}, {"_id": 0}).to_list(50)
    original = await db.media.find_one({"id": m["derived_from"]}, {"_id": 0}) if m.get("derived_from") else None
    return admin_view(m) | {"usage": await usage_of(mid), "derivatives": [admin_view(d) for d in derived],
                            "original": admin_view(original) if original else None}


@router.put("/admin/media/{mid}")
async def update_media(mid: str, body: dict, user=Depends(require("media.edit"))):
    m = await get_media(mid)
    upd = {k: v for k, v in body.items() if k in EDITABLE}
    appr = {k: v for k, v in body.items() if k in APPROVAL_FIELDS and v != m.get(k)}
    if appr and not can(user, "media.approve"):
        raise HTTPException(403, "Only editors and owners can change provenance, permission or approval")
    for k, allowed in (("authenticity", AUTH_VALUES), ("permission", PERM_VALUES), ("edit_approval", EDIT_VALUES)):
        if k in appr and appr[k] not in allowed:
            raise HTTPException(400, f"Invalid value for {k}")
    upd.update(appr)
    for k in ("alt", "caption", "credit"):
        if k in upd:
            upd[k] = str(upd[k])[:1000]
    upd["updated_at"] = now()
    log_entry = {"at": now(), "by": user["email"], "changes": {k: v for k, v in appr.items()}}
    await db.media.update_one({"id": mid}, {"$set": upd, **({"$push": {"approval_log": log_entry}} if appr else {})})
    _cache.clear() if appr else None
    return admin_view(await get_media(mid))


@router.post("/admin/media/{mid}/replace")
async def replace_media(mid: str, file: UploadFile = File(...), user=Depends(require("media.edit"))):
    m = await get_media(mid)
    data = await read_upload(file)
    ver = m.get("version", 1) + 1
    stored = await store_file(mid, data, file.filename or "upload", ver)
    prev = {k: m.get(k) for k in ("filename", "original_path", "derivs", "width", "height", "content_type", "sha256", "version")} | {"replaced_at": now(), "replaced_by": user["email"]}
    await db.media.update_one({"id": mid}, {"$set": {**stored, "filename": file.filename, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "version": ver, "updated_at": now()},
                                            "$push": {"versions": prev}})
    return admin_view(await get_media(mid))


@router.post("/admin/media/{mid}/restore-version/{version}")
async def restore_version(mid: str, version: int, user=Depends(require("media.edit"))):
    m = await get_media(mid)
    old = next((v for v in m.get("versions", []) if v.get("version") == version), None)
    if not old:
        raise HTTPException(404, "Version not found")
    cur = {k: m.get(k) for k in ("filename", "original_path", "derivs", "width", "height", "content_type", "sha256", "version")} | {"replaced_at": now(), "replaced_by": user["email"]}
    ver = m.get("version", 1) + 1
    restored = {k: old[k] for k in ("filename", "original_path", "derivs", "width", "height", "content_type", "sha256")}
    await db.media.update_one({"id": mid}, {"$set": {**restored, "version": ver, "updated_at": now()}, "$push": {"versions": cur}})
    return admin_view(await get_media(mid))


@router.post("/admin/media/{mid}/derivative")
async def upload_derivative(mid: str, file: UploadFile = File(...), edit_log: str = Form(""), user=Depends(require("media.edit"))):
    orig = await get_media(mid)
    data = await read_upload(file)
    nid = new_id()
    stored = await store_file(nid, data, file.filename or "edit", 1)
    doc = {k: orig.get(k) for k in ("category", "alt", "caption", "credit", "permitted_use", "permission", "permission_notes", "permission_expiry",
                                     "evidence_ref", "may_include_minors", "minor_approval_documented", "focal_desktop", "focal_mobile", "title")}
    doc.update({"id": nid, "filename": file.filename, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data), "authenticity": "edited_original",
                "edit_approval": "pending", "edit_log": edit_log[:4000], "derived_from": mid, "version": 1, "versions": [], "archived_sources": [],
                "is_deleted": False, "uploaded_by": user["email"], "created_at": now(), "updated_at": now(), **stored})
    await db.media.insert_one(doc)
    return admin_view(doc)


def swap_ids(obj, old, new):
    if isinstance(obj, dict):
        return {k: (new if k == "media_id" and v == old else swap_ids(v, old, new)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [swap_ids(v, old, new) for v in obj]
    return obj


@router.post("/admin/media/{mid}/revert-to-original")
async def revert_to_original(mid: str, user=Depends(require("content.publish"))):
    m = await get_media(mid)
    if not m.get("derived_from"):
        raise HTTPException(400, "This item is not an edited derivative")
    count = 0
    for coll in (db.pages, db.notes):
        async for d in coll.find({}, {"_id": 0}):
            if mid in collect_media_ids([d.get("draft"), d.get("published")], set()):
                await coll.update_one({"id": d["id"]}, {"$set": {"draft": swap_ids(d.get("draft"), mid, m["derived_from"]),
                                                                  "published": swap_ids(d.get("published"), mid, m["derived_from"]), "updated_at": now()}})
                count += 1
    return {"ok": True, "updated": count}


@router.delete("/admin/media/{mid}")
async def delete_media(mid: str, user=Depends(require("media.approve"))):
    await get_media(mid)
    used = [u for u in await usage_of(mid) if "published" in u["versions"]]
    if used:
        raise HTTPException(409, "This file is used on published content. Remove it from those places first.")
    await db.media.update_one({"id": mid}, {"$set": {"is_deleted": True, "deleted_at": now(), "deleted_by": user["email"]}})
    return {"ok": True}


def serve(data, ctype, cache, download_name=None):
    h = {"Cache-Control": cache, "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"}
    if download_name:
        h["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return Response(content=data, media_type=ctype, headers=h)


@router.get("/admin/media/{mid}/view/{w}")
async def admin_view_file(mid: str, w: int, user=Depends(current_user)):
    m = await get_media(mid)
    d = next((x for x in m.get("derivs", []) if x["w"] == w), None) or (m["derivs"][-1] if m.get("derivs") else None)
    if not d:
        raise HTTPException(404, "No preview")
    return serve(await fetch(d["path"]), d["ctype"], "private, no-store")


@router.get("/admin/media/{mid}/version/{version}/view")
async def admin_version_view(mid: str, version: int, user=Depends(current_user)):
    m = await get_media(mid)
    v = next((x for x in m.get("versions", []) if x.get("version") == version), None)
    if not v or not v.get("derivs"):
        raise HTTPException(404, "Version not found")
    d = v["derivs"][-1]
    return serve(await fetch(d["path"]), d["ctype"], "private, no-store")


@router.get("/admin/media/{mid}/original")
async def admin_original(mid: str, user=Depends(require("media.edit"))):
    m = await get_media(mid)
    return serve(await fetch(m["original_path"]), m["content_type"], "private, no-store", m.get("filename"))


@router.get("/media/{mid}/file")
async def public_file(mid: str):
    m = await db.media.find_one({"id": mid}, {"_id": 0})
    if not media_public_ok(m) or m.get("kind") != "file":
        raise HTTPException(404, "Not found")
    return serve(await fetch(m["original_path"]), "application/pdf", "public, max-age=300", m.get("filename"))


@router.get("/media/{mid}/{w}")
async def public_image(mid: str, w: int):
    m = await db.media.find_one({"id": mid}, {"_id": 0})
    if not media_public_ok(m) or m.get("kind") != "image":
        raise HTTPException(404, "Not found")
    d = next((x for x in m["derivs"] if x["w"] == w), None)
    if not d:
        raise HTTPException(404, "Not found")
    try:
        data = await fetch(d["path"])
    except Exception:
        # Transient object-storage error (e.g. rate limit) — 503 so caches don't store it and the browser retries.
        raise HTTPException(503, "Image temporarily unavailable")
    return serve(data, d["ctype"], "public, max-age=31536000, immutable")
