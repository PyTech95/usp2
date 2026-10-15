import { Image as ImageIcon } from "lucide-react";

export const PhotoPlaceholder = ({ label, crop, className, testid, ed }) => (
  <figure
    className={`photo photo-placeholder ${className || ""}`}
    data-testid={testid}
    data-edit={ed?.["data-edit"]}
    style={{ "--placeholder-ratio": crop || "4/3", ...ed?.style }}
    ref={ed?.ref}
    role="img"
    aria-label={`${label || "Photograph"} — placeholder`}
  >
    <div className="photo-frame" data-testid={`${testid}-placeholder`}>
      <ImageIcon size={30} strokeWidth={1} aria-hidden="true" />
      <span data-testid={`${testid}-placeholder-label`}>{label || "Photograph"}</span>
    </div>
  </figure>
);