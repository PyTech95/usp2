import { editableFields, getPath, isImageField } from "./editorFields";

export const FieldInspector = ({ sections, selected, onSelect, onChange, title, onTitleChange }) => {
  const section = sections.find((s) => s.id === selected?.sec);
  const path = selected?.field;
  const value = section && path && (getPath(section.data, path) ?? document.querySelector(`[data-sec="${CSS.escape(section.id)}"] [data-edit="${CSS.escape(path)}"]`)?.innerText);
  const listed = section && editableFields(section.data).some((f) => f.path === path);
  return <div className="live-field-inspector" data-testid="live-field-inspector">
    {onTitleChange && <label className="live-field">Page title<input value={title || ""} onChange={(e) => onTitleChange(e.target.value)} data-testid="live-page-title" /></label>}
    <label className="live-field">All page fields<select value={selected ? `${selected.sec}|${path}` : ""} onChange={(e) => { const [sec, field] = e.target.value.split("|"); if (sec) onSelect({ sec, field }); }} data-testid="live-field-selector">
      <option value="">Select text, label, link or image</option>
      {selected && path !== "_section" && !listed && <option value={`${selected.sec}|${path}`}>{path}</option>}
      {sections.map((s, i) => <optgroup key={s.id} label={`${i + 1}. ${s.data?.eyebrow || s.data?.heading || s.type}${s.hidden ? " (hidden)" : ""}`}>
        <option value={`${s.id}|_section`}>Whole section</option>
        {editableFields(s.data).map((f) => <option key={f.path} value={`${s.id}|${f.path}`}>{f.path}{f.kind === "image" ? " — image" : ""}</option>)}
      </optgroup>)}
    </select></label>
    {section && path && path !== "_section" && !isImageField(path) && <label className="live-field">{path.endsWith("_html") ? "Text / HTML" : "Text or link"}<textarea rows={path.endsWith("_html") ? 8 : 3} value={typeof value === "string" ? value : ""} onChange={(e) => onChange(section.id, path, e.target.value)} data-testid="live-field-value" /></label>}
  </div>;
};