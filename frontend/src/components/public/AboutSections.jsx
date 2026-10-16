import { Photo } from "./Photo";

const Title = ({ data, id, editable }) => <h2 className="h2 about-title" data-testid={`${id}-heading`} {...editable("heading")}>{data.heading}</h2>;
const Copy = ({ html, id, ed }) => <div className="prose" data-testid={id} {...ed} dangerouslySetInnerHTML={{ __html: html || "" }} />;

export const AboutHero = ({ data, first, id, editable }) => {
  const Heading = first ? "h1" : "h2";
  return <div className="about-hero" data-testid="about-hero">
    <Heading className="h1 about-title" data-testid={`${id}-heading`} {...editable("heading")}>{data.heading}</Heading>
  </div>;
};

export const AboutIntroduction = ({ data, id, editable }) => <section className="about-intro-column" data-testid={id}>
  <Copy html={data.body_html} id={`${id}-body`} ed={editable("body_html")} />
</section>;

export const AboutTeam = ({ data, id, editable }) => <section className="about-core" data-testid={id}>
  <div className="about-inner">
    <Title data={data} id={id} editable={editable} />
    <div className="about-team-grid" data-testid="about-team-grid">
      {(data.items || []).map((person, i) => <article className="about-team-member" data-testid={`about-team-member-${i}`} key={i}>
        <Photo ref_={person.image} crop="3/4" cropMobile="3/4" className="about-team-portrait" sizes="(min-width: 1440px) 350px, (min-width: 701px) 27vw, 85vw" testid={`${id}-person-${i}-image`} ed={editable(`items.${i}.image`)} />
        <h3 className="about-person-name" data-testid={`${id}-person-${i}-name`} {...editable(`items.${i}.name`)}>{person.name}</h3>
        <p className="about-person-intro" data-testid={`${id}-person-${i}-intro`} {...editable(`items.${i}.intro`)}>{person.intro}</p>
      </article>)}
    </div>
  </div>
</section>;

export const AboutApproach = ({ data, id, editable }) => <section className="about-approach" data-testid={id}>
  <div className="about-approach-copy">
    <Title data={data} id={id} editable={editable} />
    <Copy html={data.body_html} id={`${id}-body`} ed={editable("body_html")} />
  </div>
  <aside className="about-principles" aria-label="Our principles" data-testid="about-principles">
    <ul>{(data.values || []).map((value, i) => <li key={i}><span data-testid={`${id}-principle-${i}`} {...editable(`values.${i}.text`)}>{value.text}</span></li>)}</ul>
  </aside>
</section>;