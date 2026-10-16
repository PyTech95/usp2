# Theatre reference implementation notes

The supplied `USP Theatre stories beyond the stage (1).webp` is the visual source of truth. Its typography is entirely sans-serif, hero copy overlays a full photograph, and the archive uses a wide photograph below its text. These observations supersede conflicting serif/split-hero suggestions in the generated design_guidelines.json.

- Preserve shared header/footer/navigation and every other route. Scope new CSS to #theatre-reference.
- Use Public Sans, pale neutral background, thin grey dividers, short ruby rules and an unframed grey Ambition band. No cards, invented graphics or generated media.
- Exact owner-supplied white-costume photograph for hero; red/grey/green photograph for past work. Preserve originals in existing object storage, use approved library IDs and existing derivative/photo component pipeline.
- Hero and intro, everyday culture, past work, current production, ambition, connect. Hide but retain the existing notes-feed block for later use. Keep existing section IDs and style overrides; separate shared header/footer settings are untouched.
- Desktop hero copy overlays the lower image with readable contrast. Small screens show the full photograph above its dark caption band so text does not obscure performers. Archive photograph remains fully visible at 3:2.
- Introduction/culture/production/ambition have paired columns on desktop; single columns on narrow mobile. Body 16px desktop/14px mobile, H2 18px desktop/16px mobile per editor-system guidelines, H1 48/40/30/26 at fixed breakpoints; no viewport-scaled type. Generous section spacing and zero horizontal overflow.
- All new text fields, image references, links and wrappers have stable test IDs and use the existing sx editor styling hooks. New secondary question/copy fields must remain independently editable and persist through save/reload and release capture.
- Existing link destinations are /our-work/theatre#past-work and #prayer-meeting (confirmed in apply_client_content.py); Connect uses the existing /connect route. No invented production-detail routes.