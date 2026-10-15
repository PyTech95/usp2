import { useEffect, useMemo, useState } from "react";
import { Save, X, Images } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../../lib/api";
import { useSite, useRefreshSite } from "../../../lib/site";
import { useAuth } from "../../../lib/auth";
import { MediaPicker } from "../../admin/Kit";
import { useLiveEditor } from "./LiveEditorProvider";
import { UI_TEXT } from "./SiteText";
import { getPath } from "./editorFields";

export const SiteChromeEditor = () => {
  const { on, scope, setScope, registerDirty } = useLiveEditor();
  const { can } = useAuth();
  const site = useSite(), refresh = useRefreshSite();
  const [path, setPath] = useState("brand_label"), [value, setValue] = useState("");
  const [busy, setBusy] = useState(false), [picker, setPicker] = useState(false), [dirty, setDirty] = useState(false);
  const visible = on && scope === "site" && can("config");
  const chooseField = (next) => { if (!dirty || window.confirm("Discard unsaved text before selecting another field?")) setPath(next); };
  const fields = useMemo(() => {
    const out = ["brand_label", "site_name", "full_name", "tagline", "privacy_html", "contact.email", "contact.phone", "logo_media_id"];
    const menus = (items, prefix) => (items || []).forEach((item, i) => { out.push(`${prefix}.${i}.label`); menus(item.children, `${prefix}.${i}.children`); });
    menus(site?.menus?.main, "menus.main"); menus(site?.menus?.footer, "menus.footer");
    (site?.social || []).forEach((_, i) => out.push(`social.${i}.label`));
    return [...out, ...Object.keys(UI_TEXT).map((key) => `ui_text.${key}`), ...(site?.categories || []).map((category) => `ui_text.category_${category.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`)];
  }, [site]);
  useEffect(() => {
    setValue(path === "logo_media_id" ? site?.logo?.id || "" : getPath(site, path) ?? UI_TEXT[path.replace("ui_text.", "")] ?? "");
    setDirty(false);
  }, [path, site, visible]);
  useEffect(() => { registerDirty(visible && dirty, "site"); return () => registerDirty(false, "site"); }, [dirty, visible, registerDirty]);
  useEffect(() => {
    if (!visible) return undefined;
    const select = (event) => {
      if (event.target.closest(".live-ui,[role=dialog]")) return;
      const el = event.target.closest("[data-site-edit]");
      if (!el) return;
      event.preventDefault(); event.stopPropagation();
      chooseField(el.dataset.siteEdit);
    };
    document.body.classList.add("live-site-editing");
    document.addEventListener("click", select, true);
    return () => { document.body.classList.remove("live-site-editing"); document.removeEventListener("click", select, true); };
  }, [visible, dirty]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async (next = value) => {
    setBusy(true);
    try { await api.put("/admin/site-live", { path, value: next }); await refresh(); setDirty(false); registerDirty(false, "site"); toast.success("Site copy saved"); }
    catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  if (!visible) return null;
  return <aside className="live-ui live-panel live-site-panel" data-testid="live-site-panel">
    <div className="live-row live-top"><strong>Header, footer & shared text</strong><button className="live-btn" type="button" onClick={() => setScope("page")} aria-label="Close site text" data-testid="live-site-close"><X size={16} /></button></div>
    <label className="live-field">Field<select value={path} onChange={(e) => chooseField(e.target.value)} data-testid="live-site-field">{fields.map((field) => <option key={field} value={field}>{field}</option>)}</select></label>
    {path === "logo_media_id" ? <button type="button" className="live-btn" onClick={() => setPicker(true)} data-testid="live-site-logo"><Images size={16} /> Choose approved logo</button> : <label className="live-field">Text<textarea rows={path.endsWith("_html") ? 12 : 5} value={value} onChange={(e) => { setValue(e.target.value); setDirty(true); }} data-testid="live-site-value" /></label>}
    <button className="live-btn live-primary" type="button" disabled={busy || !dirty} onClick={() => save()} data-testid="live-site-save"><Save size={15} /> {busy ? "Saving…" : "Save site text"}</button>
    <MediaPicker open={picker} onClose={() => setPicker(false)} onPick={(m) => save(m.id)} />
  </aside>;
};