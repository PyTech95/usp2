import { createElement, useEffect, useRef, useState } from "react";

const REG = {};
import { Bold, Italic, Heading2, Heading3, List, ListOrdered, Quote, Link2, RemoveFormatting, Plus, Trash2, ArrowUp, ArrowDown, ImageIcon } from "lucide-react";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "../ui/dialog";
import { api, errMsg, media, fmtDateTime } from "../../lib/api";
import { useAuth } from "../../lib/auth";

export const PERM_LABEL = { pending: "Permission pending", approved: "Permission approved", restricted: "Restricted", withdrawn: "Withdrawn" };
export const AUTH_LABEL = { original: "Original", edited_original: "Edited original", ai_reference: "AI reference", unverified: "Unverified" };
export const EDIT_LABEL = { pending: "Edit pending", approved: "Edit approved", rejected: "Edit rejected" };

export const Tag = ({ tone = "neutral", children, testid }) => {
  const c = { ok: "bg-[#344C40] text-white", warn: "bg-[#F3E3C3] text-[#5a4210]", bad: "bg-[#9A4F36] text-white", neutral: "bg-[#EDE5D6] text-[#2D302B]" }[tone];
  return <span className={`inline-block text-xs font-semibold px-2 py-0.5 ${c}`} data-testid={testid}>{children}</span>;
};

export const PageHead = ({ title, desc, children }) => (
  <div className="flex flex-wrap items-end justify-between gap-4 mb-6 border-b pb-4">
    <div><h1 data-testid="admin-page-title">{title}</h1>{desc && <p className="text-sm text-muted-foreground mt-1 max-w-2xl">{desc}</p>}</div>
    <div className="flex flex-wrap gap-2">{children}</div>
  </div>
);

export const Field = ({ label, hint, id, children }) => (
  <div className="mb-4">
    <label htmlFor={id} className="block text-sm font-semibold mb-1">{label}</label>
    {children}
    {hint && <p className="text-xs text-muted-foreground mt-1">{hint}</p>}
  </div>
);

let uid = 0;
const useId = (p) => useRef(`${p}-${++uid}`).current;

export function TextIn({ label, value, onChange, hint, testid, type = "text", ...rest }) {
  const id = useId("t");
  return <Field label={label} hint={hint} id={id}><Input id={id} type={type} value={value ?? ""} onChange={(e) => onChange(type === "number" ? Number(e.target.value) : e.target.value)} data-testid={testid} {...rest} /></Field>;
}

export function AreaIn({ label, value, onChange, hint, testid, rows = 3 }) {
  const id = useId("a");
  return <Field label={label} hint={hint} id={id}><Textarea id={id} rows={rows} value={value ?? ""} onChange={(e) => onChange(e.target.value)} data-testid={testid} /></Field>;
}

export function SelectIn({ label, value, onChange, options, testid, hint }) {
  const id = useId("s");
  return (
    <Field label={label} id={id} hint={hint}>
      <select id={id} className="w-full h-10 border border-input bg-white px-2" value={value ?? ""} onChange={(e) => onChange(e.target.value)} data-testid={testid}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
      </select>
    </Field>
  );
}

export function CheckIn({ label, checked, onChange, testid }) {
  return (
    <label className="flex items-center gap-2 mb-3 text-sm cursor-pointer">
      <input type="checkbox" className="w-4 h-4" checked={!!checked} onChange={(e) => onChange(e.target.checked)} data-testid={testid} /> {label}
    </label>
  );
}

const TOOLS = [
  [Bold, "Bold", () => document.execCommand("bold")], [Italic, "Italic", () => document.execCommand("italic")],
  [Heading2, "Heading", () => document.execCommand("formatBlock", false, "h2")], [Heading3, "Subheading", () => document.execCommand("formatBlock", false, "h3")],
  [List, "Bulleted list", () => document.execCommand("insertUnorderedList")], [ListOrdered, "Numbered list", () => document.execCommand("insertOrderedList")],
  [Quote, "Quotation", () => document.execCommand("formatBlock", false, "blockquote")],
  [Link2, "Link", () => { const u = window.prompt("Link address (https://… or /page)"); if (u) document.execCommand("createLink", false, u); }],
  [RemoveFormatting, "Plain paragraph", () => { document.execCommand("removeFormat"); document.execCommand("formatBlock", false, "p"); }],
];

export function RichText({ label, value, onChange, testid }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current && ref.current.innerHTML !== (value || "")) ref.current.innerHTML = value || "";
  }, [value]);
  return (
    <div className="mb-4">
      <span className="block text-sm font-semibold mb-1">{label}</span>
      <div className="flex flex-wrap gap-1 border border-b-0 border-input bg-[#F6F1E8] p-1" role="toolbar" aria-label={`${label} formatting`}>
        {TOOLS.map(([Icon, name, fn]) => (
          <button key={name} type="button" title={name} aria-label={name} className="p-2 hover:bg-white focus-visible:bg-white"
            onMouseDown={(e) => e.preventDefault()} onClick={() => { ref.current.focus(); fn(); onChange(ref.current.innerHTML); }}>
            <Icon size={16} aria-hidden="true" />
          </button>
        ))}
      </div>
      <div ref={ref} className="rt-editor" contentEditable suppressContentEditableWarning role="textbox" aria-multiline="true" aria-label={label}
        onInput={(e) => onChange(e.currentTarget.innerHTML)} data-testid={testid} />
    </div>
  );
}

export function MediaPicker({ open, onClose, onPick, kind = "image" }) {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  useEffect(() => {
    if (open) api.get("/admin/media", { params: { q, kind } }).then((r) => setItems(r.data));
  }, [open, q, kind]);
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="media-picker-dialog max-w-4xl max-h-[85vh] overflow-y-auto" data-testid="media-picker-dialog">
        <DialogHeader><DialogTitle>Choose from the Media Library</DialogTitle>
          <DialogDescription>Only items with an eligible source, approved permission and approved edit appear publicly. Others show only in private preview.</DialogDescription></DialogHeader>
        <Input placeholder="Search filename, caption, credit…" value={q} onChange={(e) => setQ(e.target.value)} data-testid="media-picker-search" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
          {items.map((m) => (
            <button key={m.id} type="button" className="text-left border hover:border-[#344C40] focus-visible:border-[#344C40] p-1" onClick={() => { onPick(m); onClose(); }} data-testid={`media-pick-${m.id}`}>
              {m.thumb ? <img src={media(m.thumb)} alt="" className="w-full h-28 object-contain bg-[#EDE5D6]" /> : <div className="h-28 flex items-center justify-center bg-[#EDE5D6] text-xs">{m.format}</div>}
              <span className="block text-xs truncate mt-1">{m.filename}</span>
              <Tag tone={m.public_ok ? "ok" : "warn"}>{m.public_ok ? "Public OK" : "Not public"}</Tag>
            </button>
          ))}
          {!items.length && <p className="text-sm col-span-4">No matching media.</p>}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export function ImageField({ label = "Photograph", value, onChange, testid }) {
  const [open, setOpen] = useState(false);
  const [info, setInfo] = useState(null);
  const v = value || {};
  useEffect(() => {
    if (v.media_id) api.get(`/admin/media/${v.media_id}`).then((r) => setInfo(r.data)).catch(() => setInfo(null));
    else setInfo(null);
  }, [v.media_id]);
  const set = (k, val) => onChange({ ...v, [k]: val });
  return (
    <div className="mb-4 border border-dashed p-3 bg-white">
      <span className="block text-sm font-semibold mb-2">{label}</span>
      <div className="flex gap-3 items-start flex-wrap">
        {info?.thumb ? <img src={media(info.thumb)} alt="" className="w-32 h-24 object-contain bg-[#EDE5D6]" /> : <div className="w-32 h-24 bg-[#EDE5D6] flex items-center justify-center"><ImageIcon size={20} aria-hidden="true" /></div>}
        <div className="flex-1 min-w-[200px]">
          {info && <p className="text-xs mb-1">{info.filename} · {info.width}×{info.height} <Tag tone={info.public_ok ? "ok" : "warn"}>{info.public_ok ? "Public OK" : "Not approved for public"}</Tag></p>}
          <div className="flex gap-2 mb-2">
            <Button type="button" size="sm" variant="outline" onClick={() => setOpen(true)} data-testid={testid ? `${testid}-choose` : undefined}>{v.media_id ? "Replace" : "Choose"}</Button>
            {v.media_id && <Button type="button" size="sm" variant="ghost" onClick={() => onChange({ media_id: "", caption: v.caption || "" })}>Remove</Button>}
          </div>
          <Input aria-label="Caption for this placement" placeholder="Caption for this placement (blank = library caption)" value={v.caption || ""} onChange={(e) => set("caption", e.target.value)} className="mb-2" data-testid={testid ? `${testid}-caption` : undefined} />
          <details className="text-sm">
            <summary className="cursor-pointer">Placement options (this page only)</summary>
            <div className="grid grid-cols-2 gap-2 mt-2">
              <Input aria-label="Alt text override" placeholder="Alt text override" value={v.alt || ""} onChange={(e) => set("alt", e.target.value)} className="col-span-2" />
              <SelectIn label="Display size" value={v.size || "large"} onChange={(x) => set("size", x)} options={[["large", "Large (natural ratio)"], ["small", "Small module (low-resolution sources)"]]} />
              <CheckIn label="Hide “view original photograph” link (edited versions only)" checked={v.hide_original} onChange={(x) => set("hide_original", x)} />
              <div className="text-xs text-muted-foreground self-center col-span-2">Photos display uncropped at their natural ratio. Focal points apply only where a layout crops (e.g. Field Note cards).</div>
            </div>
          </details>
        </div>
      </div>
      <MediaPicker open={open} onClose={() => setOpen(false)} onPick={(m) => onChange({ ...v, media_id: m.id })} />
    </div>
  );
}

export function FileField({ label = "File", value, onChange }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mb-3">
      <span className="block text-sm font-semibold mb-1">{label}</span>
      <div className="flex gap-2 items-center"><span className="text-xs truncate">{value || "None selected"}</span>
        <Button type="button" size="sm" variant="outline" onClick={() => setOpen(true)}>Choose PDF</Button></div>
      <MediaPicker open={open} kind="file" onClose={() => setOpen(false)} onPick={(m) => onChange(m.id)} />
    </div>
  );
}

export function FieldsFor({ schema, data, onChange, prefix }) {
  const set = (k) => (v) => onChange({ ...data, [k]: v });
  return schema.map(([k, type, label]) => {
    const L = label || k.replace(/_html$/, "").replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
    const tid = `${prefix}-${k}`;
    if (type === "text") return <TextIn key={k} label={L} value={data[k]} onChange={set(k)} testid={tid} />;
    if (type === "number") return <TextIn key={k} type="number" label={L} value={data[k]} onChange={set(k)} testid={tid} />;
    if (type === "textarea") return <AreaIn key={k} label={L} value={data[k]} onChange={set(k)} testid={tid} />;
    if (type === "rich") return <RichText key={k} label={L} value={data[k]} onChange={set(k)} testid={tid} />;
    if (type === "image") return <ImageField key={k} label={L} value={data[k]} onChange={set(k)} testid={tid} />;
    if (type === "file") return <FileField key={k} label={L} value={data[k]} onChange={set(k)} />;
    if (type === "bool") return <CheckIn key={k} label={L} checked={data[k]} onChange={set(k)} testid={tid} />;
    if (type.startsWith("select:")) return <SelectIn key={k} label={L} value={data[k]} onChange={set(k)} options={type.slice(7).split(",").map((o) => [o, o])} testid={tid} />;
    if (type.startsWith("list:")) return createElement(REG.Repeater, { key: k, label: L, items: data[k] || [], onChange: set(k), fields: LISTS[type.slice(5)], testid: tid });
    return null;
  });
}

export const LISTS = {
  links: [["label", "text", "Button label"], ["href", "text", "Link address"]],
  gallery: [["image", "image"]],
  work: [["title", "text"], ["subtitle", "text", "Heading line"], ["text", "textarea"], ["href", "text", "Link address"], ["image", "image"]],
  downloads: [["label", "text"], ["media_id", "file", "PDF file"]],
  references: [["text", "text", "Reference"], ["url", "text", "Source URL (optional)"]],
};

export function Repeater({ label, items, onChange, fields, testid }) {
  const move = (i, d) => { const a = [...items]; [a[i], a[i + d]] = [a[i + d], a[i]]; onChange(a); };
  return (
    <div className="mb-4">
      <span className="block text-sm font-semibold mb-1">{label}</span>
      {items.map((it, i) => (
        <div key={i} className="border p-3 mb-2 bg-[#FCFAF6]">
          <div className="flex justify-end gap-1 mb-1">
            <Button type="button" size="icon" variant="ghost" aria-label="Move item up" disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp size={14} /></Button>
            <Button type="button" size="icon" variant="ghost" aria-label="Move item down" disabled={i === items.length - 1} onClick={() => move(i, 1)}><ArrowDown size={14} /></Button>
            <Button type="button" size="icon" variant="ghost" aria-label="Remove item" onClick={() => onChange(items.filter((_, j) => j !== i))}><Trash2 size={14} /></Button>
          </div>
          <FieldsFor schema={fields} data={it} prefix={`${testid}-${i}`} onChange={(v) => onChange(items.map((x, j) => (j === i ? v : x)))} />
        </div>
      ))}
      <Button type="button" size="sm" variant="outline" onClick={() => onChange([...items, {}])} data-testid={`${testid}-add`}><Plus size={14} /> Add item</Button>
    </div>
  );
}

REG.Repeater = Repeater;

export function SeoFields({ seo, onChange, path, fallbackTitle }) {
  const s = seo || {};
  const set = (k) => (v) => onChange({ ...s, [k]: v });
  const title = s.title || fallbackTitle;
  return (
    <div>
      <TextIn label="Search & social title" value={s.title} onChange={set("title")} hint={`Leave blank to use “${fallbackTitle}”. ${title.length} characters (results often shorten above ~60).`} testid="seo-title" />
      <AreaIn label="Search description" value={s.description} onChange={set("description")} hint={`${(s.description || "").length} characters (aim for 50–160).`} testid="seo-description" />
      <TextIn label="Canonical URL override" value={s.canonical} onChange={set("canonical")} hint="Optional. Must start with https://www.uspindia.org/" testid="seo-canonical" />
      <CheckIn label="Hide from search engines (noindex, excluded from sitemap)" checked={s.noindex} onChange={set("noindex")} testid="seo-noindex" />
      <ImageField label="Sharing image (blank = main photograph)" value={{ media_id: s.share_media_id }} onChange={(v) => set("share_media_id")(v.media_id || "")} />
      <div className="border p-3 bg-white" aria-label="Approximate search result preview">
        <p className="text-xs text-muted-foreground mb-1">Approximate search preview — actual appearance is decided by search engines.</p>
        <p className="text-xs text-[#344C40]">www.uspindia.org{path}</p>
        <p className="text-lg text-[#1a0dab] leading-tight">{title}</p>
        <p className="text-sm">{s.description || <em>No description yet.</em>}</p>
      </div>
    </div>
  );
}

export function ReviewPanel({ entityType, entityId, onRestored, reloadKey }) {
  const { can } = useAuth();
  const [revs, setRevs] = useState([]);
  const [comments, setComments] = useState([]);
  const [text, setText] = useState("");
  const load = () => {
    api.get("/admin/revisions", { params: { entity_type: entityType, entity_id: entityId } }).then((r) => setRevs(r.data));
    api.get("/admin/comments", { params: { entity_type: entityType, entity_id: entityId } }).then((r) => setComments(r.data));
  };
  useEffect(load, [entityType, entityId, reloadKey]);
  const comment = async (verdict) => {
    try { await api.post("/admin/comments", { entity_type: entityType, entity_id: entityId, text, verdict }); setText(""); load(); toast.success("Review note saved"); }
    catch (e) { toast.error(errMsg(e)); }
  };
  const restore = async (id) => {
    if (!window.confirm("Restore this revision into the draft? The public page will not change until you publish.")) return;
    try { await api.post(`/admin/revisions/${id}/restore`); toast.success("Revision restored to draft"); onRestored(); load(); }
    catch (e) { toast.error(errMsg(e)); }
  };
  return (
    <div className="space-y-6">
      <section>
        <h2 className="font-semibold mb-2">Client review</h2>
        <Textarea value={text} onChange={(e) => setText(e.target.value)} placeholder="Comment for the editors" aria-label="Review comment" data-testid="review-comment-input" />
        <div className="flex flex-wrap gap-2 mt-2">
          <Button size="sm" variant="outline" onClick={() => comment("comment")} data-testid="review-comment-btn">Comment</Button>
          <Button size="sm" onClick={() => comment("approve")} data-testid="review-approve-btn">Approve</Button>
          <Button size="sm" variant="outline" onClick={() => comment("changes")} data-testid="review-changes-btn">Request changes</Button>
        </div>
        <ul className="mt-3 space-y-2" data-testid="review-comments">
          {comments.map((c) => (
            <li key={c.id} className="border-l-2 pl-2 text-sm border-[#9A4F36]">
              <Tag tone={c.verdict === "approve" ? "ok" : c.verdict === "changes" ? "bad" : "neutral"}>{c.verdict === "approve" ? "Approved" : c.verdict === "changes" ? "Changes requested" : "Comment"}</Tag>{" "}
              <span className="text-xs">{c.by_name || c.by} ({c.role}) · {fmtDateTime(c.created_at)}</span>
              {c.text && <p>{c.text}</p>}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h2 className="font-semibold mb-2">Revision history</h2>
        <ul className="space-y-1 max-h-80 overflow-y-auto" data-testid="revision-list">
          {revs.map((r) => (
            <li key={r.id} className="flex justify-between gap-2 text-sm border-b py-1">
              <span>{r.action}<br /><span className="text-xs text-muted-foreground">{fmtDateTime(r.created_at)} · {r.by}</span></span>
              {(can("content.edit") || can("notes.draft")) && <Button size="sm" variant="ghost" onClick={() => restore(r.id)} data-testid={`revision-restore-${r.id}`}>Restore</Button>}
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
