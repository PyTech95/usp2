from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from core import db, require, now
from content_sync.schema import MAX_BYTES, encoded
from content_sync.state import lease
from content_json.service import current_content, export_document, plan_import, apply_import, backup_document

router = APIRouter(prefix="/api/admin")


class Counts(BaseModel):
    total: int
    created: int
    updated: int
    unchanged: int


class ImportPreview(BaseModel):
    sha256: str
    state: str
    counts: dict[str, Counts]
    warnings: list[str]


class ImportResult(BaseModel):
    ok: bool
    backup_id: str
    counts: dict[str, Counts]
    media_files_restored: int


async def uploaded_json(file):
    if not (file.filename or "").lower().endswith(".json"):
        raise HTTPException(400, "Choose a .json file. Use the separate ZIP import for full site archives.")
    return await file.read(MAX_BYTES + 1)


def download(document, filename):
    return Response(encoded(document), media_type="application/json", headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


@router.get("/content-export")
async def export_json(user=Depends(require("config"))):
    async with lease(db, "promotion"):
        content = await current_content(db)
    return download(export_document(content["collections"], content["site"]), f"usp-content-{now()[:10]}.json")


@router.post("/content-import/preview", response_model=ImportPreview)
async def preview_json(file: UploadFile = File(...), user=Depends(require("config"))):
    plan = await plan_import(db, await uploaded_json(file))
    return ImportPreview(**{key: plan[key] for key in ("sha256", "state", "counts", "warnings")})


@router.post("/content-import", response_model=ImportResult)
async def import_json(file: UploadFile = File(...), expected_sha256: str = Form(..., min_length=64, max_length=64),
                      expected_state: str = Form(..., min_length=64, max_length=64), user=Depends(require("config"))):
    return ImportResult(**await apply_import(db, await uploaded_json(file), expected_sha256, expected_state, user["email"]))


@router.get("/content-import/backups/{bid}")
async def download_import_backup(bid: str, user=Depends(require("config"))):
    return download(await backup_document(db, bid), f"usp-before-import-{bid}.json")