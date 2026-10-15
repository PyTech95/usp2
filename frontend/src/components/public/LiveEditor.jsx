import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import {
  Pencil, X, Save, Upload, Images, RotateCcw, AlignLeft, AlignCenter, AlignRight,
  ArrowUp, ArrowDown, Copy, Trash2, Eye, EyeOff, Plus, Undo2, Redo2, Bold, Italic,
  Monitor, Tablet, Smartphone, Type, Paintbrush, Square, LayoutGrid, GripVertical,
  ArrowLeft, ArrowRight,
} from "lucide-react";
import { api, errMsg } from "../../lib/api";
import { MediaPicker } from "../admin/Kit";
import { useLiveEditor } from "./editor/LiveEditorProvider";
import { FieldInspector } from "./editor/FieldInspector";
import { isImageField } from "./editor/editorFields";

export const FONTS = ["Public Sans", "Lora", "Source Serif 4", "Libre Baskerville", "Source Sans 3", "Noto Sans",
  "Atkinson Hyperlegible", "Cormorant", "Literata", "Playfair Display", "Merriweather", "DM Serif Display",
  "Montserrat", "Poppins", "Raleway", "Work Sans"];

const LABELS = { eyebrow: "Small label", heading: "Heading", subheading: "Sub-heading", intro: "Intro text",
  body_html: "Body text", aside: "Side statement", text: "Text", image: "Image", _section: "Whole section" };
function labelFor(field) {
  if (!field) return "";
  if (LABELS[field]) return LABELS[field];
  if (/^collage\.\d+$/.test(field)) return `Photograph ${Number(field.split(".")[1]) + 1}`;
  const m = field.match(/^(items|cards)\.(\d+)\.(\w+)$/);
  if (m) {
    const kind = m[1] === "items" ? "Card" : "Note card";
    const sub = { title: "Title", subtitle: "Subtitle", text: "Text", eyebrow: "Small label" }[m[3]] || m[3];
    return `${kind} ${Number(m[2]) + 1} — ${sub}`;
  }
  return field;
}
const TEXT_FIELDS = ["eyebrow", "heading", "subheading", "intro", "body_html", "aside", "text"];
const ADD_TYPES = [
  ["text", "Text", Type], ["image_text", "Image + text", LayoutGrid], ["image", "Big image", Images],
  ["gallery", "Gallery", LayoutGrid], ["quote", "Quote", Square], ["contact_invite", "Call to action", Plus],
  ["hero", "Hero banner", Square],
];
const px = (v) => (v ? parseInt(v, 10) : "");
const newId = () => Math.random().toString(36).slice(2, 12);
const clone = (o) => JSON.parse(JSON.stringify(o));
const getPath = (obj, path) => path.split(".").reduce((o, k) => (o == null ? o : o[k]), obj);
const setPath = (obj, path, val) => {
  const keys = path.split(".");
  const root = Array.isArray(obj) ? [...obj] : { ...obj };
  let cur = root;
  for (let i = 0; i < keys.length - 1; i++) {
    const k = keys[i];
    cur[k] = Array.isArray(cur[k]) ? [...cur[k]] : { ...(cur[k] || {}) };
    cur = cur[k];
  }
  cur[keys[keys.length - 1]] = val;
  return root;
};
const findSecEl = (id) => (id ? document.querySelector(`main [data-sec="${CSS.escape(id)}"]`) : null);
const findEl = (sel) => {
  const s = findSecEl(sel?.sec);
  if (!s) return null;
  return sel.field === "_section" ? s : s.querySelector(`[data-edit="${sel.field}"]`);
};

const DEFAULTS = {
  text: { heading: "New heading", body_html: "<p>New paragraph. Click to edit this text.</p>", style: "stacked" },
  image_text: { heading: "Heading", body_html: "<p>Describe this section.</p>", image: { media_id: "" }, image_side: "left" },
  image: { image: { media_id: "" }, layout: "full", body_html: "" },
  gallery: { heading: "Gallery", items: [] },
  quote: { quote: "A short, approved quotation.", attribution: "", approved: true },
  contact_invite: { heading: "Work with us", text: "A short invitation to get in touch.", button_label: "Connect with Us", href: "/connect", buttons: [] },
  hero: { eyebrow: "", heading: "New heading", intro: "Short introduction text.", image: { media_id: "" }, buttons: [] },
};
const makeSection = (type) => ({ id: newId(), type, hidden: false, data: clone(DEFAULTS[type] || {}), styles: {} });
const stripMedia = (o) => {
  if (Array.isArray(o)) return o.map(stripMedia);
  if (o && typeof o === "object") return Object.fromEntries(Object.entries(o).filter(([k]) => !["media", "original", "edit_note"].includes(k)).map(([k, v]) => [k, stripMedia(v)]));
  return o;
};

export function LiveEditor(props) {
  // Permission/mode is centralized in the layout provider. Keep the local state
  // mounted through logout so its closing effect can discard unsaved content.
  if (!props.content) return null;
  return <Editor key={props.pageKey} {...props} />;
}

function Editor({ pageKey, content, setContent, original, remount, noteId }) {
  const { on, setOn, scope, registerDirty } = useLiveEditor();
  const [sel, setSel] = useState(null);
  const [dirty, setDirty] = useState(false);
  const [base, setBase] = useState(original);
  const [busy, setBusy] = useState(false);
  const [picker, setPicker] = useState(false);
  const [addAt, setAddAt] = useState(null);
  const [rect, setRect] = useState(null);
  const [device, setDevice] = useState("desktop");
  const [hist, setHist] = useState({ past: [], future: [] });
  const [pos, setPos] = useState(null);
  const [panelTop, setPanelTop] = useState(132);
  const [guides, setGuides] = useState([]);
  const fileRef = useRef(null);
  const inlineDraft = useRef(null);

  const sections = content.sections;
  const sec = sel && sections.find((s) => s.id === sel.sec);
  const field = sel?.field;
  const st = (sec?.styles || {})[field] || {};
  const isImage = isImageField(field);
  const isText = !!field && field !== "_section" && !isImage;
  const selEl = on && sel ? findEl(sel) : null;
  const cstyle = selEl ? window.getComputedStyle(selEl) : null;
  const padPH = (p) => (cstyle ? String(Math.round(parseFloat(cstyle[p]) || 0)) : "0");

  const commit = useCallback((nextSections, mark = true) => {
    setHist((h) => ({ past: [...h.past, content].slice(-50), future: [] }));
    setContent((c) => ({ ...c, sections: nextSections }));
    if (mark) setDirty(true);
  }, [content, setContent]);

  const patchSec = (id, fn) => commit(sections.map((s) => (s.id === id ? fn(s) : s)));
  const selectField = (next) => {
    const draft = inlineDraft.current;
    if (draft) {
      inlineDraft.current = null;
      patchSec(draft.sec, (s) => ({ ...s, data: setPath(s.data, draft.field, draft.value) }));
    }
    setSel(next);
  };
  const setStyles = (patch) => {
    if (!sel) return;
    patchSec(sel.sec, (s) => {
      const f = { ...((s.styles || {})[field] || {}), ...patch };
      Object.keys(f).forEach((k) => (f[k] === "" || f[k] == null) && delete f[k]);
      return { ...s, styles: { ...(s.styles || {}), [field]: f } };
    });
  };

  const undo = () => setHist((h) => {
    if (!h.past.length) return h;
    const prev = h.past[h.past.length - 1];
    setContent(prev); setDirty(true); remount();
    return { past: h.past.slice(0, -1), future: [content, ...h.future].slice(0, 50) };
  });
  const redo = () => setHist((h) => {
    if (!h.future.length) return h;
    const next = h.future[0];
    setContent(next); setDirty(true); remount();
    return { past: [...h.past, content].slice(-50), future: h.future.slice(1) };
  });

  // section operations
  const idx = (id) => sections.findIndex((s) => s.id === id);
  const move = (id, dir) => { const i = idx(id); const j = i + dir; if (j < 0 || j >= sections.length) return; const a = [...sections]; [a[i], a[j]] = [a[j], a[i]]; commit(a); };
  const dup = (id) => { const i = idx(id); const a = [...sections]; a.splice(i + 1, 0, { ...clone(a[i]), id: newId() }); commit(a); };
  const remove = (id) => { commit(sections.filter((s) => s.id !== id)); if (sel?.sec === id) setSel(null); };
  const toggleHide = (id) => patchSec(id, (s) => ({ ...s, hidden: !s.hidden }));
  const addSection = (type) => {
    const s = makeSection(type);
    const a = [...sections]; a.splice(addAt ?? a.length, 0, s); commit(a);
    setAddAt(null); remount();
    if (["image", "image_text", "hero"].includes(type)) setTimeout(() => { setSel({ sec: s.id, field: "image" }); setPicker(true); }, 50);
    else setSel({ sec: s.id, field: type === "quote" ? "_section" : "heading" });
    toast.success("Section added");
  };

  useEffect(() => { registerDirty(dirty); return () => registerDirty(false); }, [dirty, registerDirty]);
  // Closing the panel discards only unsaved local edits; the launcher stays mounted.
  useEffect(() => {
    if (!on) {
      if (dirty) { setContent(base); setDirty(false); }
      setSel(null); setDevice("desktop"); inlineDraft.current = null;
    }
    remount();
  }, [on]); // eslint-disable-line

  useEffect(() => {
    document.body.classList.remove("live-dev-tablet", "live-dev-mobile");
  }, [on, device]);

  const previewSrc = typeof window !== "undefined" ? `${window.location.pathname}?editor-preview=1` : "/";

  // Keep the default panel clear of navigation on every page and viewport.
  useEffect(() => {
    if (!on) return undefined;
    const header = document.querySelector(".site .header");
    if (!header) return undefined;
    const measure = () => setPanelTop(Math.ceil(header.getBoundingClientRect().height) + 12);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(header);
    return () => observer.disconnect();
  }, [on, pageKey]);

  // click to select
  useEffect(() => {
    if (!on || scope !== "page") return undefined;
    const h = (e) => {
      if (e.target.closest(".live-ui, [role=dialog], [data-site-edit], [data-live-navigate]") || !e.target.closest("main")) return;
      const el = e.target.closest("[data-edit]");
      const secEl = e.target.closest("[data-sec]");
      if (el || secEl) { e.preventDefault(); e.stopPropagation(); }
      if (secEl) selectField({ sec: secEl.dataset.sec, field: el ? el.dataset.edit : "_section" });
    };
    document.addEventListener("click", h, true);
    return () => document.removeEventListener("click", h, true);
  }, [on, scope, sections]); // eslint-disable-line react-hooks/exhaustive-deps

  // inline contentEditable for text fields
  useEffect(() => {
    const el = findEl(sel);
    if (!on || scope !== "page" || !el || !isText) return undefined;
    el.contentEditable = "true";
    const record = () => {
      inlineDraft.current = { ...sel, value: field.endsWith("_html") ? el.innerHTML : el.innerText.replace(/\n{3,}/g, "\n\n").trim() };
      setDirty(true);
    };
    const commitText = () => {
      const draft = inlineDraft.current;
      if (!draft || draft.sec !== sel.sec || draft.field !== field) return;
      inlineDraft.current = null;
      const s = sections.find((x) => x.id === sel.sec);
      if (!s) return;
      const v = draft.value;
      if (v !== (getPath(s.data, field) || "")) { patchSec(sel.sec, (x) => ({ ...x, data: setPath(x.data, field, v) })); remount(); }
    };
    el.addEventListener("blur", commitText);
    el.addEventListener("input", record);
    return () => { el.removeEventListener("input", record); el.removeEventListener("blur", commitText); el.removeAttribute("contenteditable"); };
  }, [on, scope, sel, content]); // eslint-disable-line

  // track selection rectangle
  useEffect(() => {
    if (!on || !sel) { setRect(null); return undefined; }
    let raf;
    const tick = () => {
      const r = findEl(sel)?.getBoundingClientRect();
      setRect((o) => (r && (!o || o.top !== r.top || o.left !== r.left || o.width !== r.width || o.height !== r.height) ? { top: r.top, left: r.left, width: r.width, height: r.height } : r ? o : null));
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [on, sel, device]);

  useEffect(() => {
    const h = (e) => { if (dirty) { e.preventDefault(); e.returnValue = ""; } };
    window.addEventListener("beforeunload", h);
    return () => window.removeEventListener("beforeunload", h);
  }, [dirty]);

  const save = async () => {
    setBusy(true);
    // Flush any in-progress inline text edit (user may click Save without blurring first)
    let secs = sections;
    const draft = inlineDraft.current;
    if (draft) {
      secs = sections.map((s) => (s.id === draft.sec ? { ...s, data: setPath(s.data, draft.field, draft.value) } : s));
      inlineDraft.current = null;
      setContent((c) => ({ ...c, sections: secs }));
    }
    try {
      const payload = { title: content.title, sections: secs.map((s) => ({ id: s.id, type: s.type, hidden: !!s.hidden, data: stripMedia(s.data), styles: s.styles || {} })) };
      const r = noteId ? await api.put(`/admin/notes/${noteId}/live`, { ...stripMedia(secs[0].data), styles: secs[0].styles || {} }) : await api.put(`/admin/pages/${pageKey}/live`, payload);
      const saved = noteId ? { ...content, sections: [{ ...secs[0], data: r.data.note, styles: r.data.note.styles || {} }] } : r.data.content;
      setContent(saved); setBase(saved); setDirty(false); setHist({ past: [], future: [] }); remount();
      toast.success("Saved on this site");
    } catch (e) { toast.error(errMsg(e)); } finally { setBusy(false); }
  };
  const setImage = (m) => {
    const resolved = { ...m, src: m.preview, srcs: (m.derivs || []).map((d) => ({ w: d.w, url: `/api/admin/media/${m.id}/view/${d.w}?v=${m.version}` })) };
    patchSec(sel.sec, (s) => ({ ...s, data: setPath(s.data, field, { ...(getPath(s.data, field) || {}), media_id: m.id, media: resolved }) }));
    remount(); setBusy(false);
  };
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append("file", file); fd.append("category", "live-editor");
    try { setBusy(true); const r = await api.post("/admin/media", fd); setImage(r.data); }
    catch (e) { toast.error(errMsg(e)); setBusy(false); }
  };
  const exit = () => setOn(false);
  const num = (v) => (v ? parseInt(v, 10) || 0 : 0);
  const SNAP = 6;
  const gatherSnaps = (exclude) => {
    const xs = [], ys = [];
    document.querySelectorAll("main [data-sec], main [data-edit]").forEach((el) => {
      if (!exclude || el === exclude || exclude.contains(el) || el.contains(exclude)) return;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      xs.push(r.left, r.right, r.left + r.width / 2);
      ys.push(r.top, r.bottom, r.top + r.height / 2);
    });
    return { xs, ys };
  };
  const nearest = (val, cands) => {
    let best = null, bd = SNAP;
    for (const c of cands) { const d = Math.abs(val - c); if (d <= bd) { bd = d; best = c; } }
    return best;
  };
  const resize = (dir) => (e) => {
    e.preventDefault(); e.stopPropagation();
    e.target.setPointerCapture?.(e.pointerId);
    const el = findEl(sel);
    const r0 = el?.getBoundingClientRect() || rect;
    if (!r0) return;
    const { xs, ys } = gatherSnaps(el);
    const sx0 = e.clientX, sy0 = e.clientY, w0 = r0.width, h0 = r0.height;
    const tx0 = num(st.translateX), ty0 = num(st.translateY);
    const mv = (ev) => {
      let dx = ev.clientX - sx0, dy = ev.clientY - sy0;
      const gls = [];
      if (dir.includes("e")) { const s = nearest(r0.right + dx, xs); if (s != null) { dx += s - (r0.right + dx); gls.push({ x: s }); } }
      if (dir.includes("w")) { const s = nearest(r0.left + dx, xs); if (s != null) { dx += s - (r0.left + dx); gls.push({ x: s }); } }
      if (dir.includes("s")) { const s = nearest(r0.bottom + dy, ys); if (s != null) { dy += s - (r0.bottom + dy); gls.push({ y: s }); } }
      if (dir.includes("n")) { const s = nearest(r0.top + dy, ys); if (s != null) { dy += s - (r0.top + dy); gls.push({ y: s }); } }
      const patch = {};
      if (dir.includes("e")) patch.width = `${Math.max(40, Math.round(w0 + dx))}px`;
      if (dir.includes("w")) { const nw = Math.max(40, Math.round(w0 - dx)); patch.width = `${nw}px`; patch.translateX = `${tx0 + (w0 - nw)}px`; }
      if (dir.includes("s")) patch.height = `${Math.max(20, Math.round(h0 + dy))}px`;
      if (dir.includes("n")) { const nh = Math.max(20, Math.round(h0 - dy)); patch.height = `${nh}px`; patch.translateY = `${ty0 + (h0 - nh)}px`; }
      setStyles(patch); setGuides(gls);
    };
    const up = () => { setGuides([]); window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
  };
  const moveDrag = (e) => {
    e.preventDefault(); e.stopPropagation();
    e.target.setPointerCapture?.(e.pointerId);
    const el = findEl(sel);
    const r0 = el?.getBoundingClientRect() || rect;
    const { xs, ys } = gatherSnaps(el);
    const sx0 = e.clientX, sy0 = e.clientY, tx0 = num(st.translateX), ty0 = num(st.translateY);
    const mv = (ev) => {
      let dx = ev.clientX - sx0, dy = ev.clientY - sy0;
      const gls = [];
      if (r0) {
        const xc = [[r0.left + dx], [r0.right + dx], [r0.left + r0.width / 2 + dx]].map(([v]) => [nearest(v, xs), v]).filter((c) => c[0] != null);
        if (xc.length) { xc.sort((a, b) => Math.abs(a[0] - a[1]) - Math.abs(b[0] - b[1])); dx += xc[0][0] - xc[0][1]; gls.push({ x: xc[0][0] }); }
        const yc = [[r0.top + dy], [r0.bottom + dy], [r0.top + r0.height / 2 + dy]].map(([v]) => [nearest(v, ys), v]).filter((c) => c[0] != null);
        if (yc.length) { yc.sort((a, b) => Math.abs(a[0] - a[1]) - Math.abs(b[0] - b[1])); dy += yc[0][0] - yc[0][1]; gls.push({ y: yc[0][0] }); }
      }
      setStyles({ translateX: `${tx0 + dx}px`, translateY: `${ty0 + dy}px` }); setGuides(gls);
    };
    const up = () => { setGuides([]); window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
  };
  const dragPanel = (e) => {
    if (e.target.closest("button")) return;
    e.preventDefault();
    const panel = e.currentTarget.closest(".live-panel");
    const r = panel.getBoundingClientRect();
    const off = { x: e.clientX - r.left, y: e.clientY - r.top };
    const mv = (ev) => setPos({
      left: Math.max(4, Math.min(window.innerWidth - 80, ev.clientX - off.x)),
      top: Math.max(4, Math.min(window.innerHeight - 44, ev.clientY - off.y)),
    });
    const up = () => { window.removeEventListener("pointermove", mv); window.removeEventListener("pointerup", up); };
    window.addEventListener("pointermove", mv); window.addEventListener("pointerup", up);
  };

  if (!on || scope !== "page") return null;

  return (
    <>
      {guides.map((g, i) => (
        <div key={i} className={`live-ui live-guide ${g.x != null ? "live-guide-v" : "live-guide-h"}`} style={g.x != null ? { left: g.x } : { top: g.y }} data-testid="live-guide" />
      ))}
      {rect && (
        <div className={`live-ui live-box ${field === "_section" ? "live-box-sec" : ""}`} style={{ top: rect.top, left: rect.left, width: rect.width, height: rect.height }} data-testid="live-selection-box">
          <span className="live-move-grip" onPointerDown={moveDrag} title="Drag to move anywhere" data-testid="live-move-grip"><GripVertical size={13} /></span>
          <span className="live-handle live-h-n" onPointerDown={resize("n")} data-testid="live-resize-n" />
          <span className="live-handle live-h-s" onPointerDown={resize("s")} data-testid="live-resize-s" />
          <span className="live-handle live-h-e" onPointerDown={resize("e")} data-testid="live-resize-e" />
          <span className="live-handle live-h-w" onPointerDown={resize("w")} data-testid="live-resize-w" />
          <span className="live-handle live-h-ne" onPointerDown={resize("ne")} data-testid="live-resize-ne" />
          <span className="live-handle live-h-nw" onPointerDown={resize("nw")} data-testid="live-resize-nw" />
          <span className="live-handle live-h-se" onPointerDown={resize("se")} data-testid="live-resize-se" />
          <span className="live-handle live-h-sw" onPointerDown={resize("sw")} data-testid="live-resize-sw" />
          <Dim cls="live-dim-up" icon={ArrowUp} value={num(st.translateY) < 0 ? -num(st.translateY) : 0} onSet={(v) => setStyles({ translateY: v ? `-${v}px` : "" })} testid="live-dim-up" />
          <Dim cls="live-dim-down" icon={ArrowDown} value={num(st.translateY) > 0 ? num(st.translateY) : 0} onSet={(v) => setStyles({ translateY: v ? `${v}px` : "" })} testid="live-dim-down" />
          <Dim cls="live-dim-left" icon={ArrowLeft} value={num(st.translateX) < 0 ? -num(st.translateX) : 0} onSet={(v) => setStyles({ translateX: v ? `-${v}px` : "" })} testid="live-dim-left" />
          <Dim cls="live-dim-right" icon={ArrowRight} value={num(st.translateX) > 0 ? num(st.translateX) : 0} onSet={(v) => setStyles({ translateX: v ? `${v}px` : "" })} testid="live-dim-right" />
          {sec && !noteId && (
            <div className="live-sectools" data-testid="live-section-tools">
              <button type="button" title="Move up" onClick={() => move(sec.id, -1)} data-testid="live-sec-up"><ArrowUp size={14} /></button>
              <button type="button" title="Move down" onClick={() => move(sec.id, 1)} data-testid="live-sec-down"><ArrowDown size={14} /></button>
              <button type="button" title="Duplicate" onClick={() => dup(sec.id)} data-testid="live-sec-duplicate"><Copy size={14} /></button>
              <button type="button" title={sec.hidden ? "Show" : "Hide"} onClick={() => toggleHide(sec.id)} data-testid="live-sec-hide">{sec.hidden ? <EyeOff size={14} /> : <Eye size={14} />}</button>
              <button type="button" title="Delete" onClick={() => remove(sec.id)} data-testid="live-sec-delete"><Trash2 size={14} /></button>
              <button type="button" title="Add section below" onClick={() => setAddAt(idx(sec.id) + 1)} data-testid="live-sec-add-below"><Plus size={14} /></button>
            </div>
          )}
        </div>
      )}

      <aside className="live-ui live-panel" style={{ "--live-panel-top": `${panelTop}px`, ...(pos ? { top: pos.top, left: pos.left, right: "auto" } : {}) }} data-testid="live-editor-panel">
        <div className="live-row live-top">
          <strong className="live-drag" onPointerDown={dragPanel} title="Drag to move" data-testid="live-panel-drag"><GripVertical size={14} /> Live editor</strong>
          <button type="button" className="live-btn" disabled={!hist.past.length} onClick={undo} title="Undo" data-testid="live-undo"><Undo2 size={14} /></button>
          <button type="button" className="live-btn" disabled={!hist.future.length} onClick={redo} title="Redo" data-testid="live-redo"><Redo2 size={14} /></button>
          <button type="button" className="live-btn live-primary" disabled={busy || !dirty} onClick={save} data-testid="live-save-btn"><Save size={14} /> {busy ? "Saving…" : "Save"}</button>
          <button type="button" className="live-btn" onClick={exit} aria-label="Close live editor" data-testid="live-exit-btn"><X size={14} /></button>
        </div>

        <div className="live-devs" role="group" aria-label="Preview device">
          {[["desktop", Monitor], ["tablet", Tablet], ["mobile", Smartphone]].map(([d, I]) => (
            <button key={d} type="button" className={`live-btn ${device === d ? "live-on" : ""}`} onClick={() => setDevice(d)} aria-label={d} data-testid={`live-device-${d}`}><I size={14} /></button>
          ))}
        </div>

        <FieldInspector sections={sections} selected={sel} onSelect={selectField} title={content.title} onTitleChange={noteId ? undefined : (title) => { setHist((h) => ({ past: [...h.past, content].slice(-50), future: [] })); setContent((c) => ({ ...c, title })); setDirty(true); }} onChange={(id, path, value) => { inlineDraft.current = null; patchSec(id, (s) => ({ ...s, data: setPath(s.data, path, value) })); }} />

        {!sel || !sec ? (
          <p className="live-hint" data-testid="live-hint">Click any heading, text, image or whole section on the page. Drag the dark grip to move it anywhere (up, down, left, right), or drag any of the 8 red handles to resize from every side. Use the numeric Move X/Y and Width/Height boxes for precise control. Press Save to publish live.</p>
        ) : (
          <div data-testid="live-controls">
            <p className="live-label" data-testid="live-selected-label">{labelFor(field)}</p>

            {isImage ? (
              <div>
              <div className="live-row">
                <button type="button" className="live-btn" onClick={() => setPicker(true)} data-testid="live-choose-image"><Images size={14} /> Library</button>
                <button type="button" className="live-btn" onClick={() => fileRef.current?.click()} disabled={busy} data-testid="live-upload-image"><Upload size={14} /> Upload</button>
                <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => upload(e.target.files?.[0])} data-testid="live-upload-input" />
              </div>
              {["caption", "credit", "alt"].map((name) => <label key={name} className="live-field">{name}<input type="text" value={getPath(sec.data, `${field}.${name}`) ?? getPath(sec.data, `${field}.media.${name}`) ?? ""} onChange={(e) => patchSec(sec.id, (s) => ({ ...s, data: setPath(s.data, `${field}.${name}`, e.target.value) }))} data-testid={`live-image-${name}`} /></label>)}
              <label className="live-field">Image position<input type="text" value={st.objectPosition || ""} placeholder="50% 50%" onChange={(e) => setStyles({ objectPosition: e.target.value })} data-testid="live-image-position" /></label>
              </div>
            ) : field === "_section" ? (
              <p className="live-hint">Style the whole section — its background colour and spacing.</p>
            ) : (<>
              <p className="live-hint">Type directly on the page to change the words.</p>
              <label className="live-field">Font
                <select value={st.fontFamily || ""} onChange={(e) => setStyles({ fontFamily: e.target.value })} data-testid="live-font-select">
                  <option value="">Default</option>{FONTS.map((f) => <option key={f} value={f}>{f}</option>)}
                </select>
              </label>
              <div className="live-row">
                <label className="live-field">Size (px)<input type="number" min="8" max="200" value={px(st.fontSize)} placeholder="auto" onChange={(e) => setStyles({ fontSize: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-font-size" /></label>
                <label className="live-field">Weight
                  <select value={st.fontWeight || ""} onChange={(e) => setStyles({ fontWeight: e.target.value })} data-testid="live-font-weight">
                    <option value="">Default</option>{["300", "400", "500", "600", "700"].map((w) => <option key={w}>{w}</option>)}
                  </select>
                </label>
              </div>
              <div className="live-row">
                <button type="button" className={`live-btn ${st.fontWeight === "700" ? "live-on" : ""}`} onClick={() => setStyles({ fontWeight: st.fontWeight === "700" ? "" : "700" })} title="Bold" data-testid="live-bold"><Bold size={14} /></button>
                <button type="button" className={`live-btn ${st.fontStyle === "italic" ? "live-on" : ""}`} onClick={() => setStyles({ fontStyle: st.fontStyle === "italic" ? "" : "italic" })} title="Italic" data-testid="live-italic"><Italic size={14} /></button>
                <button type="button" className={`live-btn ${st.textTransform === "uppercase" ? "live-on" : ""}`} onClick={() => setStyles({ textTransform: st.textTransform === "uppercase" ? "" : "uppercase" })} title="UPPERCASE" data-testid="live-uppercase">AA</button>
              </div>
              <div className="live-row">
                <label className="live-field"><Paintbrush size={12} /> Colour<input type="color" value={st.color || "#2b2b2b"} onChange={(e) => setStyles({ color: e.target.value })} data-testid="live-font-color" /></label>
                <div className="live-field">Align
                  <div className="live-row" style={{ margin: 0 }}>{[["left", AlignLeft], ["center", AlignCenter], ["right", AlignRight]].map(([a, I]) => (
                    <button key={a} type="button" className={`live-btn ${st.textAlign === a ? "live-on" : ""}`} onClick={() => setStyles({ textAlign: st.textAlign === a ? "" : a })} aria-label={`Align ${a}`} data-testid={`live-align-${a}`}><I size={14} /></button>
                  ))}</div>
                </div>
              </div>
              <div className="live-row">
                <label className="live-field">Line height<input type="number" step="0.1" min="0.8" max="3" value={st.lineHeight || ""} placeholder="auto" onChange={(e) => setStyles({ lineHeight: e.target.value })} data-testid="live-line-height" /></label>
                <label className="live-field">Letter sp.<input type="text" value={st.letterSpacing || ""} placeholder="e.g. 1px" onChange={(e) => setStyles({ letterSpacing: e.target.value })} data-testid="live-letter-spacing" /></label>
              </div>
            </>)}

            {(isImage || isText || field === "_section") && (
              <>
                <div className="live-row">
                  <label className="live-field">Width (px)<input type="number" value={px(st.width)} placeholder="auto" onChange={(e) => setStyles({ width: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-width" /></label>
                  <label className="live-field">Height (px)<input type="number" value={px(st.height)} placeholder="auto" onChange={(e) => setStyles({ height: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-height" /></label>
                </div>
                <div className="live-row">
                  <label className="live-field">Move X (px)<input type="number" value={px(st.translateX)} placeholder="0" onChange={(e) => setStyles({ translateX: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-move-x" /></label>
                  <label className="live-field">Move Y (px)<input type="number" value={px(st.translateY)} placeholder="0" onChange={(e) => setStyles({ translateY: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-move-y" /></label>
                </div>
                <p className="live-label" style={{ marginTop: 4 }}>Padding inside box (px)</p>
                <div className="live-row">
                  <label className="live-field">Top<input type="number" value={px(st.paddingTop)} placeholder={padPH("paddingTop")} onChange={(e) => setStyles({ paddingTop: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-pad-top" /></label>
                  <label className="live-field">Bottom<input type="number" value={px(st.paddingBottom)} placeholder={padPH("paddingBottom")} onChange={(e) => setStyles({ paddingBottom: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-pad-bottom" /></label>
                </div>
                <div className="live-row">
                  <label className="live-field">Left<input type="number" value={px(st.paddingLeft)} placeholder={padPH("paddingLeft")} onChange={(e) => setStyles({ paddingLeft: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-pad-left" /></label>
                  <label className="live-field">Right<input type="number" value={px(st.paddingRight)} placeholder={padPH("paddingRight")} onChange={(e) => setStyles({ paddingRight: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-pad-right" /></label>
                </div>
                <p className="live-label" style={{ marginTop: 4 }}>Margin outside box (px)</p>
                <div className="live-row">
                  <label className="live-field">Top<input type="number" value={px(st.marginTop)} placeholder={padPH("marginTop")} onChange={(e) => setStyles({ marginTop: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-mar-top" /></label>
                  <label className="live-field">Bottom<input type="number" value={px(st.marginBottom)} placeholder={padPH("marginBottom")} onChange={(e) => setStyles({ marginBottom: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-mar-bottom" /></label>
                </div>
                <div className="live-row">
                  <label className="live-field">Left<input type="number" value={px(st.marginLeft)} placeholder={padPH("marginLeft")} onChange={(e) => setStyles({ marginLeft: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-mar-left" /></label>
                  <label className="live-field">Right<input type="number" value={px(st.marginRight)} placeholder={padPH("marginRight")} onChange={(e) => setStyles({ marginRight: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-mar-right" /></label>
                </div>
              </>
            )}

            <div className="live-sec-style">
              <p className="live-label">Section background &amp; spacing</p>
              <SectionStyle sec={sec} onChange={(patch) => patchSec(sec.id, (s) => {
                const f = { ...((s.styles || {})._section || {}), ...patch };
                Object.keys(f).forEach((k) => (f[k] === "" || f[k] == null) && delete f[k]);
                return { ...s, styles: { ...(s.styles || {}), _section: f } };
              })} />
            </div>

            <div className="live-row" style={{ marginTop: 10 }}>
              <button type="button" className="live-btn" onClick={() => setStyles({ width: "", height: "" })} data-testid="live-reset-size"><RotateCcw size={14} /> Reset size</button>
              <button type="button" className="live-btn" onClick={() => setStyles({ translateX: "", translateY: "" })} data-testid="live-reset-pos"><RotateCcw size={14} /> Reset position</button>
              <button type="button" className="live-btn" onClick={() => patchSec(sel.sec, (s) => ({ ...s, styles: { ...(s.styles || {}), [field]: {} } }))} data-testid="live-reset-style"><RotateCcw size={14} /> Clear styles</button>
            </div>
          </div>
        )}

        {!noteId && <div className="live-add-block">
          <button type="button" className="live-btn live-add-btn" onClick={() => setAddAt(sections.length)} data-testid="live-add-section"><Plus size={14} /> Add a new section</button>
        </div>}
      </aside>

      {addAt !== null && (
        <div className="live-ui live-add-menu" data-testid="live-add-menu" role="dialog" aria-label="Add a section">
          <div className="live-add-head"><strong>Add a section</strong><button type="button" className="live-btn" onClick={() => setAddAt(null)} data-testid="live-add-close"><X size={14} /></button></div>
          <div className="live-add-grid">
            {ADD_TYPES.map(([type, label, I]) => (
              <button key={type} type="button" className="live-add-item" onClick={() => addSection(type)} data-testid={`live-add-${type}`}><I size={20} /><span>{label}</span></button>
            ))}
          </div>
        </div>
      )}

      <MediaPicker open={picker} onClose={() => setPicker(false)} onPick={setImage} />

      {device !== "desktop" && (
        <div className="live-ui live-preview" data-testid="live-preview-overlay">
          <div className="live-preview-bar">
            <span>{device === "mobile" ? "Mobile preview (375px)" : "Tablet preview (768px)"} — view only. Edits are made in desktop view.</span>
            <div className="live-preview-devs">
              <button type="button" className={`live-btn ${device === "mobile" ? "live-on" : ""}`} onClick={() => setDevice("mobile")} aria-label="Mobile" data-testid="live-preview-mobile"><Smartphone size={14} /></button>
              <button type="button" className={`live-btn ${device === "tablet" ? "live-on" : ""}`} onClick={() => setDevice("tablet")} aria-label="Tablet" data-testid="live-preview-tablet"><Tablet size={14} /></button>
              <button type="button" className="live-btn live-primary" onClick={() => setDevice("desktop")} data-testid="live-preview-close"><X size={14} /> Back to editing</button>
            </div>
          </div>
          <div className="live-preview-stage">
            <iframe title="Responsive preview" src={previewSrc} className={`live-frame live-frame-${device}`} data-testid="live-preview-frame" />
          </div>
        </div>
      )}
    </>
  );
}

function Dim({ cls, icon: Icon, value, onSet, testid }) {
  return (
    <span className={`live-dim ${cls}`} data-testid={testid} title="Pixels to move in this direction">
      <Icon size={11} />
      <input type="number" min="0" value={value || ""} placeholder="0" onChange={(e) => onSet(Math.max(0, parseInt(e.target.value, 10) || 0))} data-testid={`${testid}-input`} />
    </span>
  );
}

function SectionStyle({ sec, onChange }) {
  const s = (sec.styles || {})._section || {};
  return (
    <>
      <div className="live-row">
        <label className="live-field">Background<input type="color" value={s.backgroundColor || "#ffffff"} onChange={(e) => onChange({ backgroundColor: e.target.value })} data-testid="live-sec-bg" /></label>
        <button type="button" className="live-btn" onClick={() => onChange({ backgroundColor: "" })} data-testid="live-sec-bg-clear" title="Clear background"><RotateCcw size={14} /></button>
      </div>
      <div className="live-row">
        <label className="live-field">Space top (px)<input type="number" value={px(s.paddingTop)} placeholder="auto" onChange={(e) => onChange({ paddingTop: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-sec-pad-top" /></label>
        <label className="live-field">Space bottom (px)<input type="number" value={px(s.paddingBottom)} placeholder="auto" onChange={(e) => onChange({ paddingBottom: e.target.value ? `${e.target.value}px` : "" })} data-testid="live-sec-pad-bottom" /></label>
      </div>
    </>
  );
}
