"""Apply the approved Workshops PDF/reference once to the configured database.

Preserves pre-change published/draft revisions. Never runs on application startup.
Existing media records and other pages are not modified.
"""
import asyncio
import copy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import db, now, new_id

KEY = "workshops-learning"
VERSION = "workshops-reference-2026-10-15"


def paras(*text):
    return "".join(f"<p>{p}</p>" for p in text)


def placeholder(label):
    return {"media_id": "", "placeholder": True, "placeholder_label": label, "caption": ""}


def transform(content):
    content = copy.deepcopy(content)
    sections = content["sections"]
    for s in sections:
        d = s["data"]
        anchor = d.get("anchor")
        if s["type"] == "hero":
            intro = d.get("intro", "").split("\n\n")
            d.update(image=placeholder("Workshop photograph"), intro="")
            learning = {"id": "workshops-learning-intro", "type": "text", "hidden": False,
                        "data": {"anchor": "learning-intro", "style": "columns", "eyebrow": "",
                                 "heading": intro[-1], "body_html": paras(*intro[:-1])}}
        elif anchor == "heritage-guide":
            s["type"] = "image"
            d.update(image=placeholder("Heritage Guide Program photograph"), crop="16/7", layout="wide")
        elif anchor == "restoration-skills":
            s["type"] = "image_text"
            d.update(image=placeholder("Restoration skills photograph"), image_side="left", crop="4/3", band=False,
                     body_html=paras("As the Rakhigarhi haveli and chaupal are restored, local workers learn alongside conservation professionals, gaining practical skills in traditional building techniques.",
                                     "The restoration becomes a place of learning, with skills that remain with the workers long after the work is complete."))
        elif anchor == "creative-exchange":
            d.update(image=placeholder("Creative exchange photograph"), crop="4/3", image_side="right")
        elif anchor == "student-projects":
            d.update(link_label="Explore Film", link_href="")
        elif d.get("eyebrow") == "The Ambition":
            d.update(anchor="ambition", style="stacked", band=True,
                     body_html=paras("The ambition is for learning to extend beyond any one workshop, project or exchange.",
                                     "Over time, this can give people greater confidence to participate, contribute to their communities, and pursue new opportunities—including opportunities to earn a livelihood."),
                     aside="Skills can be used again.\nKnowledge can be shared.\nIdeas can be adapted and passed on.")
        elif s["type"] == "notes_feed":
            s["hidden"] = True  # Not present in the supplied PDF; preserved for later use.
        elif s["type"] == "contact_invite":
            d.update(eyebrow="Learn. Contribute. Take Part.", heading="")
    sections.insert(1, learning)
    return content


async def main():
    page = await db.pages.find_one({"key": KEY}, {"_id": 0})
    if not page:
        raise RuntimeError("Workshops page not found")
    if page.get("design_migration") == VERSION:
        print("Already applied; no changes")
        return
    stamp = now()
    for field in ("published", "draft"):
        await db.revisions.insert_one({"id": new_id(), "entity_type": "page", "entity_id": KEY,
                                       "content": copy.deepcopy(page[field]), "action": f"before Workshops reference ({field})",
                                       "by": "approved-content-migration", "note": VERSION, "created_at": stamp})
    await db.pages.update_one({"key": KEY}, {"$set": {
        "published": transform(page["published"]), "draft": transform(page["draft"]),
        "design_migration": VERSION, "updated_at": stamp, "published_at": stamp,
    }})
    print("Applied Workshops PDF/reference with four editable image placeholders; other pages unchanged")


if __name__ == "__main__":
    asyncio.run(main())