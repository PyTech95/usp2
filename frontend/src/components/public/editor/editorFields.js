export const getPath = (obj, path) => path.split(".").reduce((o, k) => o?.[k], obj);
export const setPath = (obj, path, value) => {
  const keys = path.split("."), root = Array.isArray(obj) ? [...obj] : { ...obj };
  let current = root;
  keys.slice(0, -1).forEach((key) => {
    current[key] = Array.isArray(current[key]) ? [...current[key]] : { ...(current[key] || {}) };
    current = current[key];
  });
  current[keys[keys.length - 1]] = value;
  return root;
};
export const isImageField = (field) => /(^|\.)(image|cover|poster)$|^collage\.\d+$/.test(field || "");
const SKIP = new Set(["media", "original", "edit_note", "notes", "media_id", "anchor", "layout", "style", "styles", "image_side", "slot", "crop", "cropMobile", "size", "placeholder_label", "id", "slug", "seo", "related", "tags"]);
export function editableFields(data, prefix = "") {
  const result = [];
  Object.entries(data || {}).forEach(([key, value]) => {
    if (SKIP.has(key)) return;
    const path = prefix ? `${prefix}.${key}` : key;
    if (isImageField(path)) {
      result.push({ path, kind: "image" });
      if (value && typeof value === "object") result.push(...editableFields(value, path));
    } else if (typeof value === "string") result.push({ path, kind: "text" });
    else if (value && typeof value === "object") result.push(...editableFields(value, path));
  });
  return result;
}