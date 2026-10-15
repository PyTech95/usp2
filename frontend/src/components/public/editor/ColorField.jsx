export const FONTS = ["Public Sans", "Lora", "Source Serif 4", "Libre Baskerville", "Source Sans 3", "Noto Sans",
  "Atkinson Hyperlegible", "Cormorant", "Literata", "Playfair Display", "Merriweather", "DM Serif Display",
  "Montserrat", "Poppins", "Raleway", "Work Sans"];

export const px = (v) => (v ? parseInt(v, 10) : "");

const isHex = (v) => /^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$/.test(v || "");

// Colour control with a native swatch AND a text field so editors can paste an exact code (e.g. #2b2b2b).
export function ColorField({ label, value, onChange, testid, fallback = "#ffffff" }) {
  return (
    <label className="live-field">{label}
      <span className="live-color-row">
        <input type="color" value={isHex(value) ? value : fallback} onChange={(e) => onChange(e.target.value)} data-testid={testid} aria-label="Pick colour" />
        <input type="text" className="live-color-hex" value={value || ""} placeholder={fallback} maxLength={24} onChange={(e) => onChange(e.target.value)} data-testid={`${testid}-hex`} aria-label="Colour code" />
      </span>
    </label>
  );
}
