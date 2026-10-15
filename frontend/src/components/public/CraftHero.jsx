import { Photo } from "./Photo";

export const CraftHero = ({ data, first, id, editable }) => {
  const Heading = first ? "h1" : "h2";
  const lines = (data.heading || "").split(/(?<=\.)\s+|\n+/).filter(Boolean);

  return (
    <div className="craft-reference-hero" data-testid="craft-reference-hero">
      <div className="craft-hero-frame" data-testid="craft-hero-frame">
        <Photo
          ref_={data.image}
          eager
          crop="20/11"
          cropMobile="4/5"
          className="craft-hero-photo"
          sizes="91vw"
          testid={`${id}-image`}
          ed={editable("image")}
        />
        <div className="craft-hero-copy" data-testid="craft-hero-copy">
          {data.eyebrow && <p className="eyebrow" data-testid={`${id}-eyebrow`} {...editable("eyebrow")}>{data.eyebrow}</p>}
          <Heading className="h1" data-testid={`${id}-heading`} {...editable("heading")}>
            {lines.map((line, i) => <span className="craft-hero-line" key={i}>{line}</span>)}
          </Heading>
        </div>
      </div>
      {data.intro && (
        <div className="craft-hero-intro" data-testid={`${id}-intro`} {...editable("intro")}>
          {data.intro.split(/\n\s*\n/).map((paragraph, i) => <p key={i}>{paragraph}</p>)}
        </div>
      )}
    </div>
  );
};