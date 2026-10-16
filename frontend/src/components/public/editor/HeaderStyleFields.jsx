import { RotateCcw } from "lucide-react";
import { ColorField, FONTS, px } from "./ColorField";

const COLOURS = [["backgroundColor", "Header background", "#ffffff"], ["color", "Text colour", "#222222"],
  ["navBackgroundColor", "Navigation background", "#fcf1ed"], ["activeColor", "Active / hover colour", "#d41445"],
  ["dropdownBackgroundColor", "Dropdown background", "#ffffff"]];
const TYPE_SIZES = [["brandFontSize", "Brand size", 16, 72], ["subtitleFontSize", "Subtitle size", 8, 24], ["fontSize", "Menu size", 10, 32]];
const SPACING = [["minHeight", "Minimum height", 44, 240], ["logoHeight", "Logo height", 16, 160], ["paddingTop", "Top padding", 0, 160],
  ["paddingBottom", "Bottom padding", 0, 160], ["paddingLeft", "Left padding", 0, 160], ["paddingRight", "Right padding", 0, 160], ["navGap", "Menu gap", 0, 48]];
const slug = (key) => key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`);

export const HeaderStyleFields = ({ styles, change, reset }) => {
  const sizes = (fields) => <div className="header-style-grid">{fields.map(([key, label, min, max]) => <label className="live-field" key={key}>{label} (px)
    <input type="number" min={min} max={max} value={px(styles[key])} placeholder="Default" onChange={(e) => change(key, e.target.value === "" ? "" : `${e.target.value}px`)} data-testid={`header-style-${slug(key)}`} />
  </label>)}</div>;
  return <div data-testid="header-style-fields">
    <details open className="header-editor-group"><summary data-testid="header-colours-toggle">Colours</summary>
      {COLOURS.map(([key, label, fallback]) => <ColorField key={key} label={label} value={styles[key]} fallback={fallback} onChange={(v) => change(key, v)} testid={`header-style-${slug(key)}`} />)}
    </details>
    <details open className="header-editor-group"><summary data-testid="header-typography-toggle">Typography</summary>
      <label className="live-field">Font<select value={styles.fontFamily || ""} onChange={(e) => change("fontFamily", e.target.value)} data-testid="header-style-font-family">
        <option value="">Default</option>{FONTS.map((f) => <option key={f} value={f}>{f}</option>)}
      </select></label>
      <label className="live-field">Menu weight<select value={styles.fontWeight || ""} onChange={(e) => change("fontWeight", e.target.value)} data-testid="header-style-font-weight">
        <option value="">Default</option>{[300, 400, 500, 600, 700, 800].map((w) => <option key={w} value={w}>{w}</option>)}
      </select></label>{sizes(TYPE_SIZES)}
    </details>
    <details open className="header-editor-group"><summary data-testid="header-spacing-toggle">Size &amp; spacing</summary>{sizes(SPACING)}
      <label className="live-field">Position<select value={styles.position || ""} onChange={(e) => change("position", e.target.value)} data-testid="header-style-position">
        <option value="">Default</option><option value="relative">Scroll with page</option><option value="sticky">Sticky at top</option>
      </select></label>
    </details>
    <button type="button" className="live-btn" onClick={reset} data-testid="header-styles-reset"><RotateCcw size={15} /> Reset styles</button>
  </div>;
};