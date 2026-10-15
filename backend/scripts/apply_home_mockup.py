"""One-off: make the Home page match the client 'USP_Homepage_Revised' mockup.
- Hide the wide image block (index 3) — mockup has no big image there.
- Give the Field Notes feed two curated cards (dolls + basket makers).
Idempotent. Updates both draft and published, keeps it live.
"""
import os, asyncio, motor.motor_asyncio
from dotenv import load_dotenv
load_dotenv()

CARDS = [
    {
        "eyebrow": "Rakhigarhi / Heritage",
        "title": "What Was Already There.",
        "text": "Objects, memories and traces of everyday life encountered through the work.",
        "link_label": "Read the Story",
        "href": "/field-notes",
        "crop": "4/3",
        "image": {"media_id": "07f3512b576f4ea19497a610d33a9fc9", "caption": ""},
    },
    {
        "eyebrow": "Rakhigarhi / Craft",
        "title": "The OG Basket Makers.",
        "text": "Two experienced basket makers whose knowledge and skill inspire a new generation.",
        "link_label": "Read the Story",
        "href": "/field-notes",
        "crop": "4/3",
        "image": {"media_id": "6fc82b55f714459f9499182413231bbb", "caption": ""},
    },
]


def patch(sections):
    for s in sections:
        if s.get("type") == "image":
            s["hidden"] = True
        if s.get("type") == "notes_feed":
            s["hidden"] = False
            d = s.setdefault("data", {})
            d["cards"] = CARDS
            d["more_label"] = "Explore Field Notes"
            d["more_href"] = "/field-notes"
    return sections


async def main():
    c = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    p = await c.pages.find_one({"key": "home"})
    for sub in ("draft", "published"):
        if p.get(sub) and p[sub].get("sections"):
            p[sub]["sections"] = patch(p[sub]["sections"])
    await c.pages.update_one(
        {"key": "home"},
        {"$set": {"draft": p["draft"], "published": p["published"], "has_unpublished_changes": False}},
    )
    print("home updated: image block hidden, field-notes cards set")


asyncio.run(main())
