import { Images, Trash2 } from "lucide-react";
import { media } from "../../../lib/api";

export const HeaderContentFields = ({ draft, change, chooseLogo }) => <div data-testid="header-content-fields">
  <div className="header-logo-preview" data-testid="header-logo-preview">
    {draft.logo ? <img src={media(draft.logo.src)} alt="Selected header logo" /> : <span>No logo selected</span>}
  </div>
  <div className="live-row">
    <button type="button" className="live-btn" onClick={chooseLogo} data-testid="header-logo-choose"><Images size={15} /> {draft.logo ? "Replace logo" : "Choose logo"}</button>
    {draft.logo && <button type="button" className="live-btn" title="Remove logo" aria-label="Remove logo" onClick={() => change({ logo: null, logo_media_id: "" })} data-testid="header-logo-remove"><Trash2 size={15} /></button>}
  </div>
  {[["brand_label", "Brand name", 120], ["full_name", "Brand subtitle", 240], ["mobile_menu_label", "Mobile menu label", 40]].map(([key, label, max]) =>
    <label className="live-field" key={key}>{label}<input value={draft[key]} maxLength={max} onChange={(e) => change({ [key]: e.target.value })} data-testid={`header-content-${key.replaceAll("_", "-")}`} /></label>)}
</div>;

export const flattenHeaderMenu = (items, prefix = "menus.main", depth = 0) => (items || []).flatMap((item, i) => {
  const path = `${prefix}.${i}`;
  return [{ ...item, path, depth }, ...flattenHeaderMenu(item.children, `${path}.children`, depth + 1)];
});

export const HeaderMenuFields = ({ menus, changeMenu }) => <div data-testid="header-menu-fields">
  {flattenHeaderMenu(menus.main).map((item) => <fieldset className="header-menu-item" key={item.path} data-testid={`header-menu-item-${item.id}`}>
    <legend>{item.depth > 0 ? "↳ " : ""}{item.label}</legend>
    <label className="live-field">Label<input value={item.label} maxLength={120} onChange={(e) => changeMenu(item.path, "label", e.target.value)} data-testid={`header-menu-label-${item.id}`} /></label>
    <label className="live-field">Link<input value={item.href} maxLength={500} onChange={(e) => changeMenu(item.path, "href", e.target.value)} data-testid={`header-menu-link-${item.id}`} /></label>
  </fieldset>)}
</div>;