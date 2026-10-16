import os
import json
from html import escape as E
from urllib.parse import urlsplit, parse_qs, urlencode
from core import db, SITE_URL, PATH_TO_PAGE
from routes_public import get_site, public_page, public_note, list_notes

SCRIPTS = [s for s in os.environ.get("SSR_SCRIPT_TAGS", "").split(",") if s]
KIND_LABEL = {"article": "Article", "photo_essay": "Photo essay", "interview": "Interview", "workshop_reflection": "Workshop reflection", "resource": "Resource"}


def a(o, k, d=""):
    return (o or {}).get(k) or d


def picture(m, cls="", eager=False, sizes="(min-width: 1024px) 60vw, 100vw"):
    if not m:
        return ""
    srcset = ", ".join(f"{s['url']} {s['w']}w" for s in m["srcs"])
    load = 'fetchpriority="high"' if eager else 'loading="lazy" decoding="async"'
    return f'<img src="{E(m["src"])}" srcset="{E(srcset)}" sizes="{sizes}" width="{m["width"]}" height="{m["height"]}" alt="{E(m["alt"])}" class="{cls}" {load}>'


def figure(ref, eager=False):
    m = (ref or {}).get("media")
    if not m:
        return ""
    cap = a(ref, "caption") or m.get("caption")
    credit = m.get("credit")
    fc = f'<figcaption>{E(cap)}{(" — " + E(credit)) if credit else ""}</figcaption>' if cap or credit else ""
    orig = f'<p><a href="{E(m["original"]["src"])}">View the original photograph</a>{(" — edit: " + E(m["edit_note"])) if m.get("edit_note") else ""}</p>' if m.get("original") else ""
    return f"<figure>{picture(m, eager=eager)}{fc}{orig}</figure>"


def buttons(items):
    return "".join(f'<a class="btn" href="{E(b["href"])}">{E(b["label"])}</a>' for b in items or [] if b.get("label"))


def note_list(items):
    if not items:
        return "<p>No Field Notes have been published yet.</p>"
    lis = "".join(f'<li><article><h3><a href="/field-notes/{E(n["slug"])}">{E(n["title"])}</a></h3><p>{E(n.get("standfirst") or "")}</p>'
                  f'<p><small>{E(KIND_LABEL.get(n.get("kind"), ""))} · {E(n.get("author") or "")} · <time datetime="{E((n.get("published_at") or "")[:10])}">{E((n.get("published_at") or "")[:10])}</time></small></p></article></li>' for n in items)
    return f"<ul>{lis}</ul>"


def block(s, first):
    d, t = s["data"], s["type"]
    h = "h1" if first and t == "hero" else "h2"
    head = (f'<p>{E(a(d, "eyebrow"))}</p>' if a(d, "eyebrow") and t != "hero" else "") + (f'<{h}>{E(a(d, "heading"))}</{h}>' if a(d, "heading") else "") + (f'<p>{E(a(d, "subheading"))}</p>' if a(d, "subheading") else "")
    html = _block(s, d, t, h, head)
    return f'<div id="{E(d["anchor"])}">{html}</div>' if a(d, "anchor") and html else html


def _block(s, d, t, h, head):
    if t == "hero":
        intro = "".join(f"<p>{E(x)}</p>" for x in a(d, "intro").split("\n\n") if x.strip())
        if d.get("intro_heading"):
            intro = f'<p>{E(d["intro_heading"])}</p>' + intro
        return f'<section><p>{E(a(d, "eyebrow"))}</p>{head}{intro}{buttons(d.get("buttons"))}{figure(d.get("image"), eager=True)}</section>'
    if t == "text":
        if d.get("layout") == "about-approach":
            values = "".join(f'<li>{E(a(value, "text"))}</li>' for value in d.get("values", []))
            return f'<section>{head}{a(d, "body_html")}<aside aria-label="Our principles"><ul>{values}</ul></aside></section>'
        if d.get("layout") == "theatre-production":
            link = buttons([{"href": d["link_href"], "label": d["link_label"]}]) if d.get("link_href") else ""
            return f'<section>{head}{a(d, "body_html")}{link}<p>{E(a(d, "question"))}</p>{a(d, "aside_html")}</section>'
        return f'<section>{head}{a(d, "body_html")}{("<p>" + E(d["aside"]) + "</p>") if a(d, "aside") else ""}</section>'
    if t == "image_text":
        if d.get("layout") == "theatre-archive":
            link = buttons([{"href": d["link_href"], "label": d["link_label"]}]) if d.get("link_href") else ""
            return f'<section>{head}{a(d, "body_html")}{figure(d.get("image"))}{link}</section>'
        return f'<section>{head}{a(d, "body_html")}{figure(d.get("image"))}</section>'
    if t == "image":
        return f"<section>{head}{figure(d.get('image'))}{a(d, 'body_html')}</section>"
    if t == "gallery":
        if d.get("layout") == "about-team":
            people = []
            for i, person in enumerate(d.get("items", [])):
                image = person.get("image") or {}
                portrait = figure(image) or f'<p>{E(a(image, "placeholder_label", "Photograph"))}</p>'
                people.append(f'<article data-testid="about-team-member-{i}">{portrait}<h3>{E(a(person, "name"))}</h3><p>{E(a(person, "intro"))}</p></article>')
            return f'<section>{head}{"".join(people)}</section>'
        return f'<section>{head}{"".join(figure(i.get("image")) for i in d.get("items", []))}</section>'
    if t == "quote" and d.get("approved"):
        return f'<section><blockquote><p>{E(a(d, "quote"))}</p><footer>{E(a(d, "attribution"))}</footer></blockquote></section>'
    if t == "video" and a(d, "url"):
        tr = f'<details><summary>Transcript</summary>{a(d, "transcript_html")}</details>' if a(d, "transcript_html") else ""
        return f'<section>{head}<p><a href="{E(d["url"])}">Watch the video{(": " + E(a(d, "caption"))) if a(d, "caption") else ""}</a></p>{tr}</section>'
    if t == "related_work":
        items = "".join(f'<li><a href="{E(i["href"])}">{E(i["title"])}{(": " + E(i["subtitle"])) if a(i, "subtitle") else ""}</a> — {E(a(i, "text"))}{figure(i.get("image"))}</li>' for i in d.get("items", []))
        return f'<section>{head}<p>{E(a(d, "intro"))}</p><ul>{items}</ul></section>'
    if t == "notes_feed":
        return f'<section>{head}{("<p>" + E(d["intro"]) + "</p>") if a(d, "intro") else ""}{note_list(s.get("notes"))}<p><a href="/field-notes">All Field Notes</a></p></section>'
    if t == "download":
        items = "".join(f'<li><a href="/api/media/{E(i["media"]["id"])}/file">{E(a(i, "label", "Download"))}</a></li>' for i in d.get("items", []) if i.get("media"))
        return f"<section>{head}<ul>{items}</ul></section>" if items else ""
    if t == "contact_invite":
        btns = [b for b in d.get("buttons") or [] if b.get("label")]
        links = buttons(btns) if btns else f'<a class="btn" href="{E(a(d, "href", "/connect"))}">{E(a(d, "button_label", "Connect with Us"))}</a>'
        return f'<section>{head}<p>{E(a(d, "text"))}</p>{links}</section>'
    if t == "contact_form":
        return f'<section>{head}<p>{E(a(d, "intro"))}</p><noscript><p>The enquiry form needs JavaScript to send. Please enable JavaScript.</p></noscript></section>'
    return ""


def sub_menu(c):
    links = "".join(f'<li><a href="{E(g["href"])}">{E(g["label"])}</a></li>' for g in c.get("children") or [])
    return f"<ul>{links}</ul>" if links else ""


def menu_html(menu):
    out = ""
    for i in menu:
        kids = "".join(f'<li><a href="{E(c["href"])}">{E(c["label"])}</a>{sub_menu(c)}</li>' for c in i.get("children", []))
        out += f'<li><a href="{E(i["href"])}">{E(i["label"])}</a>{f"<ul>{kids}</ul>" if kids else ""}</li>'
    return out


def doc(site, title, desc, canonical, body, jsonld, noindex=False, og_image=None, og_type="website"):
    th = site["theme"]
    c = th["colors"]
    robots = "noindex, nofollow" if noindex or not site.get("indexing_enabled") else "index, follow"
    css = ";".join(f"--c-{k}:{v}" for k, v in c.items())
    og_img = f'<meta property="og:image" content="{SITE_URL}{og_image["src"]}"><meta property="og:image:alt" content="{E(og_image["alt"])}">' if og_image else ""
    fav = f'<link rel="icon" href="{site["favicon"]["src"]}">' if site.get("favicon") else ""
    scripts = "".join(f'<script defer src="{s}"></script>' for s in SCRIPTS)
    footer = f'<footer><p>{E(site.get("footer_text") or "")}</p><details><summary>Privacy</summary>{site.get("privacy_html") or ""}</details></footer>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title><meta name="description" content="{E(desc)}"><link rel="canonical" href="{E(canonical)}"><meta name="robots" content="{robots}">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{E(canonical)}"><meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{E(site["site_name"])}">{og_img}
<meta name="twitter:card" content="{'summary_large_image' if og_image else 'summary'}">{fav}
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@100;200;300;400;500;600;700&family=Cormorant:ital,wght@0,400;0,500;0,600;1,400&family=Literata:ital,opsz,wght@0,7..72,300;0,7..72,400;0,7..72,500;0,7..72,600;1,7..72,400&family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;1,400&display=swap" rel="stylesheet">
<style>:root{{{css}}}body{{background:var(--c-background);color:var(--c-text);margin:0}}.ssr{{font-family:'Public Sans',sans-serif;font-weight:300;font-size:18px;line-height:1.6;max-width:1240px;margin:0 auto;padding:0 24px}}.ssr h1,.ssr h2,.ssr h3{{font-weight:300}}.ssr img{{max-width:100%;height:auto}}.ssr a{{color:var(--c-green)}}</style>
<script type="application/ld+json">{json.dumps(jsonld)}</script></head>
<body><div id="root"><div class="ssr"><a href="#main">Skip to content</a><header><p><a href="/">{E(site["site_name"])} — {E(site.get("full_name") or "")}</a></p><nav aria-label="Main"><ul>{menu_html(site["menus"]["main"])}</ul></nav></header>
<main id="main">{body}</main>{footer}</div></div>{scripts}</body></html>"""


def org_ld(site):
    o = {"@type": "Organization", "@id": f"{SITE_URL}/#org", "name": site["site_name"], "alternateName": site.get("full_name"), "url": SITE_URL + "/"}
    if site.get("logo"):
        o["logo"] = SITE_URL + site["logo"]["src"]
    links = [s["url"] for s in site.get("social") or []]
    if links:
        o["sameAs"] = links
    return o


def crumbs(items):
    return {"@type": "BreadcrumbList", "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": SITE_URL + p} for i, (n, p) in enumerate(items)]}


def crumb_trail(path, title):
    trail = [("Home", "/")]
    if path.startswith("/our-work/"):
        trail.append(("Our Work", "/our-work"))
    if path.startswith("/field-notes/"):
        trail.append(("Field Notes", "/field-notes"))
    if path != "/":
        trail.append((title, path))
    return trail


def crumb_html(trail):
    if len(trail) < 2:
        return ""
    return '<nav aria-label="Breadcrumb"><ol>' + "".join(f'<li><a href="{p}">{E(n)}</a></li>' for n, p in trail) + "</ol></nav>"


async def share_image(seo, site, fallback=None):
    from core import resolve_media_tree
    if seo.get("share_media_id"):
        r = await resolve_media_tree({"media_id": seo["share_media_id"]})
        if r.get("media"):
            return r["media"]
    return fallback or None


async def not_found(site):
    body = '<h1>Page not found</h1><p>This address does not exist on the USP India website.</p><p><a href="/">Go to Home</a> · <a href="/field-notes">Read Field Notes</a></p>'
    return 404, doc(site, f"Page not found — {site['site_name']}", "Page not found.", SITE_URL + "/404", body, {"@context": "https://schema.org", "@graph": [org_ld(site)]}, noindex=True), {}


async def render(raw_path):
    parts = urlsplit(raw_path)
    path = parts.path.rstrip("/") or "/"
    qs = {k: v[0] for k, v in parse_qs(parts.query).items()}
    site = await get_site()
    r = await db.redirects.find_one({"from_path": path}, {"_id": 0})
    if r:
        return 301, "", {"Location": r["to_path"]}
    if path != (parts.path or "/"):
        return 301, "", {"Location": path + (("?" + parts.query) if parts.query else "")}
    key = PATH_TO_PAGE.get(path)
    if key:
        p = await public_page(key)
        if not p:
            return await not_found(site)
        c = p["content"]
        seo = c["seo"]
        title = seo.get("title") or (f"{c['title']} — {site['site_name']}" if key != "home" else f"{site['site_name']} — {site.get('full_name')}")
        canonical = seo.get("canonical") or (SITE_URL + (path if path != "/" else "/"))
        trail = crumb_trail(path, c["title"])
        body = crumb_html(trail) + "".join(block(s, i == 0) for i, s in enumerate(c["sections"]))
        hero_img = next((s["data"]["image"]["media"] for s in c["sections"] if s["type"] == "hero" and (s["data"].get("image") or {}).get("media")), None)
        graph = [org_ld(site)]
        if key == "home":
            graph.append({"@type": "WebSite", "@id": f"{SITE_URL}/#website", "url": SITE_URL + "/", "name": site["site_name"], "publisher": {"@id": f"{SITE_URL}/#org"}})
        ptype = {"about": "AboutPage", "connect": "ContactPage", "field-notes": "CollectionPage"}.get(key, "WebPage")
        graph.append({"@type": ptype, "url": canonical, "name": title, "description": seo.get("description", ""), "dateModified": p["updated_at"], "isPartOf": {"@id": f"{SITE_URL}/#website"}})
        if len(trail) > 1:
            graph.append(crumbs(trail))
        if key == "field-notes":
            listing = await list_notes(qs.get("q", ""), qs.get("category", ""), qs.get("tag", ""), int(qs.get("page", "1") or 1) if qs.get("page", "1").isdigit() else 1)
            body += "<section><h2>All Field Notes</h2>" + note_list(listing["items"])
            nav = []
            for n in range(1, listing["pages"] + 1):
                q = urlencode({k: v for k, v in {**qs, "page": n}.items() if v})
                nav.append(f'<a href="/field-notes?{q}">Page {n}</a>')
            body += f'<nav aria-label="Pagination">{" ".join(nav)}</nav></section>'
            if qs.get("q") or qs.get("category") or qs.get("tag"):
                seo = {**seo, "noindex": True}
        og = await share_image(seo, site, hero_img or site.get("default_share"))
        return 200, doc(site, title, seo.get("description", ""), canonical, body, {"@context": "https://schema.org", "@graph": graph}, seo.get("noindex"), og), {}
    if path.startswith("/field-notes/") and path.count("/") == 2:
        slug = path.split("/")[2]
        n = await public_note(slug)
        if not n:
            return await not_found(site)
        note = n["note"]
        seo = note["seo"]
        title = seo.get("title") or f"{note['title']} — {site['site_name']}"
        canonical = seo.get("canonical") or f"{SITE_URL}/field-notes/{slug}"
        trail = crumb_trail(path, note["title"])
        cover = (note.get("cover") or {}).get("media")
        refs = "".join(f"<li>{E(a(r, 'text'))}{(' — <a href=' + chr(34) + E(r['url']) + chr(34) + '>source</a>') if a(r, 'url') else ''}</li>" for r in note.get("references", []))
        dls = "".join(f'<li><a href="/api/media/{d["media"]["id"]}/file">{E(a(d, "label", "Download"))}</a></li>' for d in note.get("downloads", []))
        body = (crumb_html(trail) + f'<article><header><p>{E(KIND_LABEL.get(note.get("kind"), ""))} · {E(note.get("category") or "")}</p><h1>{E(note["title"])}</h1>'
                f'<p>{E(note.get("standfirst") or "")}</p><p>By {E(note.get("author") or "")} · Published <time datetime="{n["published_at"][:10]}">{n["published_at"][:10]}</time>'
                f' · Updated <time datetime="{n["updated_at"][:10]}">{n["updated_at"][:10]}</time></p></header>{figure(note.get("cover"), eager=True)}'
                f'{note.get("body_html", "")}{("<p>Credits: " + E(note["credits"]) + "</p>") if note.get("credits") else ""}'
                f'{("<section><h2>References</h2><ol>" + refs + "</ol></section>") if refs else ""}{("<section><h2>Downloads</h2><ul>" + dls + "</ul></section>") if dls else ""}</article>'
                f'<section><h2>Related Field Notes</h2>{note_list(n["related"])}</section>')
        art = {"@type": "BlogPosting", "headline": note["title"], "description": seo.get("description") or note.get("standfirst", ""), "datePublished": n["published_at"],
               "dateModified": n["updated_at"], "author": {"@type": "Person" if "team" not in (note.get("author") or "").lower() else "Organization", "name": note.get("author")},
               "publisher": {"@id": f"{SITE_URL}/#org"}, "mainEntityOfPage": canonical}
        if cover:
            art["image"] = {"@type": "ImageObject", "url": SITE_URL + cover["src"], "width": cover["width"], "height": cover["height"], "caption": cover.get("caption")}
        og = await share_image(seo, site, cover or site.get("default_share"))
        return 200, doc(site, title, seo.get("description") or note.get("standfirst", ""), canonical, body,
                        {"@context": "https://schema.org", "@graph": [org_ld(site), art, crumbs(trail)]}, seo.get("noindex"), og, "article"), {}
    return await not_found(site)
