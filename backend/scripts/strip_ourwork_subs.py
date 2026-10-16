"""One-off: remove third-level sub-items under the four 'Our Work' menu items.
The Our Work dropdown should show exactly 4 items (Rakhigarhi, Theatre,
Craft & Livelihood, Workshops & Learning) with no nested sub-menu, matching
the approved menu example. Idempotent."""
import asyncio
from core import db, now


async def main():
    s = await db.settings.find_one({"key": "site"}, {"_id": 0, "menus": 1})
    main_menu = s["menus"]["main"]
    changed = 0
    for item in main_menu:
        if item.get("href") == "/our-work":
            for child in item.get("children", []):
                if child.get("children"):
                    child["children"] = []
                    changed += 1
    await db.settings.update_one(
        {"key": "site"},
        {"$set": {"menus.main": main_menu, "updated_at": now()}},
    )
    print(f"Cleared sub-items under {changed} Our Work children.")
    # verify
    s2 = await db.settings.find_one({"key": "site"}, {"_id": 0, "menus": 1})
    work = next(i for i in s2["menus"]["main"] if i.get("href") == "/our-work")
    for c in work["children"]:
        print(f"  {c['label']}: {len(c.get('children', []))} sub-items")


if __name__ == "__main__":
    asyncio.run(main())
