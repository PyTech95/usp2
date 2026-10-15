import { useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, errMsg } from "../../lib/api";
import { useSite } from "../../lib/site";
import { SiteText, textFor } from "./editor/SiteText";

const TOPICS = ["General", "Collaboration", "Volunteer", "Craft", "Theatre", "Workshops & Learning"];
const EMPTY = { name: "", email: "", topic: "", message: "", phone: "", organisation: "", website: "" };

function validate(f, site) {
  const e = {};
  if (!f.name.trim()) e.name = textFor(site, "error_name");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(f.email)) e.email = textFor(site, "error_email");
  if (!TOPICS.includes(f.topic)) e.topic = textFor(site, "error_topic");
  if (f.message.trim().length < 10) e.message = textFor(site, "error_message");
  if (f.phone && !/^[0-9+()\-\s]{6,40}$/.test(f.phone)) e.phone = textFor(site, "error_phone");
  return e;
}

export function ContactForm() {
  const site = useSite();
  const [params] = useSearchParams();
  const initialTopic = TOPICS.includes(params.get("topic")) ? params.get("topic") : "";
  const [f, setF] = useState({ ...EMPTY, topic: initialTopic });
  const [errors, setErrors] = useState({});
  const [state, setState] = useState({ status: "idle", msg: "" });
  const started = useRef(Date.now());
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    const v = validate(f, site);
    setErrors(v);
    if (Object.keys(v).length) {
      document.getElementById(`f-${Object.keys(v)[0]}`)?.focus();
      return;
    }
    setState({ status: "sending", msg: "" });
    try {
      const r = await api.post("/public/enquiries", { ...f, elapsed_ms: Date.now() - started.current });
      setState({ status: "ok", msg: r.data.email_status });
      setF({ ...EMPTY });
    } catch (err) {
      setState({ status: "error", msg: errMsg(err) });
    }
  };

  const field = (k, label, opts = {}) => (
    <div className="form-field">
      <label htmlFor={`f-${k}`}><SiteText name={`contact_${k}`} fallback={label} />{opts.optional ? <span style={{ fontWeight: 400 }}> (<SiteText name="optional" />)</span> : ""}</label>
      {opts.textarea ? (
        <textarea id={`f-${k}`} rows={6} value={f[k]} onChange={set(k)} aria-invalid={!!errors[k]} aria-describedby={errors[k] ? `e-${k}` : undefined} data-testid={`contact-${k}`} />
      ) : (
        <input id={`f-${k}`} type={opts.type || "text"} value={f[k]} onChange={set(k)} autoComplete={opts.auto} aria-invalid={!!errors[k]} aria-describedby={errors[k] ? `e-${k}` : undefined} data-testid={`contact-${k}`} />
      )}
      {errors[k] && <span id={`e-${k}`} className="field-error" data-testid={`contact-${k}-error`}>{errors[k]}</span>}
    </div>
  );

  return (
    <form onSubmit={submit} noValidate style={{ maxWidth: 640 }} data-testid="contact-form">
      <div aria-live="polite">
        {state.status === "ok" && (
          <div className="notice" role="status" data-testid="contact-success">
            <SiteText as="strong" name="contact_thanks" />
            <SiteText as="p" style={{ margin: ".3rem 0 0" }} name={state.msg === "not_configured" ? "contact_stored" : "contact_notified"} />
          </div>
        )}
        {state.status === "error" && <div className="notice error" role="alert" data-testid="contact-error">{state.msg}</div>}
      </div>
      {field("name", "Name", { auto: "name" })}
      {field("email", "Email", { type: "email", auto: "email" })}
      <div className="form-field">
        <label htmlFor="f-topic"><SiteText name="contact_topic" /></label>
        <select id="f-topic" value={f.topic} onChange={set("topic")} aria-invalid={!!errors.topic} data-testid="contact-topic">
          <option value="">{textFor(site, "choose_topic")}</option>
          {TOPICS.map((t, i) => <option key={t} value={t}>{textFor(site, ["topic_general", "topic_collaboration", "topic_volunteer", "topic_craft", "topic_theatre", "topic_workshops"][i])}</option>)}
        </select>
        {errors.topic && <span className="field-error" data-testid="contact-topic-error">{errors.topic}</span>}
      </div>
      {field("message", "Message", { textarea: true })}
      {field("phone", "Phone", { optional: true, type: "tel", auto: "tel" })}
      {field("organisation", "Organisation", { optional: true, auto: "organization" })}
      <div aria-hidden="true" style={{ position: "absolute", left: "-10000px" }}>
        <label htmlFor="f-website">Leave this empty</label>
        <input id="f-website" tabIndex={-1} autoComplete="off" value={f.website} onChange={set("website")} />
      </div>
      <button type="submit" className="btn" disabled={state.status === "sending"} data-testid="contact-submit">
        <SiteText name={state.status === "sending" ? "sending" : "send_message"} />
      </button>
    </form>
  );
}
