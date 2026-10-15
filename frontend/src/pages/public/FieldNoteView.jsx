import { Fragment, useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { Download } from "lucide-react";
import { api, fmtDate, media } from "../../lib/api";
import { useMeta, useSite, SITE_URL } from "../../lib/site";
import { Photo } from "../../components/public/Photo";
import { NoteList } from "../../components/public/NoteList";
import { LiveEditor } from "../../components/public/LiveEditor";
import { sx } from "../../components/public/Blocks";
import { SiteText } from "../../components/public/editor/SiteText";
import { Crumbs } from "./PageView";
import NotFound from "./NotFound";

export function NoteArticle({ note, id, slug, published_at, updated_at, related = [] }) {
  const site = useSite();
  const original = useRef({ title: note.title, sections: [{ id: `note-${id || slug}`, type: "note", data: note, styles: note.styles || {} }] });
  const [content, setContent] = useState(original.current), [rev, setRev] = useState(0);
  const s = content.sections[0], data = s.data;
  useMeta({ title: data.seo?.title || `${data.title} — ${site?.site_name || "USP India"}`, description: data.seo?.description || data.standfirst, canonical: data.seo?.canonical || `${SITE_URL}/field-notes/${slug}`, noindex: data.seo?.noindex });
  return <>
    {id && <LiveEditor pageKey={`note-${id}`} noteId={id} content={content} setContent={setContent} original={original.current} remount={() => setRev((n) => n + 1)} />}
    <article data-testid="field-note" data-sec={s.id}>
      <Fragment key={rev}>
        <Crumbs path={`/field-notes/${slug}`} title={data.title} />
        <header className="wrap article-head" style={{ paddingTop: "3rem", paddingBottom: "2rem" }}>
          <p className="eyebrow" data-testid="note-category"><SiteText name={`kind_${data.kind}`} fallback="Field Note" />{data.category && <> · <span {...sx(s, "category")}>{data.category}</span></>}</p>
          <h1 className="h1" data-testid="note-title" {...sx(s, "title")}>{data.title}</h1>
          {data.standfirst && <p className="lede" data-testid="note-standfirst" {...sx(s, "standfirst")}>{data.standfirst}</p>}
          <p className="meta" data-testid="note-publication-info">
            {data.author && <><SiteText name="note_by" /> <span data-testid="note-author" {...sx(s, "author")}>{data.author}</span> · </>}
            {published_at && <><SiteText name="note_published" /> <time dateTime={published_at}>{fmtDate(published_at)}</time></>}
            {updated_at && updated_at.slice(0, 10) !== (published_at || "").slice(0, 10) && <> · <SiteText name="note_updated" /> <time dateTime={updated_at}>{fmtDate(updated_at)}</time></>}
          </p>
        </header>
        <div className="wrap"><Photo ref_={data.cover} eager sizes="(min-width: 1240px) 1100px, 100vw" ed={sx(s, "cover")} testid="note-cover" /></div>
        <div className="wrap section">
          <div className="prose" data-testid="note-body" {...sx(s, "body_html")} style={{ margin: "0 auto", ...sx(s, "body_html").style }} dangerouslySetInnerHTML={{ __html: data.body_html }} />
          <div className="prose" style={{ margin: "0 auto" }}>
            {data.credits && <p className="meta"><SiteText name="credits" />: <span {...sx(s, "credits")} data-testid="note-credits">{data.credits}</span></p>}
            {data.references?.length > 0 && <section><SiteText name="references" as="h2" /><ol>{data.references.map((r, i) => <li key={i}><span {...sx(s, `references.${i}.text`)} data-testid={`note-reference-${i}`}>{r.text}</span>{r.url && <> — <a href={r.url} rel="noopener noreferrer" data-testid={`note-reference-source-${i}`}><SiteText name="source" /></a></>}</li>)}</ol></section>}
            {data.downloads?.length > 0 && <section><SiteText name="downloads" as="h2" /><ul style={{ listStyle: "none", padding: 0 }}>{data.downloads.map((d, i) => d.media && <li key={i}><a href={media(`/api/media/${d.media.id}/file`)} data-testid={`note-download-${i}`}><Download size={16} aria-hidden="true" /> <span {...sx(s, `downloads.${i}.label`)}>{d.label || "Download"}</span></a></li>)}</ul></section>}
          </div>
        </div>
      </Fragment>
    </article>
    <section className="wrap section"><SiteText name="related_notes" as="h2" className="h2" /><NoteList items={related} /></section>
  </>;
}

export default function FieldNoteView() {
  const { slug } = useParams();
  const [data, setData] = useState(undefined);
  useEffect(() => {
    let current = true;
    setData(undefined);
    api.get(`/public/notes/${slug}`).then((r) => { if (current) setData(r.data?.note ? r.data : null); }).catch(() => { if (current) setData(null); });
    return () => { current = false; };
  }, [slug]);
  if (data === undefined) return <div className="wrap section" style={{ minHeight: "60vh" }} aria-busy="true" data-testid="note-loading" />;
  if (data === null) return <NotFound />;
  return <NoteArticle key={data.id || slug} {...data} />;
}