import { Photo } from "./Photo";

export const WorkshopsHero = ({ data, id, editable }) => (
  <div className="workshops-hero" data-testid="workshops-hero">
    <Photo ref_={data.image} crop="4/1" eager sizes="96vw" testid={`${id}-image`} ed={editable("image")} />
    <div className="workshops-hero-copy" data-testid="workshops-hero-copy">
      <p className="eyebrow" data-testid={`${id}-eyebrow`} {...editable("eyebrow")}>{data.eyebrow}</p>
      <h1 className="h1" data-testid={`${id}-heading`} {...editable("heading")}>{data.heading}</h1>
    </div>
  </div>
);