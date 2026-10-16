"""Validation for the public header editor; never accepts arbitrary CSS or DB paths."""
import re
from urllib.parse import urlsplit
from fastapi import HTTPException
from pydantic import BaseModel, Field

COLORS = {"backgroundColor", "color", "navBackgroundColor", "activeColor", "dropdownBackgroundColor"}
SIZES = {"paddingTop": (0, 160), "paddingBottom": (0, 160), "paddingLeft": (0, 160),
         "paddingRight": (0, 160), "minHeight": (44, 240), "fontSize": (10, 32),
         "brandFontSize": (16, 72), "subtitleFontSize": (8, 24), "logoHeight": (16, 160), "navGap": (0, 48)}
FONTS = {"Public Sans", "Lora", "Source Serif 4", "Libre Baskerville", "Source Sans 3", "Noto Sans",
         "Atkinson Hyperlegible", "Cormorant", "Literata", "Playfair Display", "Merriweather",
         "DM Serif Display", "Montserrat", "Poppins", "Raleway", "Work Sans"}


def clean_header_styles(styles):
    clean = {}
    for key, raw in styles.items():
        value = ("" if raw is None else str(raw)).strip()
        if not value:
            continue
        valid = False
        if key in COLORS:
            valid = bool(re.fullmatch(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})", value)) or value == "transparent"
        elif key in SIZES:
            match = re.fullmatch(r"(\d+(?:\.\d+)?)px", value)
            valid = bool(match) and SIZES[key][0] <= float(match[1]) <= SIZES[key][1]
        elif key == "fontFamily":
            valid = value in FONTS
        elif key == "fontWeight":
            valid = value in {str(n) for n in range(300, 801, 100)}
        elif key == "position":
            valid = value in {"relative", "sticky"}
        if not valid:
            raise HTTPException(400, f"Invalid value for {key}")
        clean[key] = value
    return clean


def valid_header_link(value):
    if not value or re.search(r"[\s\\\x00-\x1f\x7f]", value) or "%5c" in value.lower():
        return False
    if value.startswith("/") and not value.startswith("//"):
        return True
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


class HeaderMenuItem(BaseModel):
    path: str = Field(pattern=r"^menus\.main\.\d+(?:\.children\.\d+){0,2}$", max_length=160)
    id: str = Field(max_length=100)
    label: str = Field(min_length=1, max_length=120)
    href: str = Field(min_length=1, max_length=500)


class HeaderPatch(BaseModel):
    brand_label: str = Field(min_length=1, max_length=120)
    full_name: str = Field(max_length=240)
    logo_media_id: str = Field(max_length=100)
    mobile_menu_label: str = Field(min_length=1, max_length=40)
    menu_items: list[HeaderMenuItem] = Field(max_length=100)
    styles: dict


class HeaderSaved(BaseModel):
    ok: bool