import { useEffect, useRef, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { ChevronDown, Menu, X } from "lucide-react";
import { useSite, PreviewCtx } from "../../lib/site";
import { media } from "../../lib/api";
import { LiveEditorProvider } from "./editor/LiveEditorProvider";
import { SiteChromeEditor } from "./editor/SiteChromeEditor";
import { SiteText } from "./editor/SiteText";

function Dropdown({ item, onNavigate }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const loc = useLocation();
  useEffect(() => setOpen(false), [loc.pathname, loc.hash]);
  useEffect(() => {
    const close = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false);
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  const active = loc.pathname.startsWith(item.href);
  const hover = () => window.matchMedia("(hover: hover) and (pointer: fine) and (min-width: 961px)").matches;
  return (
    <li ref={ref} style={{ position: "relative" }} onMouseEnter={() => hover() && setOpen(true)} onMouseLeave={() => hover() && setOpen(false)}
      onKeyDown={(e) => e.key === "Escape" && (setOpen(false), ref.current.querySelector("button").focus())}>
      <span style={{ display: "inline-flex" }}>
        <Link to={item.href} className="nav-link" aria-current={active ? "page" : undefined} onClick={onNavigate} data-testid={`nav-${item.id}`}><SiteText path={item.editPath}>{item.label}</SiteText></Link>
        <button type="button" className="nav-link" style={{ padding: "0 .5rem" }} aria-expanded={open} aria-label={`${item.label} submenu`}
          onClick={() => setOpen((o) => !o)} data-testid={`nav-${item.id}-toggle`}>
          <ChevronDown size={16} aria-hidden="true" style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform .18s" }} />
        </button>
      </span>
      {open && (
        <ul className={`dropdown ${item.children.some((c) => c.children?.length) ? "mega" : ""}`} data-testid={`nav-${item.id}-menu`}>
          {item.children.map((c, ci) => (
            <li key={c.id} className={c.children?.length ? "mega-col" : undefined}>
              <Link to={c.href} onClick={onNavigate} className={c.children?.length ? "mega-head" : undefined} data-testid={`nav-${c.id}`}><SiteText path={`${item.editPath.replace(/\.label$/, "")}.children.${ci}.label`}>{c.label}</SiteText></Link>
              {c.children?.length > 0 && (
                <ul>{c.children.map((g, gi) => <li key={g.id}><Link to={g.href} onClick={onNavigate} data-testid={`nav-${g.id}`}><SiteText path={`${item.editPath.replace(/\.label$/, "")}.children.${ci}.children.${gi}.label`}>{g.label}</SiteText></Link></li>)}</ul>
              )}
            </li>
          ))}
        </ul>
      )}
    </li>
  );
}

function Header({ site }) {
  const [open, setOpen] = useState(false);
  const close = () => setOpen(false);
  return (
    <header className="header">
      <div className="wrap header-inner">
        <Link to="/" className="brand" data-testid="brand-link">
          {site?.logo && <img src={media(site.logo.src)} alt="" width={site.logo.width} height={site.logo.height} style={{ height: 44, width: "auto" }} data-site-edit="logo_media_id" data-testid="header-logo" />}
          <span><SiteText path="brand_label" className="brand-name" data-testid="header-brand-name" fallback="USP" /><SiteText path="full_name" className="brand-sub" data-testid="header-brand-subtitle" /></span>
        </Link>
        <nav aria-label="Main">
          <button type="button" className="nav-link menu-toggle" aria-expanded={open} aria-controls="main-menu" onClick={() => setOpen(!open)} data-testid="mobile-menu-toggle">
            {open ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />} <SiteText name="menu" />
          </button>
          <ul id="main-menu" className={`nav-list ${open ? "open" : ""}`}>
            {(site?.menus?.main || []).map((i, index) =>
              i.children?.length ? <Dropdown key={i.id} item={{ ...i, editPath: `menus.main.${index}.label` }} onNavigate={close} /> : (
                <li key={i.id}><NavLink to={i.href} end={i.href === "/"} className="nav-link" onClick={close} data-testid={`nav-${i.id}`}><SiteText path={`menus.main.${index}.label`}>{i.label}</SiteText></NavLink></li>
              )
            )}
          </ul>
        </nav>
      </div>
    </header>
  );
}

function Footer({ site }) {
  return (
    <footer className="footer" data-testid="site-footer">
      <div className="wrap footer-top">
        <div>
          <SiteText as="p" path="brand_label" fallback="USP" className="footer-brand" data-testid="footer-brand-name" />
          <SiteText as="p" path="full_name" className="footer-sub" data-testid="footer-brand-subtitle" />
        </div>
        <nav aria-label="Footer" className="footer-nav">
          {(site?.menus?.main || []).map((i, index) => i.href !== "/" && <Link key={i.id} to={i.href} data-testid={`footer-link-${i.id}`}><SiteText path={`menus.main.${index}.label`}>{i.label}</SiteText></Link>)}
        </nav>
        {site?.tagline && <SiteText as="p" path="tagline" className="footer-tagline" data-testid="footer-tagline" />}
      </div>
      <div className="wrap footer-bottom">
        <span data-testid="footer-copyright">© {new Date().getFullYear()} <SiteText path="site_name" /></span>
        {site?.contact?.email && <a href={`mailto:${site.contact.email}`} data-testid="footer-email"><SiteText path="contact.email" /></a>}
        {site?.contact?.phone && <SiteText path="contact.phone" data-testid="footer-phone" />}
        {(site?.social || []).map((s, i) => <a key={s.url} href={s.url} rel="noopener noreferrer" data-testid={`footer-social-${i}`}><SiteText path={`social.${i}.label`}>{s.label}</SiteText></a>)}
        {(site?.menus?.footer || []).map((f, i) => <a key={f.id || f.href} href={f.href} data-testid={`footer-menu-${f.id || f.label.toLowerCase()}`}><SiteText path={`menus.footer.${i}.label`}>{f.label}</SiteText></a>)}
        <details data-testid="footer-privacy" className="footer-privacy">
          <summary style={{ cursor: "pointer" }} data-testid="footer-privacy-toggle"><SiteText name="privacy" /></summary>
          <div data-site-edit="privacy_html" data-testid="footer-privacy-body" dangerouslySetInnerHTML={{ __html: site?.privacy_html || "" }} />
        </details>
      </div>
    </footer>
  );
}

function useHashScroll() {
  const { pathname, hash } = useLocation();
  useEffect(() => {
    if (!hash) return;
    let tries = 0;
    const t = setInterval(() => {
      const el = document.getElementById(decodeURIComponent(hash.slice(1)));
      if (el || ++tries > 30) {
        clearInterval(t);
        el?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    }, 100);
    return () => clearInterval(t);
  }, [pathname, hash]);
}

export default function PublicLayout({ preview = false }) {
  const site = useSite();
  useHashScroll();
  return (
    <PreviewCtx.Provider value={preview}><LiveEditorProvider preview={preview}>
      <div className="site">
        <a href="#main" className="skip" data-testid="skip-to-content"><SiteText name="skip" /></a>
        {(preview || site?.preview_banner) && (
          <div className="preview-banner" data-testid="preview-banner" role="note">
            <div className="wrap">{preview ? "Private draft preview — not visible to the public. Unapproved photographs are flagged." : "Private preview — content marked “Draft placeholder” is awaiting client approval."}</div>
          </div>
        )}
        <Header site={site} />
        <main id="main" tabIndex={-1}><Outlet /></main>
        <Footer site={site} />
        <SiteChromeEditor />
      </div>
    </LiveEditorProvider></PreviewCtx.Provider>
  );
}
