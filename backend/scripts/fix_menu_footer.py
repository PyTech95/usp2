"""Move Blog from main nav to footer; rename About -> Who We Are; set footer tagline."""
import os, asyncio, motor.motor_asyncio
from dotenv import load_dotenv
load_dotenv()


async def main():
    c = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    s = await c.settings.find_one({}) or {}
    menus = s.get("menus") or {}
    main = menus.get("main") or []
    blog = next((m for m in main if m.get("id") == "m-blog" or m.get("href") == "/blog"), None)
    new_main = [m for m in main if not (m.get("id") == "m-blog" or m.get("href") == "/blog")]
    for m in new_main:
        if m.get("id") == "m-about" or m.get("href") == "/about":
            m["label"] = "Who We Are"
    footer = menus.get("footer") or []
    if not any(f.get("href") == "/blog" for f in footer):
        footer = footer + [{"id": "m-blog", "label": "Blog", "href": "/blog"}]
    menus["main"] = new_main
    menus["footer"] = footer
    await c.settings.update_one(
        {"_id": s["_id"]},
        {"$set": {"menus": menus, "tagline": "Heritage, Art and Culture"}},
    )
    print("main:", [(m["label"], m["href"]) for m in new_main])
    print("footer:", [(f["label"], f["href"]) for f in footer])
    print("tagline set: Heritage, Art and Culture")


asyncio.run(main())
