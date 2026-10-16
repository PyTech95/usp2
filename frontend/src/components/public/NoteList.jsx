import { Link } from "react-router-dom";
import { Photo } from "./Photo";
import { fmtDate } from "../../lib/api";
import { SiteText } from "./editor/SiteText";
import { useLiveEditor } from "./editor/LiveEditorProvider";
import { Pencil } from "lucide-react";

export const KIND = { article: "Article", photo_essay: "Photo essay", interview: "Interview", workshop_reflection: "Workshop reflection", resource: "Resource" };

export function NoteList({ items }) {
  const { on } = useLiveEditor();
  if (!items.length) return <SiteText as="p" name="empty_notes" data-testid="notes-empty" />;
  return (
    <ul style={{ listStyle: "none", padding: 0, margin: "1.5rem 0 0" }} data-testid="notes-list">
      {items.map((n) => (
        <li key={n.slug} className="note-item reveal" data-testid={`note-item-${n.slug}`}>
          <article>
            <p className="eyebrow" style={{ marginBottom: ".5rem" }} data-site-style="display.notes-category" data-testid={`note-category-${n.slug}`}><SiteText name={`kind_${n.kind}`} fallback="Field Note" />{n.category ? ` · ${n.category}` : ""}</p>
            <h3 className="h3" style={{ fontSize: "1.5rem" }} data-site-style="display.notes-title" data-testid={`note-title-${n.slug}`}><Link to={`/field-notes/${n.slug}`} data-live-navigate data-testid={`note-link-${n.slug}`}>{n.title}</Link></h3>
            {n.standfirst && <p style={{ margin: ".4rem 0" }} data-site-style="display.notes-summary" data-testid={`note-summary-${n.slug}`}>{n.standfirst}</p>}
            <p className="meta" style={{ margin: 0 }} data-site-style="display.notes-meta" data-testid={`note-meta-${n.slug}`}>{n.author}{n.author ? " · " : ""}<time dateTime={n.published_at}>{fmtDate(n.published_at)}</time></p>
            {on && <Link to={`/field-notes/${n.slug}?edit=1`} className="more-link live-note-link" data-live-navigate data-testid={`edit-note-${n.slug}`}><Pencil size={14} /> Edit story & image</Link>}
          </article>
          <div>{n.cover && <Photo ref_={{ media: n.cover }} sizes="(min-width: 860px) 30vw, 90vw" crop="4/3" framed testid={`note-card-image-${n.slug}`} />}</div>
        </li>
      ))}
    </ul>
  );
}
