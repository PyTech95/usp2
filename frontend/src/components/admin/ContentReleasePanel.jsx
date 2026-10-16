import { useEffect, useState } from "react";
import { RefreshCw, ShieldCheck, RotateCcw } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg, fmtDateTime } from "../../lib/api";

export const ContentReleasePanel = () => {
  const [status, setStatus] = useState(null), [busy, setBusy] = useState(false), [error, setError] = useState("");
  const load = () => api.get("/admin/content-release").then((r) => { setStatus(r.data); setError(""); }).catch((e) => setError(errMsg(e)));
  useEffect(() => { load(); }, []);
  const run = async (action, message, data) => {
    setBusy(true);
    try { await api.post(`/admin/content-release/${action}`, data, { timeout: 180000 }); await load(); toast.success(message); }
    catch (e) { setError(errMsg(e)); } finally { setBusy(false); }
  };
  const source = status?.role === "source", current = status?.current;
  return <section className="border rounded-lg p-6 bg-white space-y-4" data-testid="content-release-panel">
    <div className="flex items-center justify-between gap-4"><h2 className="font-semibold text-lg flex items-center gap-2"><ShieldCheck size={19} /> Republish content</h2><button type="button" className="p-2 rounded hover:bg-neutral-100" aria-label="Refresh content status" onClick={load} data-testid="release-refresh"><RefreshCw size={16} /></button></div>
    {error && <p role="alert" className="text-sm text-red-700" data-testid="release-error">{error}</p>}
    {status?.configured ? <>
      <div className="text-sm space-y-1" data-testid="release-status">
        <p><strong>{source ? "Preview source" : "Live content target"}</strong> · <span data-testid="release-state">{current?.state}</span></p>
        {current?.captured_at && <p>Prepared: <span data-testid="release-prepared-at">{fmtDateTime(current.captured_at)}</span></p>}
        {current?.applied_at && <p>Applied: <span data-testid="release-applied-at">{fmtDateTime(current.applied_at)}</span></p>}
        {current?.counts && <p data-testid="release-counts">{current.counts.pages} pages · {current.counts.notes} Field Notes · {current.counts.media} media records</p>}
        {current?.counts?.page_sections?.rakhigarhi !== undefined && <p data-testid="release-rakhigarhi-sections">Rakhigarhi: {current.counts.page_sections.rakhigarhi} sections</p>}
      </div>
      <p className="text-sm text-muted-foreground" data-testid="release-preservation-policy">Saved live edits are preserved when republishing. If Preview and live both change the same field, the live edit is kept. Each application creates a backup.</p>
      {current?.preserved_count > 0 && <p className="text-sm" data-testid="release-preserved-count">{current.preserved_count} live field changes protected in the latest release.</p>}
      <button type="button" disabled={busy} className="inline-flex items-center gap-2 rounded bg-black px-4 py-2 text-sm text-white disabled:opacity-50" data-testid="release-action" onClick={() => {
        if (!source && !window.confirm("Re-apply packaged Preview updates while preserving saved live edits? A backup will be created. Users and enquiries will not change.")) return;
        run(source ? "prepare" : "apply", source ? "Complete content release prepared" : "Preview content applied with backup");
      }}><RefreshCw size={15} className={busy ? "animate-spin" : ""} />{busy ? "Working…" : source ? "Prepare latest content" : "Re-apply deployment content"}</button>
      {status.backups?.length > 0 && <div className="border-t pt-4 space-y-2"><h3 className="font-medium text-sm">Content backups</h3>{status.backups.map((b) => <div className="flex flex-wrap items-center justify-between gap-2 text-xs" key={b.id} data-testid={`release-backup-${b.id}`}><span>{fmtDateTime(b.created_at)} · {b.records} records</span><button type="button" disabled={busy} className="inline-flex items-center gap-1 underline" data-testid={`release-restore-${b.id}`} onClick={() => {
        if (window.confirm("Restore this content backup? Current content will also be backed up. Users and enquiries are not affected.")) run(`restore/${b.id}`, "Content backup restored", { confirm: true });
      }}><RotateCcw size={12} /> Restore</button></div>)}</div>}
    </> : <p className="text-sm text-muted-foreground" data-testid="release-loading">{status ? "Content promotion is not configured." : "Loading content status…"}</p>}
  </section>;
};