// Rich text descendants can have their own !important design rules. Apply an
// explicit editor choice to the actual text nodes, and restore originals on reset.
const originals = new WeakMap();
const keys = ["fontFamily", "fontSize", "fontWeight", "fontStyle", "color", "textAlign", "textTransform", "lineHeight", "letterSpacing"];
const kebab = (key) => key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);
export function applyTypography(node, styles = {}) {
  if (!node) return;
  const previous = originals.get(node) || [];
  previous.forEach(([el, property, value, priority]) => {
    if (value) el.style.setProperty(property, value, priority);
    else el.style.removeProperty(property);
  });
  const next = [];
  const descendants = [...node.querySelectorAll("p,span,a,strong,em,b,i,h1,h2,h3,h4,li,blockquote,time,cite")]
    .filter((el) => !el.closest("[data-edit]") || el.closest("[data-edit]") === node);
  [node, ...descendants].forEach((el) => keys.forEach((key) => {
    const value = styles[key];
    if (value === undefined || value === null || value === "") return;
    const property = kebab(key);
    next.push([el, property, el.style.getPropertyValue(property), el.style.getPropertyPriority(property)]);
    el.style.setProperty(property, String(value), "important");
  }));
  originals.set(node, next);
}