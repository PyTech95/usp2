import { Loader2 } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "../ui/dialog";
import { Button } from "../ui/button";

export const JsonImportReview = ({ preview, filename, busy, error, close, confirm }) => <Dialog open={!!preview} onOpenChange={(open) => { if (!open && !busy) close(); }}>
  <DialogContent className="max-w-xl max-h-[90dvh] overflow-y-auto" data-testid="json-import-review-dialog">
    <DialogHeader><DialogTitle data-testid="json-import-review-title">Review content import</DialogTitle><DialogDescription className="break-all" data-testid="json-import-filename">{filename}</DialogDescription></DialogHeader>
    <div className="overflow-x-auto"><table className="w-full text-sm" data-testid="json-import-counts">
      <thead><tr className="border-b"><th className="text-left py-2">Content</th><th>New</th><th>Updated</th><th>Unchanged</th></tr></thead>
      <tbody>{Object.entries(preview?.counts || {}).map(([name, values]) => <tr key={name} className="border-b" data-testid={`json-import-review-${name}`}><th className="text-left font-normal py-2 capitalize">{name}</th><td className="text-center">{values.created}</td><td className="text-center">{values.updated}</td><td className="text-center">{values.unchanged}</td></tr>)}</tbody>
    </table></div>
    <div className="text-sm space-y-2 text-muted-foreground" data-testid="json-import-warnings">{preview?.warnings.map((text, i) => <p key={text} data-testid={`json-import-warning-${i}`}>{text}</p>)}<p>An automatic backup is created before changes are saved.</p></div>
    {error && <p role="alert" className="text-sm text-red-700" data-testid="json-import-review-error">{error}</p>}
    <DialogFooter><Button variant="outline" disabled={busy} onClick={close} data-testid="json-import-cancel">Cancel</Button><Button disabled={busy} onClick={confirm} data-testid="json-import-confirm">{busy && <Loader2 size={16} className="animate-spin mr-2" />}{busy ? "Importing…" : "Import content"}</Button></DialogFooter>
  </DialogContent>
</Dialog>;