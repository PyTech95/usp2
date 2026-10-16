import { useEffect } from "react";
import { loadFont } from "../../../lib/site";

// Two stable IDs outrank reference selectors containing :has(#page-reference).
export const HeaderStyleTag = ({ styles = {} }) => {
  useEffect(() => { if (styles.fontFamily) loadFont(styles.fontFamily); }, [styles.fontFamily]);
  const rules = [];
  const rule = (selectors, declarations) => {
    const css = Object.entries(declarations).filter(([, v]) => v && /^[#0-9a-zA-Z .,%()\-'\"]{1,100}$/.test(v))
      .map(([k, v]) => `${k}: ${v} !important`).join("; ");
    if (css) rules.push(`${selectors.map((s) => `#public-site #site-header${s}`).join(", ")} { ${css}; }`);
  };
  rule([""], { background: styles.backgroundColor, "padding-top": styles.paddingTop, "padding-bottom": styles.paddingBottom, position: styles.position });
  rule([" .header-inner"], { "padding-left": styles.paddingLeft, "padding-right": styles.paddingRight, "min-height": styles.minHeight });
  rule([" .brand-name", " .brand-sub", " .nav-link", " .dropdown a"], {
    color: styles.color, "font-family": styles.fontFamily && `"${styles.fontFamily}", sans-serif`,
  });
  rule([" .brand-name"], { "font-size": styles.brandFontSize });
  rule([" .brand-sub"], { "font-size": styles.subtitleFontSize });
  rule([" .nav-link", " .dropdown a"], { "font-size": styles.fontSize, "font-weight": styles.fontWeight });
  rule([" .brand img"], { height: styles.logoHeight });
  rule([" nav[aria-label=Main]", " .nav-list"], { background: styles.navBackgroundColor });
  rule([" .nav-list"], { gap: styles.navGap });
  rule([" .dropdown"], { background: styles.dropdownBackgroundColor });
  rule([" .nav-link[aria-current=page]", " .nav-link:hover", " .dropdown a:hover"], { color: styles.activeColor });
  return rules.length ? <style data-testid="header-style-overrides">{rules.join("\n")}</style> : null;
};