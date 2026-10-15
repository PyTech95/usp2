import { useEffect, useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { api } from "../../lib/api";
import { useMeta } from "../../lib/site";
import { SiteText } from "../../components/public/editor/SiteText";

export default function NotFound() {
  const loc = useLocation();
  const nav = useNavigate();
  const [checked, setChecked] = useState(false);
  useEffect(() => {
    api.get("/public/redirect", { params: { path: loc.pathname } })
      .then((r) => nav(r.data.to, { replace: true }))
      .catch(() => setChecked(true));
  }, [loc.pathname, nav]);
  useMeta({ title: "Page not found — USP India", description: "Page not found.", noindex: true });
  if (!checked) return <div className="wrap section" style={{ minHeight: "50vh" }} />;
  return (
    <div className="wrap hero-type" data-testid="not-found">
      <p className="eyebrow">404</p>
      <SiteText name="not_found" as="h1" className="h1" />
      <SiteText name="not_found_body" as="p" className="lede" />
      <div className="hero-actions">
        <Link to="/" className="btn" data-testid="not-found-home"><SiteText name="go_home" /></Link>
        <Link to="/field-notes" className="btn btn-ghost" data-testid="not-found-notes"><SiteText name="read_notes" /></Link>
      </div>
    </div>
  );
}
