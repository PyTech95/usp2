import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { Photo } from "./Photo";

const TheatreLink = ({ data, id, editable }) => {
  if (!data.link_href || !data.link_label) return null;
  const content = <><span {...editable("link_label")}>{data.link_label}</span><ArrowRight size={20} aria-hidden="true" /></>;
  return data.link_href.startsWith("/") || data.link_href.startsWith("#")
    ? <Link to={data.link_href} className="theatre-link" data-testid={`${id}-link`}>{content}</Link>
    : <a href={data.link_href} className="theatre-link" data-testid={`${id}-link`}>{content}</a>;
};

const TheatreHeading = ({ data, id, editable }) => <>
  {data.eyebrow && <p className="eyebrow" data-testid={`${id}-eyebrow`} {...editable("eyebrow")}>{data.eyebrow}</p>}
  <h2 className="h2" data-testid={`${id}-heading`} {...editable("heading")}>{data.heading}</h2>
</>;

export const TheatreHero = ({ data, first, id, editable }) => {
  const Heading = first ? "h1" : "h2";
  return <>
    <div className="theatre-hero" data-testid="theatre-hero">
      <Photo ref_={data.image} eager crop="16/10" cropMobile="3/2" className="theatre-hero-photo" sizes="(min-width: 1440px) 1240px, 90vw" testid={`${id}-image`} ed={editable("image")} />
      <div className="theatre-hero-copy" data-testid="theatre-hero-copy">
        <p className="eyebrow" data-testid={`${id}-eyebrow`} {...editable("eyebrow")}>{data.eyebrow}</p>
        <Heading className="h1" data-testid={`${id}-heading`} {...editable("heading")}>
          {(data.heading || "").split(/(?<=\.)\s+|\n+/).filter(Boolean).map((line, i) => <span className="theatre-hero-line" key={i}>{line}</span>)}
        </Heading>
      </div>
    </div>
    <div className="wrap theatre-introduction" data-testid="theatre-introduction">
      <p className="theatre-intro-heading" data-testid={`${id}-intro-heading`} {...editable("intro_heading")}>{data.intro_heading}</p>
      <div className="theatre-intro-copy" data-testid={`${id}-intro`} {...editable("intro")}>
        {(data.intro || "").split(/\n\s*\n/).map((text, i) => <p key={i}>{text}</p>)}
      </div>
    </div>
  </>;
};

export const TheatreArchive = ({ data, id, editable }) => <section className="wrap section theatre-archive" data-testid={id}>
  <TheatreHeading data={data} id={id} editable={editable} />
  <div className="prose" data-testid={`${id}-body`} {...editable("body_html")} dangerouslySetInnerHTML={{ __html: data.body_html || "" }} />
  <Photo ref_={data.image} crop="3/2" cropMobile="3/2" sizes="(min-width: 1440px) 1104px, 80vw" className="theatre-archive-photo reveal" testid={`${id}-image`} ed={editable("image")} />
  <TheatreLink data={data} id={id} editable={editable} />
</section>;

export const TheatreProduction = ({ data, id, editable }) => <section className="wrap section theatre-production" data-testid={id}>
  <TheatreHeading data={data} id={id} editable={editable} />
  {data.subheading && <p className="theatre-production-subtitle" data-testid={`${id}-subheading`} {...editable("subheading")}>{data.subheading}</p>}
  <div className="theatre-production-columns">
    <div>
      <div className="prose" data-testid={`${id}-body`} {...editable("body_html")} dangerouslySetInnerHTML={{ __html: data.body_html || "" }} />
      <TheatreLink data={data} id={id} editable={editable} />
    </div>
    <div>
      <p className="theatre-production-question" data-testid={`${id}-question`} {...editable("question")}>{data.question}</p>
      <div className="prose" data-testid={`${id}-aside`} {...editable("aside_html")} dangerouslySetInnerHTML={{ __html: data.aside_html || "" }} />
    </div>
  </div>
</section>;