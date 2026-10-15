import { Fragment, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../../lib/api";
import { useMeta, useSite, SITE_URL } from "../../lib/site";
import { Blocks } from "../../components/public/Blocks";
import { LiveEditor } from "../../components/public/LiveEditor";
import { loadFont } from "../../lib/site";
import { useScrollReveal } from "../../lib/useScrollReveal";
import NotFound from "./NotFound";

const PATHS = { home: "/", about: "/about", "our-work": "/our-work", rakhigarhi: "/our-work/rakhigarhi", theatre: "/our-work/theatre", "craft-livelihood": "/our-work/craft-livelihood", "workshops-learning": "/our-work/workshops-learning", "field-notes": "/field-notes", connect: "/connect" };

export function Crumbs({ path, title }) {
  if (path === "/") return null;
  const trail = [["Home", "/"]];
  if (path.startsWith("/our-work/")) trail.push(["Our Work", "/our-work"]);
  if (path.startsWith("/field-notes/")) trail.push(["Field Notes", "/field-notes"]);
  trail.push([title, path]);
  return (
    <nav aria-label="Breadcrumb" className="wrap crumbs" style={{ paddingTop: "1.5rem" }} data-testid="breadcrumbs">
      <ol>{trail.map(([n, p], i) => <li key={p}>{i === trail.length - 1 ? <span aria-current="page">{n}</span> : <Link to={p}>{n}</Link>}</li>)}</ol>
    </nav>
  );
}

export function PageBody({ pageKey, content: initial, live }) {
  const site = useSite();
  const [content, setContent] = useState(initial);
  const [rev, setRev] = useState(0);
  useEffect(() => { setContent(initial); }, [initial]);
  useEffect(() => { content.sections.forEach((s) => Object.values(s.styles || {}).forEach((v) => loadFont(v.fontFamily))); }, [content]);
  useScrollReveal([pageKey, content, rev, live]);
  const seo = content.seo || {};
  const name = site?.site_name || "USP India";
  useMeta({
    title: seo.title || (pageKey === "home" ? `${name} — ${site?.full_name || ""}` : `${content.title} — ${name}`),
    description: seo.description,
    canonical: seo.canonical || SITE_URL + PATHS[pageKey],
    noindex: seo.noindex,
  });
  return (
    <div id={{ home: "home-reference", "craft-livelihood": "craft-reference", "workshops-learning": "workshops-reference", rakhigarhi: "rakhigarhi-reference" }[pageKey]} data-testid={`page-${pageKey}`} className={`page-${pageKey}`}>
      <Crumbs path={PATHS[pageKey]} title={content.title} />
      <Fragment key={rev}><Blocks sections={content.sections} home={pageKey === "home"} pageKey={pageKey} /></Fragment>
      {live && <LiveEditor pageKey={pageKey} content={content} setContent={setContent} original={initial} remount={() => setRev((r) => r + 1)} />}
    </div>
  );
}

export default function PageView({ pageKey }) {
  const [data, setData] = useState(undefined);
  useEffect(() => {
    api.get(`/public/pages/${pageKey}`).then((r) => setData(r.data?.content ? r.data : null)).catch(() => setData(null));
  }, [pageKey]);
  if (data === undefined) return <div className="wrap section" aria-busy="true" style={{ minHeight: "60vh" }} />;
  if (data === null) return <NotFound />;
  return <PageBody pageKey={pageKey} content={data.content} live />;
}
