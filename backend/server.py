import os
import logging
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from core import db, client, init_storage, log
import routes_auth
import routes_admin
import routes_media
import routes_public
import routes_content_release
from content_sync import runtime as content_runtime
from seed import seed

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
app = FastAPI(title="USP India CMS", docs_url=None, redoc_url=None, openapi_url=None)
ALLOWED_ORIGINS = [o.strip() for o in os.environ["CORS_ORIGINS"].split(",") if o.strip()]
CSRF_EXEMPT = {"/api/auth/login", "/api/auth/forgot-password", "/api/auth/reset-password", "/api/auth/accept-invite", "/api/public/enquiries", "/api/auth/logout"}


@app.middleware("http")
async def security(request: Request, call_next):
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        host = request.headers.get("x-forwarded-host") or request.headers.get("host")
        if origin and origin not in ALLOWED_ORIGINS and urlsplit(origin).netloc != host:
            return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
        if request.cookies.get("access_token") or request.cookies.get("refresh_token"):
            if request.url.path not in CSRF_EXEMPT:
                tok = request.cookies.get("csrf_token")
                if not tok or request.headers.get("x-csrf-token") != tok:
                    return JSONResponse({"detail": "Security token missing or invalid. Please reload the page."}, status_code=403)
    resp = await call_next(request)
    release = await content_runtime.after_mutation(request.url.path, request.method, resp.status_code)
    if release:
        resp.headers["X-Content-Release-State"] = release["state"]
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.url.path.startswith("/api/admin") or request.url.path.startswith("/api/auth"):
        resp.headers["Cache-Control"] = "no-store"
        resp.headers["X-Robots-Tag"] = "noindex"
    return resp


for r in (routes_auth.router, routes_admin.router, routes_media.router, routes_public.router, routes_content_release.router):
    app.include_router(r)

app.add_middleware(CORSMiddleware, allow_credentials=True, allow_origins=ALLOWED_ORIGINS, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
async def startup():
    await seed()
    try:
        init_storage()
        log.info("Object storage initialised")
    except Exception as e:
        log.error("Object storage init failed: %s", e)
    # Target readiness waits for a complete, validated, backup-first import.
    # A failure must not silently serve half-imported/default content.
    await content_runtime.startup()


@app.get("/api/health")
async def health():
    await db.command("ping")
    if not await content_runtime.readiness():
        return JSONResponse({"ok": False, "content_release": "pending_or_failed"}, status_code=503)
    return {"ok": True}


@app.on_event("shutdown")
async def shutdown():
    client.close()
