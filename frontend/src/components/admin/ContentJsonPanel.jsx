import { useRef, useState } from "react";
import { Download, FileJson, Upload, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { api, errMsg } from "../../lib/api";
import { useRefreshSite } from "../../lib/site";
import { Button } from "../ui/button";
import { JsonImportReview } from "./JsonImportReview";

export const ContentJsonPanel = () => {
  const input = useRef(null), refresh = useRefreshSite();
  const [file, setFile] = useState(null), [preview, setPreview] = useState(null), [result, setResult] = useState(null);
  const [busy, setBusy] = useState(""), [error, setError] = useState("");
  const download = async (path, name) => {
    setBusy("download"); setError("");
    try {
      const response = await api.get(path, { responseType: "blob", timeout: 180000 });
      const url = URL.createObjectURL(response.data), link = document.createElement("a");
      link.href = url; link.download = name; document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(errMsg(e)); } finally { setBusy(""); }
  };
  const choose = async (next) => {
    if (!next) return;
    setError(""); setResult(null); setPreview(null); setFile(next);
    if (!next.name.toLowerCase().endsWith(".json") || next.size > 12 * 1024 * 1024) {
      setError("Choose a .json content export no larger than 12 MB."); if (input.current) input.current.value = ""; return;
    }
    const data = new FormData(); data.append("file", next);
    setBusy("review");
    try { const response = await api.post("/admin/content-import/preview", data, { timeout: 120000 }); setPreview(response.data); }
    catch (e) { setError(errMsg(e)); }
    finally { setBusy(""); if (input.current) input.current.value = ""; }
  };
  const confirm = async () => {
    setBusy("import"); setError("");
    const data = new FormData(); data.append("file", file); data.append("expected_sha256", preview.sha256); data.append("expected_state", preview.state);
    try {
      const response = await api.post("/admin/content-import", data, { timeout: 180000 });
      setResult(response.data); setPreview(null); setFile(null); toast.success("Content JSON imported");
      try { await refresh(); } catch { toast.message("Import saved. Site settings will refresh when you reopen the public page."); }
    } catch (e) { setError(errMsg(e)); } finally { setBusy(""); }
  };
  return <section className="border rounded-lg p-6 bg-white" data-testid="content-json-panel">
    <h2 className="font-semibold text-lg flex items-center gap-2" data-testid="content-json-title"><FileJson size={18} /> Content JSON</h2>
    <p className="mt-2 text-sm text-muted-foreground" data-testid="content-json-description">Pages, Field Notes, media metadata and presentation settings. Accepts content JSON exports and metadata backups; image files stay in object storage.</p>
    <input ref={input} type="file" hidden accept=".json,application/json" onChange={(e) => choose(e.target.files?.[0])} data-testid="json-import-input" />
    <div className="flex flex-wrap gap-3 mt-4">
      <Button variant="outline" disabled={!!busy} onClick={() => download("/admin/content-export", `usp-content-${new Date().toISOString().slice(0, 10)}.json`)} data-testid="json-export-button"><Download size={16} className="mr-2" /> Export content (.json)</Button>
      <Button disabled={!!busy} onClick={() => input.current?.click()} data-testid="json-import-button">{busy === "review" ? <Loader2 size={16} className="mr-2 animate-spin" /> : <Upload size={16} className="mr-2" />}{busy === "review" ? "Validating…" : "Choose JSON file"}</Button>
    </div>
    {error && !preview && <p className="mt-4 text-sm text-red-700" role="alert" data-testid="json-import-error">{error}</p>}
    {result && <div className="mt-4 border border-green-200 bg-green-50 p-4 rounded text-sm" role="status" data-testid="json-import-result">
      <p className="font-medium text-green-900" data-testid="json-import-success">Content import complete.</p>
      <ul className="mt-2 space-y-1">{Object.entries(result.counts).map(([name, values]) => <li key={name} className="capitalize" data-testid={`json-import-result-${name}`}>{name}: {values.created} new, {values.updated} updated, {values.unchanged} unchanged</li>)}</ul>
      <Button variant="link" className="p-0 mt-3 h-auto" disabled={!!busy} onClick={() => download(`/admin/content-import/backups/${result.backup_id}`, `usp-before-import-${result.backup_id}.json`)} data-testid="json-import-backup-download"><Download size={14} className="mr-2" /> Download pre-import JSON backup</Button>
    </div>}
    <JsonImportReview preview={preview} filename={file?.name || ""} busy={busy === "import"} error={error} close={() => { setPreview(null); setFile(null); setError(""); }} confirm={confirm} />
  </section>;
};