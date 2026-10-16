import hashlib
import re
from fastapi import HTTPException
from header_settings import FONTS


def text_style_key(area, path):
    return hashlib.sha256(f"{area}:{path}".encode()).hexdigest()


def clean_text_style(styles):
    out = {}
    for key, raw in styles.items():
        value = str(raw or "").strip()
        if not value:
            continue
        valid = False
        if key == "fontSize":
            match = re.fullmatch(r"(\d+(?:\.\d+)?)px", value)
            valid = bool(match) and 8 <= float(match[1]) <= 200
        elif key == "fontFamily":
            valid = value in FONTS
        elif key == "color":
            valid = bool(re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value))
        elif key == "fontWeight":
            valid = value in {str(n) for n in range(300, 801, 100)}
        elif key == "lineHeight":
            valid = bool(re.fullmatch(r"\d(?:\.\d+)?", value)) and .8 <= float(value) <= 3
        if not valid:
            raise HTTPException(400, f"Invalid text style: {key}")
        out[key] = value
    return out