import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import { Pencil, Globe, LogOut, X, PanelTop } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../../../lib/auth";
import { errMsg } from "../../../lib/api";

const Context = createContext({ on: false, scope: "page", setOn: () => {}, setScope: () => {}, registerDirty: () => {} });
export const useLiveEditor = () => useContext(Context);
const stored = () => { try { return sessionStorage.getItem("usp-live-edit") === "1"; } catch { return false; } };

export function LiveEditorProvider({ children, preview = false }) {
  const { user, can, logout } = useAuth();
  const location = useLocation();
  const [active, setActive] = useState(() => stored() || new URLSearchParams(location.search).has("edit"));
  const [scope, updateScope] = useState("page");
  const [headerPreview, setHeaderPreview] = useState(null);
  const [textStylePreview, setTextStylePreview] = useState(null);
  const [pending, setPending] = useState({ page: false, site: false, header: false });
  const dirty = Object.values(pending).some(Boolean);
  const setScope = (next) => {
    if (scope !== "page" && next !== scope && pending[scope] && !window.confirm("Discard unsaved changes?")) return;
    updateScope(next);
  };
  const registerDirty = useCallback((value, target = "page") => setPending((p) => p[target] === value ? p : { ...p, [target]: value }), []);
  const readOnly = preview || new URLSearchParams(location.search).has("editor-preview");
  const allowed = can("content.publish") && !readOnly;
  const on = allowed && active;
  const setOn = (next) => {
    if (!next && dirty && !window.confirm("Discard unsaved changes and close the editor?")) return;
    setActive(next); if (!next) setPending({ page: false, site: false, header: false });
    if (!next) updateScope("page");
  };
  useEffect(() => {
    if (user === false) { setActive(false); setPending({ page: false, site: false, header: false }); }
  }, [user]);
  useEffect(() => {
    if (user === null || readOnly) return;
    try { if (on) sessionStorage.setItem("usp-live-edit", "1"); else sessionStorage.removeItem("usp-live-edit"); } catch { /* storage may be restricted */ }
    document.body.classList.toggle("live-editing", on);
    return () => document.body.classList.remove("live-editing");
  }, [on, user, readOnly]);
  useEffect(() => { registerDirty(false); }, [location.pathname, registerDirty]);
  useEffect(() => {
    if (!dirty) return undefined;
    const guard = (event) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [dirty]);
  useEffect(() => {
    if (!dirty) return undefined;
    const guard = (e) => {
      const a = e.target.closest("a[href]");
      if (!a || e.target.closest(".live-ui") || a.getAttribute("href")?.startsWith("#")) return;
      if (on && scope === "page" && e.target.closest("[data-sec]") && !e.target.closest("[data-live-navigate]")) return;
      if (on && e.target.closest("[data-site-edit],[data-site-style]")) return;
      if (on && scope === "header" && e.target.closest("#site-header")) return;
      if (!window.confirm("Leave this page and discard unsaved changes?")) { e.preventDefault(); e.stopPropagation(); }
      else registerDirty(false);
    };
    document.addEventListener("click", guard, true);
    return () => document.removeEventListener("click", guard, true);
  }, [dirty, on, scope, registerDirty]);
  const endSession = async () => {
    if (dirty && !window.confirm("Discard unsaved changes and log out?")) return;
    try { await logout(); } catch (e) { toast.error(errMsg(e)); }
  };
  return <Context.Provider value={{ on, setOn, scope, setScope, registerDirty, headerPreview: on && scope === "header" ? headerPreview : null, setHeaderPreview, textStylePreview: on && scope === "site" ? textStylePreview : null, setTextStylePreview }}>
    {children}
    {allowed && <div className="live-ui live-dock" data-testid="live-editor-dock">
      <button type="button" onClick={() => setOn(!on)} aria-expanded={on} data-testid="live-editor-toggle">
        {on ? <X size={15} /> : <Pencil size={15} />} {on ? "Close editor" : "Live editor"}
      </button>
      {can("config") && <button type="button" title="Edit header" onClick={() => { setOn(true); setScope(scope === "header" ? "page" : "header"); }} aria-pressed={on && scope === "header"} data-testid="live-header-toggle"><PanelTop size={15} /> Edit Header</button>}
      {can("config") && <button type="button" title="Edit footer and shared text" onClick={() => { setOn(true); setScope(scope === "site" ? "page" : "site"); }} aria-pressed={on && scope === "site"} data-testid="live-site-toggle"><Globe size={15} /> Site text</button>}
      <button type="button" title="Log out" aria-label="Log out" onClick={endSession} data-testid="live-editor-logout"><LogOut size={15} /></button>
    </div>}
  </Context.Provider>;
}