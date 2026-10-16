import { Link } from "react-router-dom";
import { ArrowRight, ArrowUpRight, Download } from "lucide-react";
import { Photo } from "./Photo";
import { ContactForm } from "./ContactForm";
import { NoteList } from "./NoteList";
import { media } from "../../lib/api";
import { useSite } from "../../lib/site";
import { CraftHero } from "./CraftHero";
import { WorkshopsHero } from "./WorkshopsHero";
import { RakhigarhiHero, HaveliRestoration } from "./RakhigarhiSections";
import { isImageField } from "./editor/editorFields";
import { SiteText } from "./editor/SiteText";
import { applyTypography } from "./editor/typography";

export const fontStack = (f) => `"${f}", system-ui, sans-serif`;
const LAYOUT_PROPS = ["width", "maxWidth", "height", "overflow", "transform", "position", "alignSelf", "justifySelf", "zIndex", "paddingTop", "paddingBottom", "paddingLeft", "paddingRight", "marginTop", "marginBottom", "marginLeft", "marginRight"];
const toKebab = (p) => p.replace(/[A-Z]/g, (m) => "-" + m.toLowerCase());
function applyProps(node, obj, keys) {
  if (!node) return;
  keys.forEach((p) => {
    const v = obj[p];
    if (v !== undefined && v !== null && v !== "") node.style.setProperty(toKebab(p), String(v), "important");
    else node.style.removeProperty(toKebab(p));
  });
}
// Build the free-form layout (size + float position) from editor style values.
export function layoutStyle(raw, field) {
  const o = {};
  const tx = raw.translateX, ty = raw.translateY;
  if (raw.width) { o.width = raw.width; o.maxWidth = "none"; }
  if (raw.height) { o.height = raw.height; if (!isImageField(field)) o.overflow = "visible"; }
  if (raw.objectPosition) o.objectPosition = raw.objectPosition;
  if (tx || ty) { o.transform = `translate(${tx || "0px"}, ${ty || "0px"})`; o.zIndex = 5; }
  if (raw.width || raw.height || tx || ty) { o.position = "relative"; o.alignSelf = "flex-start"; o.justifySelf = "start"; }
  ["paddingTop", "paddingBottom", "paddingLeft", "paddingRight", "marginTop", "marginBottom", "marginLeft", "marginRight"].forEach((k) => { if (raw[k]) o[k] = raw[k]; });
  return o;
}
export function sx(s, field) {
  const raw = { ...(s?.styles?.[field] || {}) };
  if (raw.fontFamily) raw.fontFamily = fontStack(raw.fontFamily);
  const style = layoutStyle(raw, field);
  return {
    "data-edit": field,
    style: Object.keys(style).length ? style : undefined,
    ref: (node) => {
      if (!isImageField(field)) applyTypography(node, raw);
      applyProps(node, style, LAYOUT_PROPS);
      if (node && !node.dataset.testid) node.dataset.testid = `editable-${s?.id || "text"}-${field.replaceAll(".", "-")}`;
    },
    ...(isImageField(field) ? { captionEd: sx(s, `${field}.caption`), creditEd: sx(s, `${field}.credit`) } : {}),
  };
}
// Section-wrapper style: visual props + free-form layout (translate -> transform).
function secStyleOf(raw) {
  if (!raw || !Object.keys(raw).length) return undefined;
  const o = {};
  ["backgroundColor", "borderRadius"].forEach((k) => { if (raw[k]) o[k] = raw[k]; });
  Object.assign(o, layoutStyle(raw, "_section"));
  return Object.keys(o).length ? o : undefined;
}
const Html = ({ html, testid, ed }) => <div className="prose" data-testid={testid} {...ed} dangerouslySetInnerHTML={{ __html: html || "" }} />;
const Eyebrow = ({ text, ed }) => (text ? <p className="eyebrow" data-testid={`eyebrow-${text.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} {...ed}>{text}</p> : null);
const Paras = ({ text, className = "lede", testid, ed }) => (text ? <div className={className} data-testid={testid} {...ed}>{text.split(/\n\s*\n/).map((t, k) => <p key={k}>{t}</p>)}</div> : null);
const H = ({ first, children, testid, ed }) => (first ? <h1 className="h1" data-testid={testid} {...ed}>{children}</h1> : <h2 className="h2" data-testid={testid} {...ed}>{children}</h2>);
const Btn = ({ href, label, ghost, testid, ed }) =>
  href?.startsWith("/") ? <Link to={href} className={`btn ${ghost ? "btn-ghost" : ""}`} data-testid={testid}><span {...ed}>{label}</span> <ArrowRight size={16} aria-hidden="true" /></Link>
    : <a href={href} className={`btn ${ghost ? "btn-ghost" : ""}`} data-testid={testid}><span {...ed}>{label}</span></a>;

const SectionHead = ({ first, heading, intro, testid, aside, s, columns = false }) => (
  <div className="sec-head">
    <div>{heading && <H first={first} testid={testid} ed={sx(s, "heading")}>{heading}</H>}{!columns && intro && <p className="lede" {...sx(s, "intro")} style={{ margin: 0, ...sx(s, "intro").style }}>{intro}</p>}</div>
    {columns && <Paras text={intro} testid={`${testid}-intro`} ed={sx(s, "intro")} />}
    {aside}
  </div>
);

function AreaStrip() {
  const site = useSite();
  const areas = (site?.menus?.main || []).find((m) => m.href === "/our-work")?.children || [];
  if (!areas.length) return null;
  return (
    <div className="wrap area-strip reveal d2" data-testid="area-strip">
      <span className="area-strip-label">Four areas of work</span>
      {areas.map((a, k) => (
        <Link key={a.id} to={a.href} className="area-link" data-testid={`area-link-${k}`}>
          <span className="work-num">{String(k + 1).padStart(2, "0")}</span>{a.label}<ArrowUpRight size={14} aria-hidden="true" />
        </Link>
      ))}
    </div>
  );
}

function Hero({ d, s, first, i, home, pageKey }) {
  const hasImg = !!d.image?.media;
  if (pageKey === "rakhigarhi") {
    return <RakhigarhiHero data={d} id={`block-${i}`} editable={(field) => sx(s, field)} />;
  }
  if (pageKey === "workshops-learning") {
    return <WorkshopsHero data={d} id={`block-${i}`} editable={(field) => sx(s, field)} />;
  }
  if (pageKey === "craft-livelihood" && hasImg) {
    return <CraftHero data={d} first={first} id={`block-${i}`} editable={(field) => sx(s, field)} />;
  }
  const text = (
    <div className="hero-text reveal">
      <Eyebrow text={d.eyebrow} ed={sx(s, "eyebrow")} />
      <H first={first} testid={`block-${i}-heading`} ed={sx(s, "heading")}>{d.heading}</H>
      {(home || !hasImg) && <Paras text={d.intro} testid={`block-${i}-intro`} ed={sx(s, "intro")} />}
      {d.buttons?.length > 0 && (
        <div className="hero-actions">{d.buttons.map((b, k) => b.label && <Btn key={k} href={b.href} label={b.label} ghost={k > 0} testid={`hero-btn-${k}`} ed={sx(s, `buttons.${k}.label`)} />)}</div>
      )}
    </div>
  );
  if (home) {
    const lines = (d.heading || "").split(/(?<=\.)\s+/).filter(Boolean);
    const tagline = d.tagline ?? ((d.intro || "").split(/(?<=\.)\s+/)[0] || "").trim();
    return (
      <div className="hero-home hero-plain" data-testid="hero-section">
        <div className="wrap hero-text">
          <h1 className="h1" data-testid={`block-${i}-heading`} {...sx(s, "heading")}>
            {lines.map((ln, k) => <span className="hero-line" key={k}>{ln}</span>)}
          </h1>
          {tagline && <p className="hero-tagline" data-testid={`block-${i}-intro`} {...sx(s, "tagline")}>{tagline}</p>}
        </div>
      </div>
    );
  }
  if (!hasImg) return <div className="wrap hero-type">{text}<Photo ref_={d.image} testid={`block-${i}-image`} ed={sx(s, "image")} /></div>;
  return (
    <div className="hero-inner">
      <div className="wrap">
        {text}
        <Photo ref_={d.image} eager crop="16/9" cropMobile="4/3" className="reveal d1" sizes="(min-width: 1240px) 1160px, 100vw" testid={`block-${i}-image`} ed={sx(s, "image")} />
        <Paras text={d.intro} className="hero-after" testid={`block-${i}-intro`} ed={sx(s, "intro")} />
      </div>
    </div>
  );
}

function RelatedWork({ d, s, i, home }) {
  return (
    <div className="wrap section">
      <Eyebrow text={d.eyebrow} ed={sx(s, "eyebrow")} />
      <SectionHead s={s} columns={home} testid={`block-${i}-heading`} heading={d.heading} intro={d.intro} aside={!home && <Link to="/our-work" className="more-link" data-testid={`block-${i}-all-work`}><span {...sx(s, "all_work_label")}>{d.all_work_label ?? "All areas of work"}</span> <ArrowUpRight size={16} aria-hidden="true" /></Link>} />
      <div className="work-grid">
        {(d.items || []).map((it, k) => (
          <article className={`work-card reveal d${k + 1}`} key={k} data-testid={`work-item-${k}`}>
            {!home && <Photo ref_={it.image} crop="4/5" sizes="(min-width: 860px) 24vw, 90vw" testid={`work-item-${k}-image`} ed={sx(s, `items.${k}.image`)} />}
            <div className="work-card-body">
              <span className="work-num"><span className="wn-n" aria-hidden="true" data-site-style="display.work-number" data-testid={`work-item-${k}-number`}>{String(k + 1).padStart(2, "0")}</span><span className="wn-sep"> — </span><span className="wn-t" data-testid={`work-item-${k}-category`} {...sx(s, `items.${k}.title`)}>{it.title}</span></span>
              <h3 className="h3"><Link to={it.href || "#"} data-testid={`work-item-${k}-link`}><span data-testid={`work-item-${k}-title`} {...sx(s, `items.${k}.subtitle`)}>{home ? (it.subtitle || it.title).split(/(?<=\.)\s+/).map((line, n) => <span className="work-title-line" key={n}>{line}</span>) : it.subtitle || it.title}</span></Link></h3>
              <p data-testid={`work-item-${k}-description`} {...sx(s, `items.${k}.text`)}>{it.text}</p>
              <Link to={it.href || "/our-work"} className="more-link" data-testid={`work-item-${k}-explore`}><span {...sx(s, `items.${k}.link_label`)}>{it.link_label ?? "Explore"}</span> <ArrowRight size={14} aria-hidden="true" /></Link>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

function NoteCards({ cards, id, s }) {
  return (
    <div className="note-cards">
      {cards.map((c, k) => (
        <article className="note-card reveal" key={k} data-testid={`${id}-card-${k}`}>
          <Photo ref_={c.image} crop={c.crop} sizes="(min-width: 860px) 45vw, 100vw" testid={`${id}-card-${k}-image`} ed={sx(s, `cards.${k}.image`)} />
          {c.eyebrow && <p className="eyebrow" data-testid={`${id}-card-${k}-category`} {...sx(s, `cards.${k}.eyebrow`)}>{c.eyebrow}</p>}
          <h3 className="h3" data-testid={`${id}-card-${k}-title`} {...sx(s, `cards.${k}.title`)}>{c.title}</h3>
          {c.text && <p data-testid={`${id}-card-${k}-description`} {...sx(s, `cards.${k}.text`)}>{c.text}</p>}
          <Link to={c.href || "/field-notes"} className="more-link" data-testid={`${id}-card-${k}-link`}><span {...sx(s, `cards.${k}.link_label`)}>{c.link_label ?? "Read the Story"}</span> <ArrowRight size={14} aria-hidden="true" /></Link>
        </article>
      ))}
    </div>
  );
}

export function Block(props) {
  const d = props.s.data || {};
  const t = props.s.type;
  const el = <BlockInner {...props} />;
  const secStyle = props.s?.styles?._section;
  const style = secStyleOf(secStyle);
  const hasBg = !!secStyle?.backgroundColor;
  return <div id={d.anchor || undefined} className={`hb hb-${t} ${d.band ? "band" : ""} ${hasBg ? "hb-bg" : ""}`} data-block-type={t} data-sec={props.s.id} style={style} ref={(node) => {
    applyProps(node, style || {}, [...LAYOUT_PROPS, "backgroundColor", "borderRadius"]);
    if (node) node.querySelectorAll(":scope > section, .hero-plain, .rak-hero, .workshops-hero, .craft-hero-intro").forEach((child) => {
      if (hasBg) child.style.setProperty("background-color", "transparent", "important");
      else child.style.removeProperty("background-color");
    });
  }} data-testid={`block-${props.i}-wrap`}>{el}</div>;
}

function TextBlock({ d, s, first, id }) {
  const head = <><Eyebrow text={d.eyebrow} ed={sx(s, "eyebrow")} />{d.heading && <H first={first} testid={`${id}-heading`} ed={sx(s, "heading")}>{d.heading}</H>}{d.subheading && <p className="subhead" {...sx(s, "subheading")}>{d.subheading}</p>}</>;
  const html = <Html html={d.body_html} testid={`${id}-body`} ed={sx(s, "body_html")} />;
  const body = d.link_label ? <div className="text-block-copy">{html}<div className="text-block-link">
    {d.link_href ? <Btn href={d.link_href} label={d.link_label} testid={`${id}-link`} ed={sx(s, "link_label")} /> : <><button type="button" className="more-link" disabled aria-describedby={`${id}-link-status`} data-testid={`${id}-link-pending`}><span {...sx(s, "link_label")}>{d.link_label}</span> <ArrowRight size={16} aria-hidden="true" /></button><SiteText name="film_pending" id={`${id}-link-status`} className="link-pending-note" data-testid={`${id}-link-status`} /></>}
  </div></div> : html;
  if (d.style === "stacked")
    return (
      <section className={`wrap section stacked ${d.aside ? "has-aside" : ""}`} data-testid={id}>
        <div>{head}{body}</div>
        {d.aside && <p className="aside-statement" data-testid={`${id}-aside`} {...sx(s, "aside")}>{d.aside}</p>}
      </section>
    );
  return (
    <section className="wrap section text-cols" data-testid={id}>
      <div className="text-cols-head">{head}</div>
      {body}
    </section>
  );
}

function BlockInner({ s, first, i, home, pageKey }) {
  const d = s.data || {};
  const t = s.type;
  const id = `block-${i}`;
  if (pageKey === "rakhigarhi" && t === "image_text" && d.layout === "haveli-reference") {
    return <HaveliRestoration data={d} id={id} editable={(field) => sx(s, field)} />;
  }
  if (t === "hero") return <section data-testid={id}><Hero d={d} s={s} first={first} i={i} home={home} pageKey={pageKey} /></section>;
  if (t === "text" && d.style === "statement")
    return (
      <section className="wrap section statement" data-testid={id}>
        {d.heading && <p className="eyebrow" {...sx(s, "heading")}>{d.heading}</p>}
        <Html html={d.body_html} testid={`${id}-body`} ed={sx(s, "body_html")} />
      </section>
    );
  if (t === "text") return <TextBlock d={d} s={s} first={first} id={id} />;
  if (t === "image_text")
    return (
      <section className={`wrap section split ${d.image_side === "right" ? "right" : ""}`} data-testid={id}>
        {d.collage?.length ? (
          <div className="collage" data-testid={`${id}-collage`}>
            {d.collage.map((c, k) => <Photo key={k} ref_={c} crop={c.crop} sizes="(min-width: 860px) 40vw, 100vw" className={`reveal collage-${c.slot || k}`} testid={`${id}-collage-${k}`} ed={sx(s, `collage.${k}`)} />)}
          </div>
        ) : (
          <Photo ref_={d.image} crop={d.crop} sizes="(min-width: 860px) 40vw, 100vw" testid={`${id}-image`} small={d.image?.size === "small"} className="reveal" ed={sx(s, "image")} />
        )}
        <div className="split-text"><Eyebrow text={d.eyebrow} ed={sx(s, "eyebrow")} />{d.heading && <H first={first} testid={`${id}-heading`} ed={sx(s, "heading")}>{d.heading}</H>}<Html html={d.body_html} testid={`${id}-body`} ed={sx(s, "body_html")} /></div>
      </section>
    );
  if (t === "image")
    return (
      <section className={`section image-block ${d.layout === "portrait" ? "wrap portrait" : "wrap"} ${d.flush ? "flush" : ""}`} data-testid={id}>
        <Eyebrow text={d.eyebrow} ed={sx(s, "eyebrow")} />
        {d.heading && <H first={first} testid={`${id}-heading`} ed={sx(s, "heading")}>{d.heading}</H>}
        <Photo ref_={d.image} crop={d.layout === "portrait" ? undefined : d.crop || "16/9"} cropMobile="4/3" sizes={d.layout === "portrait" ? "720px" : "(min-width: 1240px) 1160px, 100vw"} className="reveal" testid={`${id}-image`} ed={sx(s, "image")} />
        {d.body_html && <div className="image-body"><Html html={d.body_html} testid={`${id}-body`} ed={sx(s, "body_html")} /></div>}
      </section>
    );
  if (t === "gallery" && d.layout === "mosaic")
    return (
      <section className="mosaic-wrap section" data-testid={id}>
        <div className="wrap">{d.heading && <SectionHead s={s} first={first} heading={d.heading} intro={d.intro} testid={`${id}-heading`} />}</div>
        <div className="wrap wrap-wide mosaic">{(d.items || []).map((g, k) => <Photo key={k} ref_={g.image} crop={k === 0 ? "4/5" : "4/3"} sizes="(min-width: 860px) 45vw, 100vw" className={`reveal d${k + 1}`} testid={`${id}-image-${k}`} ed={sx(s, `items.${k}.image`)} />)}</div>
      </section>
    );
  if (t === "gallery")
    return (
      <section className="wrap section" data-testid={id}>
        {d.heading && <SectionHead s={s} first={first} heading={d.heading} testid={`${id}-heading`} />}
        <div className="gallery">{(d.items || []).map((g, k) => <Photo key={k} ref_={g.image} sizes="(min-width: 860px) 32vw, 100vw" className={`reveal d${(k % 3) + 1}`} testid={`${id}-image-${k}`} ed={sx(s, `items.${k}.image`)} />)}</div>
      </section>
    );
  if (t === "quote")
    return d.approved ? (
      <section className="wrap section" data-testid={id}>
        <blockquote className="pull-quote">
          <p>“<span {...sx(s, "quote")} data-testid={`${id}-quote`}>{d.quote}</span>”</p>
          {d.attribution && <footer>— <span {...sx(s, "attribution")} data-testid={`${id}-attribution`}>{d.attribution}</span></footer>}
        </blockquote>
      </section>
    ) : null;
  if (t === "video") {
    const posterEd = sx(s, "poster");
    return d.url ? (
      <section className="wrap section" data-testid={id}>
        {d.heading && <H first={first} ed={sx(s, "heading")} testid={`${id}-heading`}>{d.heading}</H>}
        <video controls preload="none" poster={d.poster?.media ? media(d.poster.media.src) : undefined} style={{ width: "100%", maxWidth: 960, ...posterEd.style }} ref={posterEd.ref} src={d.url} data-testid={`${id}-video`} data-edit="poster">
          <a href={d.url} data-testid={`${id}-watch`}><SiteText name="watch_video" /></a>
        </video>
        {d.caption && <p className="meta" {...sx(s, "caption")} data-testid={`${id}-caption`}>{d.caption}</p>}
        {d.transcript_html && <details><summary data-testid={`${id}-transcript-toggle`}><SiteText name="transcript" /></summary><Html html={d.transcript_html} ed={sx(s, "transcript_html")} testid={`${id}-transcript`} /></details>}
      </section>
    ) : null;
  }
  if (t === "related_work") return <section data-testid={id}><RelatedWork d={d} s={s} i={i} home={home} /></section>;
  if (t === "notes_feed")
    return (
      <section className="wrap section" data-testid={id}>
        <Eyebrow text={d.eyebrow} ed={sx(s, "eyebrow")} />
        <SectionHead s={s} columns={home} testid={`${id}-heading`} first={first} heading={d.heading} intro={home ? d.intro?.replace(/(along the way\.)\s+/, "$1\n\n") : d.intro} aside={!home && <Link to={d.category ? `/field-notes?category=${encodeURIComponent(d.category)}` : "/field-notes"} className="more-link" data-testid={`${id}-all-notes`}><span {...sx(s, "all_notes_label")}>{d.all_notes_label ?? "All Field Notes"}</span> <ArrowUpRight size={16} aria-hidden="true" /></Link>} />
        {d.cards?.length ? <NoteCards cards={d.cards} id={id} s={s} /> : <NoteList items={s.notes || []} />}
        {d.more_label && <Link to={d.more_href || "/field-notes"} className="more-link notes-more" data-testid={`${id}-more`}><span {...sx(s, "more_label")}>{d.more_label}</span> <ArrowRight size={14} aria-hidden="true" /></Link>}
      </section>
    );
  if (t === "download") {
    const items = (d.items || []).filter((x) => x.media);
    return items.length ? (
      <section className="wrap section" data-testid={id}>
        {d.heading && <H first={first} ed={sx(s, "heading")} testid={`${id}-heading`}>{d.heading}</H>}
        <ul>{(d.items || []).map((x, k) => x.media && <li key={k}><a href={media(`/api/media/${x.media.id}/file`)} data-testid={`${id}-download-${k}`}><Download size={16} aria-hidden="true" style={{ display: "inline" }} /> <span {...sx(s, `items.${k}.label`)}>{x.label || "Download"}</span></a></li>)}</ul>
      </section>
    ) : null;
  }
  if (t === "contact_invite")
    return (
      <section className="invite" data-testid={id}>
        <div className="wrap invite-inner">
          <div><Eyebrow text={d.eyebrow} ed={sx(s, "eyebrow")} />{d.heading && <H first={first} testid={`${id}-heading`} ed={sx(s, "heading")}>{d.heading}</H>}<p className="lede" data-testid={`${id}-description`} {...sx(s, "text")} style={{ margin: 0, ...sx(s, "text").style }}>{d.text}</p></div>
          <div className="invite-actions">
            {d.buttons?.filter((b) => b.label).length
              ? d.buttons.map((b, k) => b.label && <Btn key={k} href={b.href} label={b.label} ghost={k > 0} testid={`${id}-button-${k}`} ed={sx(s, `buttons.${k}.label`)} />)
              : <Btn href={d.href || "/connect"} label={d.button_label || "Connect with Us"} testid={`${id}-button`} ed={sx(s, "button_label")} />}
          </div>
        </div>
      </section>
    );
  if (t === "contact_form")
    return (
      <section className="wrap section text-cols" data-testid={id}>
        <div className="text-cols-head">{d.heading && <H first={first} ed={sx(s, "heading")} testid={`${id}-heading`}>{d.heading}</H>}{d.intro && <p {...sx(s, "intro")} data-testid={`${id}-intro`}>{d.intro}</p>}</div>
        <ContactForm />
      </section>
    );
  return null;
}

export function Blocks({ sections, home = false, pageKey }) {
  const visible = sections.filter((s) => !s.hidden);
  const render = (s, i) => <Block key={s.id || i} s={s} i={i} first={i === 0} home={home} pageKey={pageKey} />;
  if (pageKey !== "rakhigarhi") return visible.map(render);
  const result = [];
  let group = [];
  const flush = () => {
    if (group.length) result.push(<div className="rak-use-grid" data-testid={`rakhigarhi-use-grid-${result.length}`} key={`use-${group[0].key}`}>{group}</div>);
    group = [];
  };
  visible.forEach((s, i) => {
    if (s.data?.layout === "haveli-use") group.push(render(s, i));
    else { flush(); result.push(render(s, i)); }
  });
  flush();
  return result;
}
