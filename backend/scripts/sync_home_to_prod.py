"""Push the preview Home page + menus + tagline to PRODUCTION via its admin HTTP API.
This performs the same operations the admin UI does (draft save -> publish, update menus/settings),
so production (which uses a separate DB) matches the designed homepage.
Run: python3 scripts/sync_home_to_prod.py
"""
import os, sys, asyncio, requests, motor.motor_asyncio
from dotenv import load_dotenv
load_dotenv()

PROD = os.environ.get("PROD_URL", "https://usp-india-cms.emergent.host").rstrip("/")
EMAIL = os.environ.get("PROD_ADMIN_EMAIL", "intrinsicamerica.web@gmail.com")
PASSWORD = os.environ.get("PROD_ADMIN_PASSWORD", "Usp-NArl-bV_MfteEKPs")


async def read_preview():
    c = motor.motor_asyncio.AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    page = await c.pages.find_one({"key": "home"}, {"_id": 0})
    s = await c.settings.find_one({"key": "site"}, {"_id": 0}) or await c.settings.find_one({}, {"_id": 0})
    draft = page["draft"]
    return (
        {"title": draft.get("title") or "Home", "sections": draft["sections"], "seo": draft.get("seo") or {}},
        s.get("menus") or {},
        s.get("tagline") or "",
    )


def main():
    draft, menus, tagline = asyncio.get_event_loop().run_until_complete(read_preview())
    print(f"preview: {len(draft['sections'])} sections | menus main={len(menus.get('main',[]))} footer={len(menus.get('footer',[]))} | tagline={tagline!r}")

    sess = requests.Session()
    r = sess.post(f"{PROD}/api/auth/login", json={"email": EMAIL, "password": PASSWORD}, timeout=30)
    print("login:", r.status_code)
    if r.status_code != 200:
        print(r.text[:300]); sys.exit(1)
    token = sess.cookies.get("access_token")
    if not token:
        try:
            token = r.json().get("access_token") or r.json().get("token")
        except Exception:
            token = None
    if not token:
        print("No access_token from login; cookies:", sess.cookies.get_dict()); sys.exit(1)
    # Bearer only, no cookies -> CSRF middleware skipped
    H = {"Authorization": f"Bearer {token}"}

    r = requests.put(f"{PROD}/api/admin/pages/home/draft", json=draft, headers=H, timeout=60)
    print("save draft:", r.status_code, r.text[:200] if r.status_code >= 400 else "")
    r = requests.post(f"{PROD}/api/admin/pages/home/publish", headers=H, timeout=60)
    print("publish:", r.status_code, r.text[:200] if r.status_code >= 400 else "")
    r = requests.put(f"{PROD}/api/admin/menus", json={"main": menus.get("main", []), "footer": menus.get("footer", [])}, headers=H, timeout=30)
    print("menus:", r.status_code, r.text[:200] if r.status_code >= 400 else "")
    r = requests.put(f"{PROD}/api/admin/settings", json={"tagline": tagline}, headers=H, timeout=30)
    print("settings tagline:", r.status_code, r.text[:200] if r.status_code >= 400 else "")


if __name__ == "__main__":
    main()
