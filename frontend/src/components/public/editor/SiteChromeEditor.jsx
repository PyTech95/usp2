import { useEffect, useMemo, useState } from "react";
import { Save, X, Images, RotateCcw, PanelTop } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../../lib/api";
import { useSite, useRefreshSite } from "../../../lib/site";
import { useAuth } from "../../../lib/auth";
import { MediaPicker } from "../../admin/Kit";
import { useLiveEditor } from "./LiveEditorProvider";
import { UI_TEXT } from "./SiteText";
import { getPath } from "./editorFields";
import { ColorField, FONTS, px } from "./ColorField";
import { DISPLAY_FIELDS, textSelector } from "./TextStyleTag";

export const SiteChromeEditor = () => {
  const { on, scope, setScope, registerDirty, setTextStylePreview } = useLiveEditor();
  const { can } = useAuth();
  const site = useSite(), refresh = useRefreshSite();
  const [path, setPath] = useState("tagline"), [area, setArea] = useState("footer"), [value, setValue] = useState("");
  const [styles, setStyles] = useState({}), [currentSize, setCurrentSize] = useState("");
  const [busy, setBusy] = useState(false), [picker, setPicker] = useState(false), [dirty, setDirty] = useState(false), [error, setError] = useState("");
  const visible = on && scope === "site" && can("config");
  const chooseField = (next, location = area) => {
    if (next === path && location === area) return true;
    if (dirty && !window.confirm("Discard unsaved text and style changes?")) return false;
    setPath(next); setArea(location); return true;
  };
  const fields = useMemo(() => {
    const out = ["brand_label", "site_name", "full_name", "tagline", "privacy_html", "contact.email", "contact.phone", "logo_media_id"];
    const menus = (items, prefix) => (items || []).forEach((item, i) => { out.push(`${prefix}.${i}.label`); menus(item.children, `${prefix}.${i}.children`); });
    menus(site?.menus?.main, "menus.main"); menus(site?.menus?.footer, "menus.footer");
    (site?.social || []).forEach((_, i) => out.push(`social.${i}.label`));
    return [...out, ...Object.keys(UI_TEXT).map((key) => `ui_text.${key}`), ...(site?.categories || []).map((category) => `ui_text.category_${category.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`), ...Object.keys(DISPLAY_FIELDS)];
  }, [site]);
  useEffect(() => {
    setValue(path === "logo_media_id" ? site?.logo?.id || "" : getPath(site, path) ?? UI_TEXT[path.replace("ui_text.", "")] ?? "");
    setStyles(Object.values(site?.text_styles || {}).find((entry) => entry.path === path && entry.area === area)?.styles || {});
    setDirty(false); setError("");
    const element = document.querySelector(textSelector(path, area));
    setCurrentSize(element ? String(parseFloat(getComputedStyle(element).fontSize)) : "Default");
  }, [path, area, site, visible]);
  useEffect(() => { registerDirty(visible && dirty, "site"); return () => registerDirty(false, "site"); }, [dirty, visible, registerDirty]);
  useEffect(() => {
    if (visible) setTextStylePreview({ path, area, styles });
    return () => setTextStylePreview(null);
  }, [visible, path, area, styles, setTextStylePreview]);
  useEffect(() => {
    if (!on || !can("config") || scope === "header") return undefined;
    const select = (event) => {
      if (event.target.closest(".live-ui,[role=dialog]")) return;
      const el = event.target.closest("[data-site-edit],[data-site-style]");
      if (!el) return;
      if (el.closest("#site-header") && scope === "page") { event.preventDefault(); event.stopPropagation(); setScope("header"); return; }
      event.preventDefault(); event.stopPropagation();
      const location = el.closest("header.header") ? "header" : el.closest("footer.footer") ? "footer" : "main";
      if (chooseField(el.dataset.siteEdit || el.dataset.siteStyle, location)) setScope("site");
    };
    document.body.classList.toggle("live-site-editing", visible);
    document.addEventListener("click", select, true);
    return () => { document.body.classList.remove("live-site-editing"); document.removeEventListener("click", select, true); };
  }, [on, scope, visible, dirty, path, area]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async (next = value) => {
    setBusy(true); setError("");
    try { await api.put("/admin/site-live", { path, value: next, area, ...(path !== "logo_media_id" ? { styles } : {}) }); await refresh(); setDirty(false); registerDirty(false, "site"); toast.success("Text and style saved"); }
    catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };
  const style = (key, next) => { setStyles((s) => ({ ...s, [key]: next })); setDirty(true); };
  if (!visible) return null;
  return <aside className="live-ui live-panel live-site-panel" data-testid="live-site-panel" data-live-panel-ready="true">
    <div className="live-row live-top"><strong data-testid="live-site-title">Text &amp; typography</strong><button className="live-btn" type="button" onClick={() => setScope("page")} aria-label="Close site text" data-testid="live-site-close"><X size={16} /></button></div>
    <label className="live-field">Field<select value={path} onChange={(e) => chooseField(e.target.value)} data-testid="live-site-field">{fields.map((field) => <option key={field} value={field}>{DISPLAY_FIELDS[field] || field}</option>)}</select></label>
    <label className="live-field">Location<select value={area} onChange={(e) => chooseField(path, e.target.value)} data-testid="live-site-area"><option value="header">Header</option><option value="main">Page content</option><option value="footer">Footer</option></select></label>
    {path === "logo_media_id" ? <button type="button" className="live-btn" onClick={() => setPicker(true)} data-testid="live-site-logo"><Images size={16} /> Choose approved logo</button> : <>
      {!path.startsWith("display.") && <label className="live-field">Text<textarea rows={path.endsWith("_html") ? 8 : 3} value={value} onChange={(e) => { setValue(e.target.value); setDirty(true); }} data-testid="live-site-value" /></label>}
      <label className="live-field">Text size (px)<input type="number" min="8" max="200" value={px(styles.fontSize)} placeholder={currentSize} onChange={(e) => style("fontSize", e.target.value ? `${e.target.value}px` : "")} data-testid="live-site-font-size" /></label>
      <label className="live-field">Font<select value={styles.fontFamily || ""} onChange={(e) => style("fontFamily", e.target.value)} data-testid="live-site-font"><option value="">Default</option>{FONTS.map((f) => <option key={f}>{f}</option>)}</select></label>
      <ColorField label="Text colour" value={styles.color} onChange={(v) => style("color", v)} testid="live-site-color" fallback="#222222" />
      <button className="live-btn" type="button" onClick={() => { setStyles({}); setDirty(true); }} data-testid="live-site-reset-style"><RotateCcw size={14} /> Reset text style</button>
    </>}
    {error && <p role="alert" className="header-editor-error" data-testid="live-site-error">{error}</p>}
    <div className="live-row" style={{ marginTop: 14 }}><button className="live-btn live-primary" type="button" disabled={busy || !dirty} onClick={() => save()} data-testid="live-site-save"><Save size={15} /> {busy ? "Saving…" : "Save text & style"}</button></div>
    <button type="button" className="live-btn" onClick={() => setScope("header")} data-testid="live-site-open-header"><PanelTop size={15} /> Edit Header</button>
    <MediaPicker open={picker} onClose={() => setPicker(false)} onPick={(m) => save(m.id)} />
  </aside>;
};