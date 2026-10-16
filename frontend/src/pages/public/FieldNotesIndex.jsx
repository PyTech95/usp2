import { useEffect, useRef, useState, Fragment } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Search } from "lucide-react";
import { api } from "../../lib/api";
import { useMeta, useSite, SITE_URL } from "../../lib/site";
import { NoteList } from "../../components/public/NoteList";
import { Blocks } from "../../components/public/Blocks";
import { LiveEditor } from "../../components/public/LiveEditor";
import { Crumbs } from "./PageView";
import { SiteText, textFor } from "../../components/public/editor/SiteText";

export default function FieldNotesIndex() {
  const site = useSite();
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "", category = params.get("category") || "", page = parseInt(params.get("page") || "1", 10);
  const [pageData, setPageData] = useState(null);
  const [list, setList] = useState(null);
  const [term, setTerm] = useState(q);
  const [rev, setRev] = useState(0);
  const orig = useRef(null);

  useEffect(() => { api.get("/public/pages/field-notes").then((r) => { setPageData(r.data.content); if (!orig.current) orig.current = r.data.content; }).catch(() => {}); }, []);
  useEffect(() => { api.get("/public/notes", { params: { q, category, page } }).then((r) => setList(Array.isArray(r.data?.items) ? r.data : { items: [], total: 0, page: 1, pages: 1 })).catch(() => setList({ items: [], total: 0, page: 1, pages: 1 })); }, [q, category, page]);
  useEffect(() => setTerm(q), [q]);

  useMeta({
    title: pageData?.seo?.title || `Field Notes — ${site?.site_name || "USP India"}`,
    description: pageData?.seo?.description,
    canonical: `${SITE_URL}/field-notes`,
    noindex: !!(q || category),
  });

  const href = (over) => {
    const p = new URLSearchParams({ ...(q && { q }), ...(category && { category }), ...over });
    [...p.keys()].forEach((k) => !p.get(k) && p.delete(k));
    return `/field-notes${p.toString() ? "?" + p : ""}`;
  };

  return (
    <div data-testid="page-field-notes">
      <Crumbs path="/field-notes" title="Field Notes" />
      {pageData && <Fragment key={rev}><Blocks sections={pageData.sections} /></Fragment>}
      {pageData && <LiveEditor pageKey="field-notes" content={pageData} setContent={setPageData} original={orig.current} remount={() => setRev((r) => r + 1)} live />}
      <section className="wrap section" style={{ paddingTop: 0 }}>
        <form role="search" onSubmit={(e) => { e.preventDefault(); setParams(term ? { q: term, ...(category && { category }) } : category ? { category } : {}); }}
          style={{ display: "flex", gap: ".5rem", maxWidth: 560, marginBottom: "1.5rem" }} className="form-field">
          <label htmlFor="notes-search" className="sr-only"><SiteText name="search_notes" /></label>
          <input id="notes-search" type="search" value={term} onChange={(e) => setTerm(e.target.value)} placeholder={textFor(site, "search_notes")} style={{ flex: 1, minWidth: 0 }} data-site-style="display.notes-search" data-testid="notes-search-input" />
          <button className="btn" type="submit" data-testid="notes-search-submit"><Search size={16} aria-hidden="true" /> <SiteText name="search" /></button>
        </form>
        <nav aria-label="Topics" style={{ display: "flex", flexWrap: "wrap", gap: ".5rem" }} data-testid="notes-filters">
          <Link className="chip" to={href({ category: "", page: "" })} aria-current={!category ? "true" : undefined} data-testid="notes-all-topics"><SiteText name="all_topics" /></Link>
          {(site?.categories || []).map((c) => (
            <Link key={c} className="chip" to={href({ category: c, page: "" })} aria-current={category === c ? "true" : undefined} data-testid={`notes-filter-${c}`}><SiteText name={`category_${c.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`} fallback={c} /></Link>
          ))}
        </nav>
        {list && (
          <>
            <p className="meta" style={{ marginTop: "1.5rem" }} aria-live="polite" data-site-style="display.notes-count" data-testid="notes-count">{list.total} <SiteText name={list.total === 1 ? "note_singular" : "note_plural"} />{q && <> <SiteText name="matching" /> “{q}”</>}{category && <> <SiteText name="in_category" /> {category}</>}</p>
            <NoteList items={list.items} />
            {list.pages > 1 && (
              <nav aria-label="Pagination" style={{ display: "flex", gap: ".5rem", marginTop: "2rem" }} data-testid="notes-pagination">
                {Array.from({ length: list.pages }, (_, i) => i + 1).map((n) => (
                  <Link key={n} className="chip" to={href({ page: n === 1 ? "" : String(n) })} aria-current={n === page ? "true" : undefined} data-site-style="display.notes-page" data-testid={`notes-page-${n}`}><SiteText name="page" /> {n}</Link>
                ))}
              </nav>
            )}
          </>
        )}
      </section>
    </div>
  );
}
