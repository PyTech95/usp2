from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from core import db, require
from content_sync import schema
from content_sync.state import is_source
from content_sync.source import capture, baked
from content_sync.target import apply, restore

router = APIRouter(prefix="/api/admin/content-release")


@router.get("")
async def status(user=Depends(require("config"))):
    cfg = schema.config()
    if not cfg:
        return {"configured": False}
    role = "source" if await is_source(db, cfg) else "target"
    current = await db.content_runtime.find_one({"key": role}, {"_id": 0}) or {"state": "pending"}
    backups = await db.content_backups.find({"state": "ready"}, {"_id": 0}).sort("created_at", -1).limit(10).to_list(10)
    return {"configured": True, "role": role, "current": current, "backups": backups,
            "preserved": ["saved live editor changes", "users", "passwords", "sessions", "enquiries", "email configuration", "indexing policy"]}


@router.post("/prepare")
async def prepare(user=Depends(require("config"))):
    try:
        result = await capture(db, force=True, archive=True)
        if result.get("state") == "target":
            raise HTTPException(409, "Prepare releases in the preview source, not on the live site")
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, "The complete release could not be prepared. Existing content is unchanged; retry before republishing.")


@router.post("/apply")
async def apply_latest(user=Depends(require("config"))):
    try:
        bundle, pointer = baked()
        return await apply(db, bundle, pointer, force=True)
    except ValueError as error:
        raise HTTPException(409, str(error))
    except Exception:
        raise HTTPException(503, "Import failed. The pre-import backup was retained; check content release status.")


class Confirmation(BaseModel):
    confirm: bool


@router.post("/restore/{backup_id}")
async def restore_backup(backup_id: str, body: Confirmation, user=Depends(require("config"))):
    if not body.confirm:
        raise HTTPException(400, "Explicit confirmation is required")
    try:
        return await restore(db, backup_id)
    except ValueError as error:
        raise HTTPException(400, str(error))