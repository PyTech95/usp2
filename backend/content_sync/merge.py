"""Three-way content merge. Local saved edits always win conflicts, including deletions."""
import copy

MISSING = object()


def clone(value):
    return MISSING if value is MISSING else copy.deepcopy(value)


def merge(base, live, incoming, path, preserved):
    if live == incoming or incoming == base:
        return clone(live)
    if live == base:
        return clone(incoming)
    if isinstance(live, dict) and isinstance(incoming, dict) and (isinstance(base, dict) or base is MISSING):
        base = {} if base is MISSING else base
        out = {}
        for key in sorted(base.keys() | live.keys() | incoming.keys()):
            value = merge(base.get(key, MISSING), live.get(key, MISSING), incoming.get(key, MISSING), f"{path}.{key}", preserved)
            if value is not MISSING:
                out[key] = value
        return out
    arrays = [v for v in (base, live, incoming) if v is not MISSING]
    if arrays and all(isinstance(v, list) for v in arrays):
        # Sections and menus have stable IDs. Do not match editable items by index.
        if all(all(isinstance(x, dict) and isinstance(x.get("id"), str) for x in a) and len({x["id"] for x in a}) == len(a) for a in arrays):
            b, l, r = ({} if a is MISSING else {x["id"]: x for x in a} for a in (base, live, incoming))
            order = list(l) if list(l) != list(b) else list(r)
            order += [key for key in r if key not in order]
            out = []
            for key in order:
                value = merge(b.get(key, MISSING), l.get(key, MISSING), r.get(key, MISSING), f"{path}[{key}]", preserved)
                if value is not MISSING:
                    out.append(value)
            return out
    # No baseline / scalar conflict / changed unkeyed array: never discard local content.
    preserved.append(path)
    return clone(live)


def merge_bundle(baseline, current, incoming):
    preserved = []
    out = copy.deepcopy(incoming)
    from .schema import COLLECTION_KEYS
    for name, key in COLLECTION_KEYS.items():
        b = {d[key]: d for d in (baseline or {}).get("collections", {}).get(name, [])}
        l = {d[key]: d for d in current["collections"][name]}
        r = {d[key]: d for d in incoming["collections"][name]}
        documents = []
        for identity in sorted(b.keys() | l.keys() | r.keys()):
            # Media remains available to existing revisions, even when no longer in Preview.
            value = clone(l[identity]) if name == "media" and identity not in r and identity in l else merge(
                b.get(identity, MISSING), l.get(identity, MISSING), r.get(identity, MISSING), f"{name}:{identity}", preserved)
            if value is not MISSING:
                documents.append(value)
        out["collections"][name] = documents
    out["site"] = merge((baseline or {}).get("site", MISSING), current["site"], incoming["site"], "site", preserved)
    return out, preserved