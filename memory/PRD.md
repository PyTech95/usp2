# USP India — PRD

## Original problem statement
"USP India — Emergent Master Build Prompt": build a complete database-backed NGO website and a genuinely usable admin panel for USP India / Urban Suburban Perspectives (https://www.uspindia.org). Warm contemporary documentary-journal direction; five menus (Home, About, Our Work [Rakhigarhi, Theatre, Craft & Livelihood, Workshops & Learning], Field Notes, Connect); originals are documentary records — never regenerate, beautify or invent; separate authenticity / permission / edit-approval; real CMS (pages with blocks, drafts, publishing, revisions, Field Notes, Media Library with focal points, versions, before/after, Menus, Appearance tokens with contrast validation, Enquiries, SEO & Sharing with redirects, Users with Owner/Editor/Contributor/Reviewer, Settings); server-rendered public HTML with metadata, JSON-LD, sitemap, real 404s; security (hashed passwords, CSRF, rate limiting, sanitised HTML, validated uploads); no invented facts; private preview with approval checklist. (Full text in the first conversation message.)

User choices: JWT email/password with 4 roles; enquiries stored only (email "not configured"); server-rendered HTML now while keeping React + FastAPI; photos supplied as zip + Photo Asset Guide; owner = intrinsicamerica.web@gmail.com.

## Architecture
React 19 (CRA) + FastAPI + MongoDB + Emergent object storage. Public HTML rendered by FastAPI `/api/ssr` and served at public URLs via `frontend/src/setupProxy.js` (real 200/301/404), then React takes over. See /app/HANDOVER.md.

## User personas
USP India owner/admin; editors; contributors (drafts); client reviewer (comments/approval); public visitors; search engines.

## Implemented (2026-10-10)
- 9 public routes + Field Note template, SSR with title/description/canonical/robots/OG/JSON-LD (Organization, WebSite, WebPage/AboutPage/ContactPage/CollectionPage, BreadcrumbList, BlogPosting+ImageObject), sitemap/robots driven by indexing switch (OFF for preview), real 404, slug redirects.
- Block-based page editor (12 block types), drafts vs published, publish/discard, revisions + restore, review comments/approve, responsive preview, keyboard + drag reorder.
- Field Notes: CRUD, preview, publish/unpublish, slug-change redirect offer, authors/categories/tags, references, downloads, related; public search, topic filters, pagination with real links.
- Media Library: upload (content-validated), duplicate detection → canonical record, alt/caption/credit, provenance/permission/edit approval, minors gating, expiry, private evidence ref, focal points, replace + version history/restore, edited derivatives with edit log + before/after slider + revert placements, usage tracking, soft delete; EXIF/GPS-free derivatives, never upscaled; server-side public eligibility.
- Imported all 20 supplied files per the guide (AI references & screenshots private/restricted, brick house restricted, door duplicate linked, mango versions unverified); one conservative border-trim derivative for the blue basket (edit pending). Proposed placements on Home/Our Work/Craft are in place but NOTHING is approved, so the public site shows typographic layouts until permissions are recorded.
- Menus (required items protected), Appearance (colour tokens, fonts, size, spacing, buttons, logo, favicon, footer, privacy; contrast check; reset), Enquiries (status, notes, delete, CSV export), SEO audit + redirects, Users (invite links, roles, reset links), Settings (contact, social, banner, indexing, default share image, asset & consent register, JSON backup), Dashboard with approval checklist.
- Testing: 54 backend tests passed (iteration_1); frontend smoke passed; approval → public → withdrawal round-trip self-verified.

## Update 2026-10-10 (iteration 2)
- Recorded client-confirmed consent (chat) for 11 candidate originals + blue-basket border-removed derivative via `backend/scripts/record_approvals.py` (approval log + permission notes). Minors question unanswered → default "no minors" recorded; must be re-checked. Mango versions, AI references, screenshots, marked dolls, brick house and near-duplicate dolls stay private.
- Public "View the original photograph" toggle (with edit note) beside approved edited images; per-placement "hide" option; SSR includes the link.
- Tests: 61/61 backend, 6/6 frontend scenarios (iteration_2).

## Update 2026-10-10 (iteration 3) — visual redesign
- User: "design is boring, no images". Placed the 12 approved photographs across every public page via `backend/scripts/place_photos.py` (heroes, Our Work cards, wide image modules, About gallery, Craft gallery). Placements are editable in admin; Rakhigarhi→door and Theatre/About→reading circle are provisional and should be confirmed by client.
- Redesigned public site: two-tone home hero, full-bleed inner heroes (focal-point crops, 21/9 desktop → 4/3 mobile), 4-column work cards with hover zoom, framed photos with ochre offset, masonry galleries, sticky section headings, green invite band, dark footer, paper-grain overlay, staggered reveals. Home hero shown uncropped (register requires all eight women visible).
- Tests: 61/61 backend; frontend regression iteration_3 passed (contact "error" in test = 2.5s anti-bot timing guard, expected).

## Update 2026-10-10 (iteration 4) — home page enhancement
- Home: "Four areas of work" index strip under hero (from main menu children), Introduction rendered as a large serif statement (`text.style = "statement"`), new "From the field" asymmetric photo mosaic (`gallery.layout = "mosaic"`, surface band, hover zoom). Both options are data-driven and editable in the page editor.
- Note: Blocks.jsx edits once failed to hot-reload (CSS updated, JS stale) — `sudo supervisorctl restart frontend` fixed it.

## Backlog
- P0: client copy, colour chart, permissions for photos, hero selection, verified contact details.
- P1: production hosting rule for SSR (route HTML to /api/ssr, set SSR_SCRIPT_TAGS to build bundle); email notifications provider (needs approval); WebP derivatives; full UI test of contributor/reviewer flows.
- P2: Hindi content model activation; scheduled publishing (only with tested scheduler); image detail crops.

## Next tasks
Await client content and permissions; then record approvals in Media Library and enable indexing at launch.

## Update 2026-10-12 — ported to new Emergent environment
- Code copied from USP-India-main.zip; new .env files (fresh JWT_SECRET, same owner creds); photos re-imported into object storage; place_photos.py now looks up media by filename; home statement intro + mosaic restored; SSR_SCRIPT_TAGS=/static/js/bundle.js for dev SSR proxy.
- Tests: 61/61 backend, frontend flows passed (iteration_1 in this env).

## Update 2026-10-12 (iteration 5) — client copy, mockup, fonts/colours, navigation
- Applied client PDFs via `backend/scripts/apply_client_content.py` (idempotent for notes; rewrites Home/Theatre/Craft/Workshops draft+published, saves a revision first).
- Craft & Livelihood rebuilt to the supplied mockup; Home, Theatre, Workshops & Learning carry approved copy. Section anchors + 3-level mega navigation (About > Team; Our Work > areas > sub-sections).
- Site-wide Public Sans + warm grey palette (#F8F3F2 / #EDEAE7 / #575757 / #454545); numbers #6E6963 (sheet's #76716B fails 4.5:1); Workshops page ruby #D41445 + hero #F0EEEC. Light footer.
- New block options: eyebrow, subheading, layout (columns/stacked/statement), aside statement, grey band, anchor, image heading/body, work-card subtitle, multiple invite buttons; SSR updated. "Volunteer" enquiry topic added.
- Two Field Note drafts (What Was Already There. / The OG Basket Makers.) await story text. Omitted links without destination: "Explore Past Productions", "Explore The Prayer Meeting Edit", "Explore Film". Research & Documentation nav deferred ("for later").
- Tests: 61/61 backend; frontend iteration_2 passed; mobile submenu bug fixed after.

## Update 2026-10-12 (iteration 6) — Craft & Livelihood matched to mockup
- Measured client screenshots: neutral bg #F9F9F9, bands #ECE9E5, fluid 7vw margins, regular-weight eyebrows, type scale in vw, text-cols 5fr/7fr, basket 4:5 / dhurrie 2:3 / group 2:1 crops. Captions, view-original and breadcrumbs hidden on the craft page only.
- Client-edited photos (weaver w/o neighbour, group, dolls) imported via `scripts/import_edits.py` as approved `edited_original` derivatives; all placements swapped (originals kept, restorable).
- Footer simplified to brand + nav row and a slim bottom line. Mobile submenu fixed (hover only ≥961px fine pointer). Tests: pytest 61/61, iteration_3 all visual criteria pass.
- Note: frontend hot reload sometimes serves a stale bundle — `sudo supervisorctl restart frontend` if changes don't appear.

## Update 2026-10-12 — imported to new environment + craft spacing
- Code imported from urban-main.zip; new backend/.env (same owner creds, SITE_URL, PREVIEW_URL, SSR_SCRIPT_TAGS=/static/js/bundle.js), frontend SSR_BACKEND_ORIGIN; content & photos restored via scripts (import_assets → record_approvals → place_photos → import_edits → apply_client_content).
- Origin check now also allows same-origin requests (published domain works without editing CORS_ORIGINS).
- Craft & Livelihood: vertical rhythm matched to client mockup (text sections ~67px padding, Three Crafts→Basket gap, flush image→Impact gap fixed); mobile (<760px) stacks split/text-cols/aside layouts.
- Next: publish to live URL after user confirmation.
- 2026-10-12: Home, Theatre, Workshops & Learning now share the Craft page's mockup rhythm (non-band text sections ~4.3vw padding, flush-image follow-up, image-body spacing). Mobile Home hero caption/original-link aligned with page margin.
- 2026-10-12: Homepage redesign (scoped to .page-home): full-bleed photo hero with overlay text + glass "Four areas of work" strip, larger Who We Are, beige Our Work band with lifting cards, full-bleed baskets image, dark "What Takes Shape" band, card-style Field Notes, terracotta Connect band. Other pages untouched. Tested iteration_5 (toggle click-through bug fixed after).
- 2026-10-12: Home SEO set in CMS (draft+published): title 'USP India | Heritage, Art & Culture in Rakhigarhi', 155-char description. Site-wide noindex remains until 'indexing_enabled' is turned on in admin Settings.
- 2026-10-12: Homepage restyled to user-supplied 'editorial journal' reference (Literata serif + Source Sans 3, forest #344C40 / clay #9A4F36 / bg #F9FAF2, bordered paper cards, 2-col hero with framed photo + caption bar, forest footer). Scoped via .page-home and .site:has(.page-home) for header/footer; replaces previous immersive hero. Fonts added to public/index.html and backend/ssr.py.
- 2026-10-12: Homepage typography matched to chanakya.school/about (Cormorant 400 headings #001223; Public Sans 300 15px/1.6 body #575757 ls .02em; 11px .2em nav/labels; Public Sans 100 intro lines). Our Work menu reduced to 4 items (sub-links removed in settings.menus; backup at /app/memory/menus_backup.json).
- 2026-10-12: Site-wide: Chanakya typography (Cormorant 400 headings, Public Sans 300 body), strict black & white (white bg, black footer, black buttons weight 500, no italics anywhere), vertical spacing cut ~50% (.site main .section padding clamp(1.5rem,2.6vw,2.4rem) !important; tighter hero/eyebrow/heading/image gaps). Craft page 6892→5549px. Renamed 'Workshops & Learning' → 'Workshop and Learning' in menu + page titles/headings (note category & contact topic values unchanged). Added Tagore-style thin quote block (index 2) on home; home CSS block indices shifted +1. NOTE: re-running backend/scripts/apply_client_content.py would restore old labels.
- 2026-10-12: Responsive fix: .site .work-grid auto-fit + 4 cols ≥1280 / 2 cols 640–1279 / 1 col <640; splits & text-cols stack ≤900 (photo max 560px); mobile brand-sub single line, full-width hero/invite buttons ≤600. testing_agent iteration_6: 100% (9 pages × widths, no overflow).

## Update 2026-06 — responsive hardening
- Fixed home-only horizontal overflow at <=360px: brand tagline ("URBAN SUBURBAN PERSPECTIVES") was forcing the header wider and pushing the MENU toggle off-screen. Brand flex item now shrinks (min-width:0), tagline wraps/hides <=380px, menu toggle stays visible.
- Verified no horizontal overflow across public pages (home, about, our-work/*, craft-livelihood, field-notes, connect) and admin (login + dashboard) at 320/360/414/768px. CSS-only change in frontend/src/index.css.

## Update 2026-06 — tablet polish + admin touch
- Tablet (≤1024px): two-column photo sections (.split / image+text / text-cols / stacked-aside) now stack into a comfortable single column with generous spacing (prev. cramped 2-col above 900px). Verified single-column + no overflow at 768/912/1024; desktop (>1024) 2-col unchanged.
- Admin touch (frontend/src/index.css + PageEditor.jsx): added @media (pointer: coarse) rules scoped to .admin — 44px min tap targets for buttons/selects/summaries, 44px rich-text toolbar buttons, 16px inputs/selects/rt-editor (prevents iOS focus-zoom), 20px checkboxes/radios, taller range sliders, 180px rich-text min height. Section editor action-icon row now wraps on ≤640px (title on its own row) via .admin-card-bar/.admin-card-title. Pages/Media editors already stacked below xl(1280px).

## Update 2026-06 — fix: home "Our Work" squished on desktop (index-drift bug)
- Bug: home work cards (related_work) crushed into a ~573px left column on desktop, text one-word-per-line. Cause: home layout CSS targeted blocks by index ([data-testid=block-N]); after content re-import the block order shifted, so a stale 5fr/7fr grid meant for an old quote block (index 2) trapped related_work; notes_feed (index 5) had the same stale-grid risk.
- Fix: added block-TYPE wrapper class `hb hb-<type>` (+ data-block-type) in Blocks.jsx Block(); appended type-based overrides in index.css so `.hb-related_work > section` and `.hb-notes_feed > section` use full width. Durable against future index drift.
- Verified by testing_agent (iteration_7, frontend 100%): desktop 4-col (296px cards), 1024px 2-col (455px), 768px 2-col (337px), 390px 1-col (350px); no horizontal overflow anywhere; notes feed full-width; regression pages (/about, /our-work, /craft-livelihood, /connect) clean; card nav works.
- Known non-blocking: recurring 401s in console on public pages (auth-refresh interceptor probing when logged out) — harmless, pre-existing.
- Note: a deploy was in progress when this fix landed — redeploy to push this fix to the live .emergent.host site.

## Update 2026-06 — craft-livelihood spacing + brand typography
- Craft & Livelihood page: tightened vertical rhythm per client (page-scoped, !important to beat `.site main .section` clamp): eyebrow→heading -60% (4px), heading→image -50% (10px), image→text -40% (12px); section gaps 1↔2 -50% (~37px), 2↔3 -66% (~25px), 3↔4 -30% (~52px, below basket); blocks 5/6/8/9 tightened. Block-5 framed textile image centered in its column (justify/align center, max-width 440px).
- Brand typography applied to all public content pages (home excluded via its more-specific .page-home rules): title .h2 = 27px/35px (≤1440); eyebrow = 12px/700/lh24/0.2em/uppercase/#575757; body (.prose/.lede/.hero-after/.split-text/.image-body/.work-card-body p) = 16px/24px (≤1440). Used `.site:has(main)` to beat existing line-height:1.75 and eyebrow weight:500/#111 overrides. Home verified unchanged.

## Update 2026-06 — replaced block-5 textile image (craft-livelihood)
- Replaced the framed textile wall-hanging image in-place via media /replace logic: media_id a46cb7c0d03e4c97b2465e71b65572d1 now v2 (textile-wall-hanging.png, 1086x1448, derivs 800/1086). Page reference + public-approval status preserved; public URLs carry ?v=2 so cache busts automatically. Old version archived in media.versions.

## Update 2026-06 — craft-livelihood 100% mockup match (verified)
- Section-by-section match to client mockup. Key fix this round: restored light-grey band backgrounds (#EFEDEA, border #e3e0dc) on 'A new material' (block-4) and 'From Rakhigarhi, Outwards' (block-9) — the monochrome pass had made bands white. Scoped to the 4 Our Work content pages via :is(.page-craft-livelihood,.page-rakhigarhi,.page-theatre,.page-workshops-learning) so home is untouched.
- Verified by testing_agent (iteration_8, frontend 100%): all sections render; bands grey; typography (h2 27/35, eyebrow 12/700/#575757, body 16/24); block-5 image v=2 loads/centered; no overflow at 1440/768/390; home regression clean (bands white, eyebrow 11px).
- Note: 'Craft enquiries' contact_invite (block-10) remains (mockup was truncated before it). Non-blocking: 2x 401 console probes on public pages (pre-existing auth-refresh), harmless.

## Update 2026-06 — craft-livelihood hero/padding refinements (verified)
- Page horizontal padding set to 50px L/R via `.site:has(.page-craft-livelihood) .wrap { padding-inline: 50px }` (header/content/footer stay aligned at left=82px).
- Hero image top-anchored: `.page-craft-livelihood [data-testid="block-0-image"] img { object-position: 50% 0% }` so the subject's head is fully visible (bottom crops).
- Hero title→image spacing +20% (hero-text padding-bottom 10px→12px). Three-crafts image+text section left unchanged per request.
- Verified by testing_agent (iteration_9, frontend 100%): 50px padding + alignment, object-position 50% 0%, padding-bottom 12px, grey bands intact, typography intact, no overflow at 1440/768/390, home unchanged (48px).

## Update 2026-06 — title font = Public Sans
- Titles (.h1, .h2, .text-cols-head .h2) on content pages now use "Public Sans", sans-serif (was Cormorant serif). Home page titles explicitly kept on var(--j-serif) Cormorant so its journal look is preserved. Public Sans already loaded via index.html Google Fonts. Verified via computed styles: craft hero/section = Public Sans; home hero/section = Cormorant.

## Update 2026-06 — site-wide padding, hero title, header nav restyle
- Horizontal inset set to 100px L/R site-wide incl. home (responsive clamp(24px,7vw,100px)); header/content/footer aligned; no mobile overflow.
- Craft hero title→image gap increased to 16px.
- Hero title (content pages) = 39px, font-weight 300 (.site:has(main) .hero-inner .hero-text .h1).
- Header nav restyled toward client reference (Chanakya): nav-list gap .5rem, nav-link letter-spacing .16em, active item shows a grey box (#EFEDEA, border-radius 2px, no underline) instead of underline. USP branding kept (logo graphic / secondary brand label from reference are brand-specific, not copied).

## Update 2026-10-14 — ported to this environment + matched reference deployment
- Code from usp-source.zip; fresh .env (new JWT_SECRET, same owner creds, own EMERGENT_LLM_KEY for storage).
- Reference site https://usp-india-cms.preview.emergentagent.com ran newer frontend code than the zip: recovered exact sources from its source maps (LiveEditor.jsx, Blocks/Photo/PublicLayout/PageView/Settings/site.js, index.css with new content-page header + Craft hero overlay).
- Backend added: PUT /api/admin/pages/{key}/live (style whitelist, publishes + snapshots), `live_editor_enabled` setting.
- `backend/scripts/sync_from_reference.py <url>` mirrors settings/menus/theme, all 9 pages and their approved media (same IDs) — all page JSON identical to reference.
- Tests iteration_3: frontend pass; pytest 58/61 (3 asserted old media IDs replaced by reference content; approval_log fixed).

## Update 2026-10-14 (b)
- Craft hero heading single line per mockup; basket photo replaced with client hi-res (blue-basket-hires.png, 1122x1402, crop 4/5; previous version kept in media history).
- Site-wide darker text: theme text #2B2B2B, green #222222, terracotta #4F4A45 (DB + seed default + index.css); hardcoded greys in index.css darkened (colour only).
- Workshops & Learning page updated to client PDF (13): eyebrow/title/menu label "Workshops & Learning", new Restoration Skills copy, Ambition split into 3 paragraphs, notes feed hidden (not in PDF); "Explore Film" omitted (no URL). Revision saved before change.
- Workshops & Learning redesigned to client mockup: mint #DCEFE8 nav boxes (this page only) + intro band (statement left, ruby rule, paragraphs right), text-only beige hero (hero image kept as prev_image), overlapping Creative Exchange / Restoration cards. Revision "before mint redesign" saved.
- Workshops: nav + intro band lavender #EBE7EB, hero warm gray #EDEAE7, white 6px gap hero→intro, ruby rule.
- Header unified on all pages (incl. Home): Public Sans brand, nav band pale peach #FCF1ED with dividers, active link ruby #D41445, 6px white gap above hero, no border line. Hero grey #ECE9E4 for text heroes; Workshops mint nav boxes removed.
- Home redesigned to client mockup + PDF (15): warm-grey uppercase hero (no photo; prev image/buttons/intro kept in data), Who We Are 2-col, numbered 2x2 Our Work grid without photos, What Takes Shape warm-grey band, Field Notes 2 curated cards (data.cards; link to /field-notes until stories published; basket card uses older-woman weaving photo as stand-in), Connect text links, full-image block hidden. Light footer site-wide with tagline "Heritage, Art and Culture". Revision "before home mockup redesign" saved.
- Site-wide type & spacing scale (index.css end): eyebrow 13/400, h1 52, h2 34, h3 26, body 18/1.75, lead 23, statement ~30, section padding ~104px at 1920 (clamped for mobile). Page-specific mockup layouts (Craft, Workshops cards) keep their own spacing.
- Rakhigarhi page rewritten from client PDF (16): hero + intro, Haveli & Chaupal, "A Haveli Brought Back Into Use" + Craft Centre / A Place to Arrive / A Place to Pause, The Ambition band with aside. Placeholder sections (Place and community, Archaeology, Local accounts, Related Field Notes) hidden. Duplicated sentence in PDF used once. Revision saved.

## Update 2026-06 — ported & deployed to this Emergent environment
- Restored from usp-india-final.zip: backend + frontend copied to /app; fresh backend/.env (new JWT_SECRET, same owner creds, own EMERGENT_LLM_KEY for object storage, SITE_URL/PREVIEW_URL = preview URL, SSR_SCRIPT_TAGS=/static/js/bundle.js); frontend/.env SSR_BACKEND_ORIGIN=http://localhost:8001.
- MongoDB restored from export/db (85 docs). All 95 media files re-uploaded to the new object storage via scripts/upload_media_to_storage.py. Verified: public pages render, media serves, owner login works.

## Update 2026-06 — ADVANCED LIVE EDITOR (Squarespace/Elementor-style)
- User asked for a fully advanced, dead-simple visual editor reachable from the admin panel.
- Admin: new prominent "Live Editor" button in the sidebar (AdminLayout.jsx, data-testid admin-nav-live-editor) → opens /?edit=1; shown to owner/editor (content.publish). `live_editor_enabled` setting = true.
- Frontend (components/public/LiveEditor.jsx, full rewrite): click any heading/text/image/section to select it; inline contentEditable text editing; drag red handles to resize (width/height); floating per-section toolbar (move up/down, duplicate, hide, delete, add-below); right panel controls — font family, size, weight, bold, italic, UPPERCASE, colour, alignment, line-height, letter-spacing, width/height; SECTION BACKGROUND & SPACING (background colour, top/bottom padding); Add-a-section menu (text, image+text, big image, gallery, quote, call-to-action, hero); undo/redo; device preview (desktop/tablet/mobile). Save publishes live immediately.
- Empty image slots show a "Click to add an image" placeholder in edit mode (Photo.jsx photo-addslot) → opens media library/upload.
- Blocks.jsx: Block() applies section-level styles (styles._section) to the wrapper; sx() now applies per-field typography via a ref with CSS `!important` priority so editor font/size/weight/line-height/letter-spacing override the site-wide `!important` rhythm rules in index.css (the critical fix from testing iteration_1).
- Backend (routes_admin.py): PUT /api/admin/pages/{key}/live rewritten to accept the FULL ordered section list (supports add/remove/reorder/hide + data + styles), expanded STYLE_KEYS (backgroundColor, padding*, margin*, fontStyle, textTransform, borderRadius, opacity, maxWidth, objectPosition), strip_resolved() drops server-resolved media before persisting, snapshots each live publish for revision history.
- CSS (index.css): editor UI additions (section tools, add menu, device frames, placeholders) + z-index fix so the editor panel/toolbar sit above the sticky public header.
- Testing: testing_agent iteration_1 — 12/15 flows pass; fixed the 2 blocking issues found (typography !important override + save-button z-index occlusion); re-verified via Playwright (computed font-size 52→72px, colour applied, save clickable, success toast, persistence round-trip). Anonymous visitors never see the editor. Pages collection restored to clean state after tests.

## Update 2026-06 — Site Import / Export (move whole site)
- Admin → **Import / Export** (`/admin/transfer`, nav item, owner/config only). Page: `pages/admin/ImportExport.jsx`.
- Backend (`routes_admin.py`): `GET /api/admin/site-export` builds a `.zip` = `content.json` (settings, pages, notes, media, redirects) + all media binaries under `media/<path>` (fetched from object storage, parallelised with a 16-way semaphore to avoid gateway timeout) + `manifest.json` (ctypes + counts). `POST /api/admin/site-import` reads the zip, re-uploads every media file to this env's object storage, and upserts all content collections (key/id/from/slug detection); user accounts are left untouched; snapshots the import.
- Verified via curl round-trip: export = 97MB zip, 104/118 media saved, 9 pages/3 notes/40 media/1 settings; import returned ok with media_restored=104. UI verified via screenshot (nav item + both cards + warning).
- Lets the owner move the entire website between environments (pairs with the GitHub-code + DB-dump guidance for VPS self-hosting).

## Update 2026-06 — ADVANCED FREE-FORM LIVE EDITOR (8-way resize + move anywhere)
- User (Hinglish): make the live editor "advance" — resize any element/section from ALL sides (top/bottom/left/right + corners), MOVE/drop an element anywhere, and fix the bug where resizing a text block also grew its neighbour (the lady image on Rakhigarhi). Visual-float (overlap allowed), site-wide, with numeric controls.
- `LiveEditor.jsx`: replaced the 3 old handles with 8 directional resize handles (`live-resize-n/s/e/w/ne/nw/se/sw`) + a dark move grip (`live-move-grip`). `resize(dir)` adjusts width/height and, for W/N drags, shifts translateX/translateY so the opposite edge stays anchored; `moveDrag` repositions via translate. Reads the live element rect at pointer-down and uses `setPointerCapture` for reliable fast drags. Panel now has numeric Width/Height + Move X/Y (`live-width/height/move-x/move-y`) and `Reset position` (`live-reset-pos`) alongside Reset size / Clear styles — shown for text, image AND whole-section selections.
- `Blocks.jsx`: new `layoutStyle(raw, field)` converts width/height/translateX/translateY into inline CSS — uses `transform: translate()` for movement (no reflow) and `position:relative; align-self:flex-start; justify-self:start` on the selected element so its new box never reflows siblings (THE decoupling fix). Applied `!important` via ref for text; `secStyleOf()` applies the same to the section wrapper.
- `Photo.jsx`: figure now also honours transform/position/alignSelf/justifySelf/zIndex from `ed.style`, so images can be freely moved/resized too.
- `routes_admin.py`: `STYLE_KEYS` += `translateX`, `translateY` (persisted by PUT /pages/{key}/live). Verified via curl round-trip.
- Testing: testing_agent iteration_4 — 100% frontend pass. Neighbour image bounding rect stayed byte-identical across all 8 resize directions, move-grip drag and numeric X/Y/W/H changes on the sibling text (the reported bug is resolved). Anonymous users still never see the editor. Pages left in clean state after tests.

## Update 2026-06 — on-element directional distance badges
- User: when any section/element is selected, an on-element "number view" should show how many px to move up/down/left/right, and work 100%.
- `LiveEditor.jsx`: added a `Dim` component rendering four editable pixel badges pinned inside the selection box (`live-dim-up/down/left/right`, inputs `*-input`), each with an arrow icon. Up/Down map to −/+ translateY, Left/Right to −/+ translateX (mutually exclusive per axis), live-synced with drag and the panel Move X/Y. `index.css`: `.live-dim*` styles position them at the four side-centres.
- Self-verified via Playwright (logged-in owner, /our-work/rakhigarhi?edit=1): all four badges render on the selected heading; typing 25 in the Up badge applied `transform: matrix(1,0,0,1,0,-25)` and synced the panel Move Y to −25. No save performed, page left clean.

## Update 2026-06 — per-element / per-box padding controls
- User: when a text/box is selected, let me edit the padding inside the box (top/bottom/left/right) easily, e.g. reduce an existing 10px to 5px.
- `Blocks.jsx` `layoutStyle()` now also applies paddingTop/Bottom/Left/Right for any field (not just sections), `!important` via the ref so it overrides CSS-class padding; `secStyleOf()` delegates padding to `layoutStyle` (removed its duplicate list). `Photo.jsx` passes padding through to the figure.
- `LiveEditor.jsx`: added a "Padding inside box (px)" group (Top/Bottom/Left/Right — data-testids live-pad-top/bottom/left/right) shown for text, image and section selections. Each input's placeholder shows the element's CURRENT computed padding (via getComputedStyle) so the user can see 10 and change it to 5. Backend STYLE_KEYS already whitelists the padding keys.
- Self-verified via Playwright (owner, /our-work/craft-livelihood?edit=1): selecting body text shows the padding group; placeholder reflects current padding; setting Top=5 gives computed `padding-top: 5px`. No save performed. NOTE: frontend needed a `supervisorctl restart frontend` for the new JSX to leave the stale dev bundle.

## Update 2026-06 — HOMEPAGE matched to client mockup (USP_Homepage_Revised) — CURRENT
- User changed direction: home must match the supplied "USP_Homepage_Revised" mockup 100% (clean editorial, NOT the cinematic version). Reverted the cinematic changes (Blocks.jsx + index.css to commit 98c61f1), then rebuilt to the mockup.
- `Blocks.jsx` home Hero → `.hero-plain`: warm-grey band, text-only, heading split per sentence into `.hero-line` spans (uppercase via CSS), `.hero-tagline` = first sentence of intro; NO photo, NO buttons, NO AreaStrip. Hero text is NOT `.reveal` (always visible; fixes SPA back-nav fade).
- `index.css` (appended last, scoped `.page-home`/`.site:has(.page-home)`): warm off-white page `#FBFAF8`, warm-grey bands `#EDEAE7` (hero + What Takes Shape), Public Sans everywhere (overrides home's Cormorant), grey eyebrows (no dash), numbered Our Work 2x2 grid with photos hidden (big grey number + rule + label + title + body + Explore), wide image block hidden, 2-col Who-We-Are/What-Takes-Shape/Connect, Field Notes 2 photo cards, text-link Connect (Collaborate/Volunteer/Get in Touch), light footer, pale-peach nav band. Drift-proof TYPE selectors.
- DATA: `backend/scripts/apply_home_mockup.py` (run on PREVIEW db) hid the home `image` block and set notes_feed `cards` = 2 approved cards: "What Was Already There." (media 07f3512b…, dolls) + "The OG Basket Makers." (media 6fc82b55…, eight-women baskets), more_label "Explore Field Notes".
- Verified: testing_agent iteration_7 = 100% on mockup acceptance criteria; regression pages unaffected; no overflow 1440/390.
- ⚠️ PROD DATA: the Field Notes 2 cards + hidden image flag are DATA in the preview DB. The hidden-image is also enforced by CSS, but the 2 Field-Notes cards need the same data in production or that section will fall back to the published-notes list. Sync via admin Import/Export or a migration after deploy.

## (superseded) Update 2026-06 — HOMEPAGE cinematic redesign
- User (Hinglish): "redesign this" homepage (shared screenshot of the flat text-only home). Chose a blend of Immersive-Cinematic + Bold-Editorial + Warm-Documentary; defaults: photos prominent, keep header/footer consistent, warm palette, preview-first.
- Design blueprint generated by design_agent (`/app/design_guidelines.json`): warm paper #F9F6F0, dark #1E1A17 bands, ruby #B83227 + ochre #C88A3B accents, Cormorant serif + Public Sans.
- `Blocks.jsx` Hero() home branch rewritten → FULL-BLEED cinematic hero: `.hero-cinematic > .hero-cine-stage` (bg image of 8 women, `.hero-cine-media` img w/ Ken-Burns, `.hero-cine-scrim` 2-layer gradient, `.hero-cine-grain` noise, `.hero-cine-inner` overlaid white eyebrow/H1/intro/CTAs) + dark `.area-strip` index bar below. Other block types unchanged.
- `index.css`: large `.page-home`/`.site:has(.page-home)` redesign block appended at END (overrides the earlier site-wide monochrome layer for HOME ONLY; inner pages untouched). Sections targeted by drift-proof TYPE classes (`.hb-related_work`, `.hb-text:not(.band)`, `.hb-text.band`, `.hb-image`, `.hb-notes_feed`, `.hb-contact_invite`). Warm cards w/ hover-lift + image zoom, ruby-accented Who-We-Are, DARK "What Takes Shape" manifesto band (white serif heading), field-notes & connect bands, warm-dark footer, grain textures, scroll reveal reused.
- Key fixes (iter_5→iter_6): hero made flush (excluded `.hb-hero` from section-padding rule); dark band heading made white (stacked layout heading `.hb-text.band .h2`, not just `.text-cols-head`); scrim strengthened (bottom + left gradients) for text contrast.
- NOTE: site is SSR-first → screenshot_tool captures the pre-hydration shell (looks empty); use testing_agent/Playwright with `wait_for_function` on `.hero-cinematic .h1` containing "Inherit". SSR HTML itself (backend ssr.py) is unchanged and still shows the OLD markup → production SSR should be updated to match the new hero for no-flash (P1 backlog).
- Verified: testing_agent iteration_6 — 100% frontend. Hero flush 0px gap, manifesto band rgb(30,26,23)+white heading, scrim legible, all sections present, no overflow at 1440/390, regression /about /our-work /craft-livelihood /field-notes /connect all 200 & unaffected.

## Update 2026-06 — margin controls + alignment snap guides
- User picked both from next-actions: outside-spacing (margin) boxes, and snap lines when dragging/resizing.
- MARGIN: `LiveEditor.jsx` added a "Margin outside box (px)" group (Top/Bottom/Left/Right — data-testids live-mar-top/bottom/left/right), placeholders show the element's current computed margin. `Blocks.jsx` layoutStyle() now applies marginTop/Bottom/Left/Right (and padding) `!important`; `secStyleOf()` delegates margins to layoutStyle. `routes_admin.py` STYLE_KEYS += marginLeft, marginRight (Top/Bottom already present).
- SNAP GUIDES: during move and resize, `gatherSnaps()` collects neighbour element/section edges + centres (left/right/centerX, top/bottom/centerY), `nearest()` snaps the dragged edge/centre within a 6px threshold, and cyan guide lines (`.live-guide`, data-testid live-guide, fixed full-viewport) render at the snapped coordinate. Guides clear on pointer-up. State: `guides`/`setGuides`.
- Self-verified via Playwright: margin Top=12 → computed `margin-top: 12px`; during a move-grip drag exactly 1 guide line appeared and the box snapped, 0 guides after release. No save performed.
