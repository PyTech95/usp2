import { createContext, useContext, useEffect, useState } from "react";
import { api, media } from "./api";

const SiteCtx = createContext(null);
const SiteRefreshCtx = createContext(() => {});
export const PreviewCtx = createContext(false);
export const useSite = () => useContext(SiteCtx);
export const usePreview = () => useContext(PreviewCtx);
export const useRefreshSite = () => useContext(SiteRefreshCtx);
export const SitePreviewProvider = ({ site, children }) => <SiteCtx.Provider value={site}>{children}</SiteCtx.Provider>;

const SPACING = { compact: 0.75, comfortable: 1, airy: 1.3 };
const RADIUS = { square: "0px", soft: "4px", pill: "999px" };

export function applyTheme(theme, el = document.documentElement) {
  if (!theme) return;
  Object.entries(theme.colors || {}).forEach(([k, v]) => el.style.setProperty(`--c-${k}`, v));
  const f = theme.fonts || {};
  el.style.setProperty("--f-heading", `"${f.heading || "Public Sans"}", system-ui, sans-serif`);
  el.style.setProperty("--f-body", `"${f.body || "Public Sans"}", system-ui, sans-serif`);
  el.style.setProperty("--base", `${theme.base_size || 18}px`);
  el.style.setProperty("--space", SPACING[theme.spacing] || 1);
  el.style.setProperty("--btn-radius", RADIUS[theme.button_style] || "0px");
  [f.heading, f.body].forEach(loadFont);
}

export function loadFont(fam) {
  if (!fam || ["Lora", "Source Sans 3", "Public Sans"].includes(fam)) return;
  const id = `font-${fam.replace(/\s/g, "-")}`;
  if (document.getElementById(id)) return;
  const l = document.createElement("link");
  l.id = id;
  l.rel = "stylesheet";
  l.href = `https://fonts.googleapis.com/css2?family=${fam.replace(/\s/g, "+")}:wght@300;400;500;600;700&display=swap`;
  document.head.appendChild(l);
}

export function SiteProvider({ children }) {
  const [site, setSite] = useState(null);
  const refresh = () => api.get("/public/site").then((r) => { setSite(r.data); return r.data; });
  useEffect(() => {
    api.get("/public/site").then((r) => {
      if (!r.data || typeof r.data !== "object") return;
      setSite(r.data);
      if (r.data.theme) applyTheme(r.data.theme);
      if (r.data.favicon) {
        let l = document.querySelector("link[rel='icon']");
        if (!l) {
          l = document.createElement("link");
          l.rel = "icon";
          document.head.appendChild(l);
        }
        l.href = media(r.data.favicon.src);
      }
    });
  }, []);
  return <SiteRefreshCtx.Provider value={refresh}><SiteCtx.Provider value={site}>{children}</SiteCtx.Provider></SiteRefreshCtx.Provider>;
}

function setMeta(attr, key, val) {
  let m = document.head.querySelector(`meta[${attr}="${key}"]`);
  if (!m) {
    m = document.createElement("meta");
    m.setAttribute(attr, key);
    document.head.appendChild(m);
  }
  m.setAttribute("content", val || "");
}

export function useMeta({ title, description, canonical, noindex }) {
  const site = useSite();
  useEffect(() => {
    if (!title) return;
    document.title = title;
    setMeta("name", "description", description);
    setMeta("property", "og:title", title);
    setMeta("property", "og:description", description);
    setMeta("name", "robots", noindex || !site?.indexing_enabled ? "noindex, nofollow" : "index, follow");
    let l = document.head.querySelector("link[rel='canonical']");
    if (!l) {
      l = document.createElement("link");
      l.rel = "canonical";
      document.head.appendChild(l);
    }
    l.href = canonical || "";
  }, [title, description, canonical, noindex, site]);
}

export const SITE_URL = "https://www.uspindia.org";
