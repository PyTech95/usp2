import os
from core import db, now, new_id, hash_password, verify_password, PAGE_PATHS

DRAFT = "Draft placeholder — awaiting approved client copy."

DEFAULT_THEME = {
    "colors": {"background": "#F9F9F9", "surface": "#EDEAE7", "text": "#2B2B2B", "green": "#222222", "terracotta": "#4F4A45", "ochre": "#8C847C"},
    "fonts": {"heading": "Public Sans", "body": "Public Sans"},
    "spacing": "comfortable", "button_style": "square", "base_size": 18,
}

MAIN_MENU = [
    {"id": "m-home", "label": "Home", "href": "/", "required": True, "children": []},
    {"id": "m-about", "label": "About", "href": "/about", "required": True, "children": []},
    {"id": "m-work", "label": "Our Work", "href": "/our-work", "required": True, "children": [
        {"id": "m-rak", "label": "Rakhigarhi", "href": "/our-work/rakhigarhi", "required": True},
        {"id": "m-the", "label": "Theatre", "href": "/our-work/theatre", "required": True},
        {"id": "m-cra", "label": "Craft & Livelihood", "href": "/our-work/craft-livelihood", "required": True},
        {"id": "m-wor", "label": "Workshops & Learning", "href": "/our-work/workshops-learning", "required": True},
    ]},
    {"id": "m-notes", "label": "Field Notes", "href": "/field-notes", "required": True, "children": []},
    {"id": "m-connect", "label": "Connect", "href": "/connect", "required": True, "children": []},
]

CHECKLIST = [
    "Final colour chart supplied and applied", "Organisation statement approved", "Home page copy approved",
    "About: story, purpose, approach approved", "Team names, biographies and portraits approved",
    "Our Work overview copy approved", "Rakhigarhi copy and sources approved", "Theatre copy approved",
    "Craft & Livelihood classifications confirmed", "Workshops & Learning copy approved",
    "Verified contact details supplied", "Approved social links supplied", "Original photographs uploaded",
    "Photograph permissions recorded", "Process for photographs that may include minors documented",
    "Home hero photograph selected", "Font licences confirmed", "Enquiry email notification provider approved",
    "Search indexing enabled (only after launch approval)", "Public deployment and domain change approved",
]

REGISTER = [
    ("Women weaving under the roof", "Use Original4.jpeg. New8.png is an AI reference only — never public.", "Preserve all eight women including far right; retain roof and both pillars; clean peripheral litter; balance exposure. Candidate for Home or Craft & Livelihood (unconfirmed)."),
    ("Older woman weaving green-and-yellow basket", "Use Original.jpeg. New1.png is an AI reference only.", "Retain softness and expression; background-only adjustments; keep hands, basket, walking stick."),
    ("Woman with two cloth dolls", "Use unmarked original. Version with red arrows = private edit instructions.", "Preserve woman and both dolls; only indicated peripheral distractions via crop/local cleanup."),
    ("Basket collection", "Screenshot source — borders to be removed in display derivative.", "Preserve colours, quantities, irregularities. Low resolution: smaller image module only."),
    ("Blue basket", "Screenshot source — borders to be removed in display derivative.", "Preserve actual colours and irregularities."),
    ("Green basket with mangoes", "Two supplied versions differ in appearance and arrangement — provenance unresolved.", "Client must designate the original. For Craft & Livelihood."),
    ("Reading circle", "Original (to confirm).", "Event title, participants, date and Theatre vs Workshops assignment unconfirmed."),
    ("Papier-mâché bowls, small figures, tall object", "Original (to confirm).", "Group under Papier-mâché when approved. No invented material specs or product names."),
    ("Textile wall hanging", "Original (to confirm).", "Preserve full design, wear, proportions. Large portrait module."),
    ("Carved wooden door", "Two identical uploads — keep one canonical media record; archive both sources.", "Preserve full design and wear. Large portrait module."),
    ("Overgrown brick house", "OWNER PERMISSION REQUIRED — keep Restricted.", "Not public, not in sitemap or social previews. Not a restoration project, USP property, venue or archaeological structure."),
    ("Unmapped WhatsApp placement comments", "Not tied unambiguously to a photograph.", "Record mapping once clarified; do not guess."),
]


def sec(type_, **data):
    return {"id": new_id(), "type": type_, "hidden": False, "data": data}


def img(caption=""):
    return {"media_id": "", "caption": caption}


def work_items():
    return [
        {"title": "Rakhigarhi", "text": DRAFT, "href": "/our-work/rakhigarhi", "image": img()},
        {"title": "Theatre", "text": DRAFT, "href": "/our-work/theatre", "image": img()},
        {"title": "Craft & Livelihood", "text": DRAFT, "href": "/our-work/craft-livelihood", "image": img()},
        {"title": "Workshops & Learning", "text": DRAFT, "href": "/our-work/workshops-learning", "image": img()},
    ]


def p(t=DRAFT):
    return f"<p>{t}</p>"


def page_sections():
    return {
        "home": ("Home", [
            sec("hero", eyebrow="USP India", heading="Urban Suburban Perspectives", intro=DRAFT + " (Short approved statement about USP India.)", image=img(), buttons=[{"label": "Explore Our Work", "href": "/our-work"}, {"label": "Read Field Notes", "href": "/field-notes"}]),
            sec("text", heading="Introduction", body_html=p()),
            sec("related_work", heading="Our Work", intro="", items=work_items()),
            sec("image_text", heading="People and process", body_html=p(DRAFT + " A deeper story combining people and making process will appear here."), image=img(), image_side="left"),
            sec("notes_feed", heading="Recent Field Notes", count=3, category=""),
            sec("contact_invite", heading="Connect with Us", text=DRAFT, button_label="Connect with Us", href="/connect"),
        ]),
        "about": ("About", [
            sec("hero", eyebrow="About", heading="About USP India", intro=DRAFT, image=img(), buttons=[]),
            sec("text", heading="Our story", body_html=p()),
            sec("text", heading="Purpose", body_html=p()),
            sec("text", heading="Approach", body_html=p()),
            sec("text", heading="Team", body_html=p("Team names, biographies, portraits and affiliations will appear here once approved.")),
            sec("text", heading="Participation and collaboration", body_html=p()),
            sec("contact_invite", heading="Connect with Us", text=DRAFT, button_label="Connect with Us", href="/connect"),
        ]),
        "our-work": ("Our Work", [
            sec("hero", eyebrow="Our Work", heading="Our Work", intro=DRAFT, image=img(), buttons=[]),
            sec("text", heading="How the four areas relate", body_html=p()),
            sec("related_work", heading="Areas of work", intro="", items=work_items()),
        ]),
        "rakhigarhi": ("Rakhigarhi", [
            sec("hero", eyebrow="Our Work", heading="Rakhigarhi", intro=DRAFT, image=img(), buttons=[]),
            sec("text", heading="Place and community", body_html=p()),
            sec("text", heading="Historical context", body_html=p(DRAFT + " Researched historical context with cited sources, kept separate from USP's own activities and from personal recollections.")),
            sec("text", heading="USP's activities", body_html=p()),
            sec("text", heading="Local accounts", body_html=p(DRAFT + " Personal recollections, attributed with consent.")),
            sec("notes_feed", heading="Related Field Notes", count=3, category="Rakhigarhi"),
        ]),
        "theatre": ("Theatre", [
            sec("hero", eyebrow="Our Work", heading="Theatre", intro=DRAFT, image=img(), buttons=[]),
            sec("text", heading="Approach", body_html=p()),
            sec("text", heading="Readings, rehearsals and performances", body_html=p()),
            sec("notes_feed", heading="Related Field Notes", count=3, category="Theatre"),
        ]),
        "craft-livelihood": ("Craft & Livelihood", [
            sec("hero", eyebrow="Our Work", heading="Craft & Livelihood", intro=DRAFT, image=img(), buttons=[]),
            sec("text", heading="Makers and their work", body_html=p()),
            sec("image_text", heading="Baskets", body_html=p(DRAFT + " (Classification to be confirmed.)"), image=img(), image_side="left"),
            sec("image_text", heading="Cloth dolls", body_html=p(DRAFT + " (Classification to be confirmed.)"), image=img(), image_side="right"),
            sec("image_text", heading="Papier-mâché", body_html=p(DRAFT + " (Classification to be confirmed.)"), image=img(), image_side="left"),
            sec("image_text", heading="Textiles", body_html=p(DRAFT + " (Classification to be confirmed.)"), image=img(), image_side="right"),
            sec("contact_invite", heading="Craft enquiries", text="Questions about craft and makers can be sent through Connect.", button_label="Send a craft enquiry", href="/connect?topic=Craft"),
        ]),
        "workshops-learning": ("Workshops & Learning", [
            sec("hero", eyebrow="Our Work", heading="Workshops & Learning", intro=DRAFT, image=img(), buttons=[]),
            sec("text", heading="Overview", body_html=p()),
            sec("text", heading="Past workshops", body_html=p(DRAFT + " Documented workshop stories will be listed here.")),
            sec("text", heading="Upcoming", body_html=p("No upcoming activities have been announced.")),
            sec("notes_feed", heading="Workshop reflections", count=3, category="Workshops & Learning"),
        ]),
        "field-notes": ("Field Notes", [
            sec("hero", eyebrow="Field Notes", heading="Field Notes", intro="Articles, photo essays, interviews, workshop reflections and resources from USP India.", image=img(), buttons=[]),
        ]),
        "connect": ("Connect", [
            sec("hero", eyebrow="Connect", heading="Connect with Us", intro="Use the form below for general questions, collaboration, craft, theatre, or workshops and learning.", image=img(), buttons=[]),
            sec("contact_form", heading="Send a message", intro=""),
            sec("text", heading="Contact details", body_html=p("Verified contact details will be shown here once supplied.")),
        ]),
    }


DESCRIPTIONS = {
    "home": "USP India (Urban Suburban Perspectives) — community, culture, craft, heritage, theatre and learning.",
    "about": "About USP India — Urban Suburban Perspectives: story, purpose, approach and team.",
    "our-work": "USP India's four areas of work: Rakhigarhi, Theatre, Craft & Livelihood, and Workshops & Learning.",
    "rakhigarhi": "USP India's place-and-community work in Rakhigarhi.",
    "theatre": "Theatre at USP India: readings, rehearsals, performances and workshops.",
    "craft-livelihood": "Craft & Livelihood at USP India: makers, making processes and objects.",
    "workshops-learning": "Workshops & Learning at USP India: documented workshops and resources.",
    "field-notes": "Field Notes from USP India: articles, photo essays, interviews, workshop reflections and resources.",
    "connect": "Contact USP India — Urban Suburban Perspectives.",
}


def default_settings():
    return {
        "key": "site", "site_name": "USP India", "full_name": "Urban Suburban Perspectives", "tagline": "",
        "logo_media_id": "", "favicon_media_id": "", "theme": DEFAULT_THEME,
        "footer_text": "USP India — Urban Suburban Perspectives.",
        "privacy_html": "<p>Messages sent through Connect are stored privately and used only to respond to you. Draft privacy notice — awaiting approved text.</p>",
        "contact": {"email": "", "phone": "", "address": ""}, "social": [],
        "menus": {"main": MAIN_MENU, "footer": []},
        "preview_banner": False, "indexing_enabled": False,
        "default_share_media_id": "",
        "checklist": [{"id": new_id(), "label": c, "done": False} for c in CHECKLIST],
        "taxonomy": {"authors": [{"name": "USP India editorial team (placeholder)", "bio": ""}],
                     "categories": ["Rakhigarhi", "Theatre", "Craft & Livelihood", "Workshops & Learning", "Resources"], "tags": []},
        "email_notifications": {"status": "not_configured", "detail": "No email provider approved yet. Enquiries are stored in the admin only."},
        "updated_at": now(),
    }


SAMPLE_NOTE_BODY = """<p>This entry is a template preview that shows how a Field Note is laid out. It is not a fieldwork story and should be unpublished or replaced once real notes are approved.</p>
<h2>What a Field Note can hold</h2>
<p>One content model supports articles, photo essays, interviews, workshop reflections and resource posts. Each note can carry a standfirst, an identifiable author, published and updated dates, a cover photograph, captions and credits, references and downloadable resources.</p>
<h2>Keeping sources clear</h2>
<p>Observations, quotations, organisational statements and historical references should be written as separate passages, with sources listed under References.</p>"""


async def seed():
    await db.users.create_index("email", unique=True)
    await db.users.create_index("id", unique=True)
    await db.pages.create_index("key", unique=True)
    await db.notes.create_index("slug", unique=True)
    await db.media.create_index("id", unique=True)
    await db.redirects.create_index("from_path", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.tokens.create_index("expires_at_dt", expireAfterSeconds=0)

    email, pw = os.environ["ADMIN_EMAIL"].lower(), os.environ["ADMIN_PASSWORD"]
    # Bootstrap a new installation only. Republish must NEVER reset a live
    # account's password/role or create a second owner from changed env values.
    if await db.users.find_one({}, {"_id": 0, "id": 1}) is None:
        await db.users.update_one({"email": email}, {"$setOnInsert": {"id": new_id(), "email": email, "name": "Owner", "role": "owner", "active": True, "password_hash": hash_password(pw), "created_at": now()}}, upsert=True)

    new_site = await db.settings.find_one({"key": "site"}) is None
    if new_site:
        await db.settings.insert_one(default_settings())

    for key, (title, sections) in page_sections().items():
        if await db.pages.find_one({"key": key}):
            continue
        content = {"title": title, "sections": sections, "seo": {"title": "", "description": DESCRIPTIONS[key], "canonical": "", "noindex": False, "share_media_id": ""}}
        await db.pages.insert_one({"id": new_id(), "key": key, "path": PAGE_PATHS[key], "required": True, "draft": content, "published": content,
                                   "status": "published", "updated_at": now(), "published_at": now(), "has_unpublished_changes": False})

    if new_site and await db.register.count_documents({}) == 0:
        await db.register.insert_many([{"id": new_id(), "subject": s, "source": src, "direction": d, "status": "awaiting upload",
                                        "permission": "restricted" if "OWNER" in src else "pending", "notes": "", "media_ids": []} for s, src, d in REGISTER])

    if new_site and await db.notes.count_documents({}) == 0:
        c = {"title": "How Field Notes will work (template preview)", "slug": "how-field-notes-will-work",
             "standfirst": "A layout sample for the editorial team. Not a fieldwork story.", "kind": "resource",
             "author": "USP India editorial team (placeholder)", "category": "Resources", "tags": ["template"],
             "body_html": SAMPLE_NOTE_BODY, "cover": {"media_id": "", "caption": ""}, "credits": "", "references": [], "downloads": [], "related": [],
             "seo": {"title": "", "description": "Template preview showing how USP India Field Notes are structured.", "canonical": "", "noindex": True, "share_media_id": ""}}
        await db.notes.insert_one({"id": new_id(), "slug": c["slug"], "draft": c, "published": c, "status": "published", "created_by": "system",
                                   "created_at": now(), "updated_at": now(), "published_at": now(), "has_unpublished_changes": False})
