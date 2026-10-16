import { useEffect } from "react";
import { loadFont, useSite } from "../../../lib/site";
import { useLiveEditor } from "./LiveEditorProvider";

export const DISPLAY_FIELDS = {
  "display.notes-title": "Field Notes list — titles", "display.notes-summary": "Field Notes list — summaries",
  "display.notes-meta": "Field Notes list — author & date", "display.notes-category": "Field Notes list — categories",
  "display.breadcrumb-current": "Current breadcrumb", "display.copyright": "Footer copyright",
  "display.note-dates": "Article publication details", "display.work-number": "Work item numbers",
  "display.notes-count": "Field Notes results count", "display.notes-search": "Field Notes search input", "display.notes-page": "Field Notes page numbers",
};
export const textSelector = (path, area) => `#public-site #${area === "main" ? "main" : `site-${area}`} [${path.startsWith("display.") ? "data-site-style" : "data-site-edit"}="${CSS.escape(path)}"]`;
export const SiteTextStyles = () => {
  const site = useSite();
  const { textStylePreview } = useLiveEditor();
  const entries = Object.fromEntries(Object.entries(site?.text_styles || {}).filter(([, entry]) => !textStylePreview || entry.path !== textStylePreview.path || entry.area !== textStylePreview.area));
  if (textStylePreview) entries.preview = textStylePreview;
  return <TextStyleTag entries={entries} />;
};
export const TextStyleTag = ({ entries, testid = "site-text-style-overrides" }) => {
  useEffect(() => { Object.values(entries || {}).forEach((entry) => loadFont(entry.styles?.fontFamily)); }, [entries]);
  const rules = Object.values(entries || {}).map(({ path, area, styles = {} }) => {
    if (!path || !["main", "header", "footer"].includes(area)) return "";
    const declarations = Object.entries(styles).filter(([key, value]) => ["fontFamily", "fontSize", "fontWeight", "color", "lineHeight"].includes(key) && /^[#0-9a-zA-Z .-]{1,80}$/.test(value))
      .map(([key, value]) => `${key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}: ${key === "fontFamily" ? `"${value}", sans-serif` : value} !important`).join(";");
    if (!declarations) return "";
    const target = textSelector(path, area);
    return `${target}, ${target} :is(p,span,a,strong,em,li,h2,h3,time) {${declarations}}`;
  }).join("\n");
  return rules ? <style data-testid={testid}>{rules}</style> : null;
};