import { useRef, useState } from "react";
import { Download, Upload, Loader2, DatabaseBackup, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { ContentReleasePanel } from "../../components/admin/ContentReleasePanel";
import { ContentJsonPanel } from "../../components/admin/ContentJsonPanel";

export default function ImportExport() {
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState(null);
  const fileRef = useRef(null);

  const doExport = async () => {
    setExporting(true);
    toast.message("Preparing export…", { description: "Bundling all content and media. This can take up to a minute." });
    try {
      const res = await api.get("/admin/site-export", { responseType: "blob", timeout: 180000 });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = `usp-site-export-${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
      toast.success("Export downloaded");
    } catch (e) { toast.error(errMsg(e)); } finally { setExporting(false); }
  };

  const doImport = async (file) => {
    if (!file) return;
    if (!window.confirm("Import will REPLACE this site's pages, field notes, media and settings with the contents of this file. Continue?")) {
      fileRef.current.value = ""; return;
    }
    setImporting(true); setResult(null);
    const fd = new FormData(); fd.append("file", file);
    try {
      const r = await api.post("/admin/site-import", fd, { timeout: 180000 });
      setResult(r.data);
      toast.success("Site imported successfully");
    } catch (e) { toast.error(errMsg(e)); } finally { setImporting(false); if (fileRef.current) fileRef.current.value = ""; }
  };

  return (
    <div className="max-w-3xl space-y-8" data-testid="import-export-page">
      <div>
        <h1 className="text-2xl font-semibold flex items-center gap-2"><DatabaseBackup size={22} /> Import / Export</h1>
        <p className="text-muted-foreground mt-1 text-sm">Move the entire website — all pages, Field Notes, media and settings — to another environment.</p>
      </div>

      <ContentReleasePanel />
      <ContentJsonPanel />
      <section className="border rounded-lg p-6 bg-white" data-testid="export-card">
        <h2 className="font-semibold text-lg flex items-center gap-2"><Download size={18} /> Export the whole site</h2>
        <p className="text-sm text-muted-foreground mt-1">Downloads a single <code>.zip</code> containing every page, Field Note, media file (images) and site settings. Keep it safe or move it to another install.</p>
        <button type="button" onClick={doExport} disabled={exporting} data-testid="export-btn"
          className="mt-4 inline-flex items-center gap-2 px-4 py-2.5 bg-[#111] text-white text-sm font-medium rounded hover:bg-[#333] disabled:opacity-60">
          {exporting ? <><Loader2 size={16} className="animate-spin" /> Preparing…</> : <><Download size={16} /> Export site (.zip)</>}
        </button>
      </section>

      <section className="border rounded-lg p-6 bg-white" data-testid="import-card">
        <h2 className="font-semibold text-lg flex items-center gap-2"><Upload size={18} /> Import a site</h2>
        <div className="mt-2 flex items-start gap-2 text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded p-3">
          <AlertTriangle size={16} className="mt-0.5 shrink-0" />
          <span>Importing <strong>replaces</strong> this environment's pages, Field Notes, media and settings with the file's contents. User accounts are left untouched. Export a backup first.</span>
        </div>
        <input ref={fileRef} type="file" accept=".zip,application/zip" hidden onChange={(e) => doImport(e.target.files?.[0])} data-testid="import-input" />
        <button type="button" onClick={() => fileRef.current?.click()} disabled={importing} data-testid="import-btn"
          className="mt-4 inline-flex items-center gap-2 px-4 py-2.5 border border-[#111] text-[#111] text-sm font-medium rounded hover:bg-[#111] hover:text-white disabled:opacity-60">
          {importing ? <><Loader2 size={16} className="animate-spin" /> Importing…</> : <><Upload size={16} /> Choose export file (.zip)</>}
        </button>
        {result && (
          <div className="mt-4 text-sm bg-green-50 border border-green-200 rounded p-3" data-testid="import-result">
            <p className="font-medium text-green-800">Import complete.</p>
            <ul className="mt-1 text-green-900/80 list-disc pl-5">
              {Object.entries(result.imported || {}).map(([k, v]) => <li key={k}>{k}: {v}</li>)}
              <li>media files restored: {result.media_restored}</li>
            </ul>
          </div>
        )}
      </section>
    </div>
  );
}
