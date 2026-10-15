import { useState } from "react";
import { media } from "../../lib/api";
import { usePreview } from "../../lib/site";
import { PhotoPlaceholder } from "./PhotoPlaceholder";

function Pending({ ref_, testid }) {
  return (
    <div className="photo-pending" data-testid={testid ? `${testid}-pending` : undefined}>
      <span><strong>Photograph pending</strong>{ref_?.media_id ? "Selected file is missing or deleted." : "No approved photograph selected for this module."}</span>
    </div>
  );
}

export function Photo({ ref_, eager = false, sizes = "(min-width: 1024px) 58vw, 100vw", crop, cropMobile, framed, testid, small, className = "", ed }) {
  const preview = usePreview();
  const [showOriginal, setShowOriginal] = useState(false);
  const m = ref_?.media;
  if (!m) {
    if (ref_?.placeholder) return <PhotoPlaceholder label={ref_.placeholder_label} crop={crop} className={className} testid={testid} ed={ed} />;
    if (preview) return <Pending ref_={ref_} testid={testid} />;
    if (ed?.["data-edit"] && typeof document !== "undefined" && document.body.classList.contains("live-editing"))
      return (
        <figure className={`photo photo-addslot ${className}`} ref={ed.ref} style={ed.style} data-testid={testid} data-edit={ed["data-edit"]}>
          <div className="photo-frame"><span>Click to add an image</span></div>
        </figure>
      );
    return null;
  }
  const shown = showOriginal && m.original ? m.original : m;
  const caption = ref_.caption ?? m.caption;
  const credit = ref_.credit ?? m.credit;
  const es = ed?.style || {};
  const style = {
    "--fx-d": `${m.focal_desktop.x}%`, "--fy-d": `${m.focal_desktop.y}%`,
    "--fx-m": `${m.focal_mobile.x}%`, "--fy-m": `${m.focal_mobile.y}%`,
    ...(crop ? { "--ratio": crop } : {}), ...(cropMobile ? { "--ratio-m": cropMobile } : {}), ...(small ? { maxWidth: 420 } : {}),
    ...(es.width ? { width: es.width, maxWidth: es.maxWidth || "100%" } : {}),
    ...(es.transform ? { transform: es.transform } : {}),
    ...(es.position ? { position: es.position } : {}),
    ...(es.alignSelf ? { alignSelf: es.alignSelf } : {}),
    ...(es.justifySelf ? { justifySelf: es.justifySelf } : {}),
    ...(es.zIndex ? { zIndex: es.zIndex } : {}),
    ...(es.paddingTop ? { paddingTop: es.paddingTop } : {}),
    ...(es.paddingBottom ? { paddingBottom: es.paddingBottom } : {}),
    ...(es.paddingLeft ? { paddingLeft: es.paddingLeft } : {}),
    ...(es.paddingRight ? { paddingRight: es.paddingRight } : {}),
  };
  const imgStyle = { ...(es.height ? { height: es.height, width: "100%", aspectRatio: "auto", objectFit: "cover" } : {}), ...(es.objectPosition ? { objectPosition: es.objectPosition } : {}) };
  return (
    <figure className={`photo ${crop ? "crop" : ""} ${framed ? "framed" : ""} ${className}`} style={style} ref={ed?.ref} data-testid={testid} data-edit={ed?.["data-edit"]}>
      <div className="photo-frame">
        <img
          key={shown.id}
          src={media(shown.src)}
          srcSet={shown.srcs.map((s) => `${media(s.url)} ${s.w}w`).join(", ")}
          sizes={sizes}
          width={shown.width}
          height={shown.height}
          alt={ref_.alt ?? m.alt ?? ""}
          loading={eager ? "eager" : "lazy"}
          fetchPriority={eager ? "high" : undefined}
          decoding="async"
          style={imgStyle}
          ref={(node) => { if (node) Object.entries(imgStyle).forEach(([key, val]) => node.style.setProperty(key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`), val, "important")); }}
        />
      </div>
      {(caption || credit) && <figcaption data-testid={testid ? `${testid}-caption` : undefined}><span {...ed?.captionEd}>{caption}</span>{credit && <> — <span {...ed?.creditEd}>{credit}</span></>}</figcaption>}
      {m.original && (
        <div className="photo-original">
          <button type="button" aria-pressed={showOriginal} onClick={() => setShowOriginal(!showOriginal)} data-testid={testid ? `${testid}-original-toggle` : "photo-original-toggle"}>
            {showOriginal ? "Showing the original photograph — view edited version" : "View the original photograph"}
          </button>
          {m.edit_note && <span className="photo-edit-note" data-testid="photo-edit-note">Edit made: {m.edit_note}</span>}
        </div>
      )}
      {!m.public_ok && <span className="photo-flag">Not approved for public use — shown in private preview only</span>}
    </figure>
  );
}
