# Copyright (c) 2013-2022 khal contributors
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


dark = [
    ("header", "white", "black"),
    ("footer", "white", "black"),
    ("line header", "black", "white", "bold"),
    ("alt header", "white", "", "bold"),
    ("bright", "dark blue", "white", "bold,standout"),
    ("list", "black", "white"),
    ("list focused", "white", "light blue", "bold"),
    ("edit", "black", "white"),
    ("edit focus", "white", "light blue", "bold"),
    ("button", "black", "dark cyan"),
    ("button focused", "white", "light blue", "bold"),
    ("reveal focus", "black", "light gray"),
    ("today focus", "white", "dark magenta"),
    (
        "today",
        "dark gray",
        "dark green",
    ),
    ("date header", "light gray", "black"),
    ("date header focused", "black", "white"),
    ("date header selected", "dark gray", "light gray"),
    ("dayname", "light gray", ""),
    ("monthname", "light gray", ""),
    ("weeknumber_right", "light gray", ""),
    ("weeknumber_left", "light gray", ""),
    ("alert", "white", "dark red"),
    ("mark", "white", "dark green"),
    ("frame", "white", "black"),
    ("frame focus", "light red", "black"),
    ("frame focus color", "dark blue", "black"),
    ("frame focus top", "dark magenta", "black"),
    ("eventcolumn", "", "", ""),
    ("eventcolumn focus", "", "", ""),
    ("editor", "", "", ""),
    ("editor focus", "", "", ""),
    ("date", "", "", ""),
    ("calendar", "", "", ""),
    ("calendar focus", "", "", ""),
    ("editbx", "light gray", "dark blue"),
    ("editcp", "black", "light gray", "standout"),
    ("popupbg", "white", "black", "bold"),
    ("popupper", "white", "dark cyan"),
    ("caption", "white", "", "bold"),
]
light = [
    ("header", "black", "white"),
    ("footer", "black", "white"),
    ("line header", "black", "white", "bold"),
    ("alt header", "black", "", "bold"),
    ("bright", "dark blue", "white", "bold,standout"),
    ("list", "black", "white"),
    ("list focused", "white", "light blue", "bold"),
    ("edit", "black", "white"),
    ("edit focus", "white", "light blue", "bold"),
    ("button", "black", "dark cyan"),
    ("button focused", "white", "light blue", "bold"),
    ("reveal focus", "black", "dark cyan", "standout"),
    ("today focus", "white", "dark cyan", "standout"),
    ("today", "black", "light gray"),
    ("date header", "", "white"),
    ("date header focused", "white", "dark gray", "bold,standout"),
    ("date header selected", "dark gray", "light cyan"),
    ("dayname", "dark gray", "white"),
    ("monthname", "dark gray", "white"),
    ("weeknumber_right", "dark gray", "white"),
    ("weeknumber_left", "dark gray", "white"),
    ("alert", "white", "dark red"),
    ("mark", "white", "dark green"),
    ("frame", "dark gray", "white"),
    ("frame focus", "light red", "white"),
    ("frame focus color", "dark blue", "white"),
    ("frame focus top", "dark magenta", "white"),
    ("eventcolumn", "", "", ""),
    ("eventcolumn focus", "", "", ""),
    ("editor", "", "", ""),
    ("editor focus", "", "", ""),
    ("date", "", "", ""),
    ("calendar", "", "", ""),
    ("calendar focus", "", "", ""),
    ("editbx", "light gray", "dark blue"),
    ("editcp", "black", "light gray", "standout"),
    ("popupbg", "white", "black", "bold"),
    ("popupper", "black", "light gray"),
    ("caption", "black", "", ""),
]

themes: dict[str, list[tuple[str, ...]]] = {"light": light, "dark": dark}


# the entries of the new UI parts are generated at the end of this module


# -- backdrop: greyscale twins of every palette entry

BACKDROP_SUFFIX = " grey"
BACKDROP_DEFAULT = "backdrop"  # used for text without an attribute
_KEEP_SETTINGS = {"bold", "italics", "underline", "strikethrough"}


def _grey(rgb: tuple[int, int, int], towards: tuple[int, int, int], amount: float) -> str:
    """luminance of `rgb`, blended `amount` towards `towards`, as #rrggbb"""
    luma = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
    target = 0.299 * towards[0] + 0.587 * towards[1] + 0.114 * towards[2]
    value = round(luma * (1 - amount) + target * amount)
    return f"#{value:02x}{value:02x}{value:02x}"


def _settings(spec: str) -> list[str]:
    return [part.strip() for part in spec.split(",") if part.strip() in _KEEP_SETTINGS]


def backdrop_twin(
    entry: tuple[str, ...], dark_theme: bool = True, amount: float = 0.4
) -> tuple[str, ...]:
    """the greyscale twin `<name> grey` of a palette entry

    High colours are converted to grey and blended `amount` towards the
    background; on 16 colour terminals everything becomes dark grey.
    """
    import urwid

    name, fg, bg = entry[0], entry[1] or "", entry[2] or ""
    mono = entry[3] if len(entry) > 3 else None
    fg_high = (entry[4] if len(entry) > 4 else None) or fg
    bg_high = (entry[5] if len(entry) > 5 else None) or bg
    background = (0, 0, 0) if dark_theme else (255, 255, 255)
    foreground = (229, 229, 229) if dark_theme else (0, 0, 0)
    try:
        values = urwid.AttrSpec(fg_high, bg_high, 2**24).get_rgb_values()
    except Exception:  # anything urwid can't parse just becomes grey
        values = (None,) * 6
    fg_rgb = values[:3] if values[0] is not None else foreground
    settings = _settings(fg) + (_settings(mono) if isinstance(mono, str) else [])
    settings = sorted(set(settings))
    fg_grey = ",".join([_grey(fg_rgb, background, amount), *settings])
    bg_grey = "" if values[3] is None else _grey(values[3:], background, amount * 1.5)
    # 16 colours: one visible grey-ish colour for everything (not "dark gray",
    # which is invisible with e.g. Solarized)
    fg16 = ",".join(["light gray" if dark_theme else "dark cyan", *settings])
    return (name + BACKDROP_SUFFIX, fg16, "", None, fg_grey, bg_grey)


def add_backdrop_twins(
    palette: list[tuple[str, ...]], dark_theme: bool = True
) -> list[tuple[str, ...]]:
    """`palette` plus a greyscale twin for every entry (and for `backdrop`)"""
    entries = [entry for entry in palette if not entry[0].endswith(BACKDROP_SUFFIX)]
    twins = [backdrop_twin(entry, dark_theme) for entry in entries]
    default = backdrop_twin((BACKDROP_DEFAULT, "", ""), dark_theme)
    return [*entries, *twins, (BACKDROP_DEFAULT, *default[1:])]


def backdrop_map(palette: list[tuple[str, ...]]) -> dict[str | None, str]:
    """attribute map for an AttrMap that draws a widget with the twins"""
    mapping: dict[str | None, str] = {None: BACKDROP_DEFAULT}
    for entry in palette:
        if not entry[0].endswith(BACKDROP_SUFFIX) and entry[0] != BACKDROP_DEFAULT:
            mapping[entry[0]] = entry[0] + BACKDROP_SUFFIX
    return mapping


# -- semantic themes
#
# A theme can be given as ~15 semantic colours instead of a full urwid
# palette; `expand_theme()` turns it into a palette with an entry for every
# attribute ikhal uses (the names of the `dark` theme). Keys:
#
#   bg    background                 txt   normal text
#   dim   rules, hints, past         lbl   labels, secondary text
#   acc   accent: focus, keys, today row   focused row background
#   pop   popups                     btn   buttons
#   fld2  input fields (search)      errbg background of errors
#   grn, blu, red, yel, pur          state colours (ok, links, errors, ...)
#   cal   (optional) four calendar colours, calfg text on them
#
# Colours are '#rrggbb'. 16-colour terminals get the nearest standard colour.

# name -> (foreground role, background role, settings); roles are keys of a
# semantic theme, "bg" as background means the theme's background
ROLES: dict[str, tuple[str, str, str]] = {
    "body": ("txt", "bg", ""),
    "header": ("txt", "bg", ""),
    "footer": ("lbl", "bg", ""),
    "line header": ("txt", "bg", "bold"),
    "alt header": ("acc", "bg", "bold"),
    "bright": ("acc", "bg", "bold"),
    "list": ("txt", "bg", ""),
    "list focused": ("txt", "row", "bold"),
    "edit": ("txt", "fld2", ""),
    "edit focus": ("txt", "fld2", "bold"),
    "button": ("txt", "btn", ""),
    "button focused": ("bg", "acc", "bold"),
    "reveal focus": ("txt", "row", ""),
    "today focus": ("bg", "acc", "bold"),
    "today": ("acc", "bg", "bold"),
    "date header": ("lbl", "bg", ""),
    "date header focused": ("bg", "acc", "bold"),
    "date header selected": ("txt", "row", ""),
    "dayname": ("dim", "bg", ""),
    "monthname": ("lbl", "bg", ""),
    "weeknumber_right": ("dim", "bg", ""),
    "weeknumber_left": ("dim", "bg", ""),
    "alert": ("txt", "errbg", ""),
    "mark": ("bg", "grn", ""),
    "frame": ("dim", "bg", ""),
    "frame focus": ("acc", "bg", ""),
    "frame focus color": ("acc", "bg", ""),
    "frame focus top": ("acc", "bg", ""),
    "frame title": ("lbl", "bg", ""),
    "frame hint": ("dim", "bg", ""),
    "frame warning": ("yel", "bg", ""),
    "eventcolumn": ("txt", "bg", ""),
    "editor": ("txt", "bg", ""),
    "editor focus": ("txt", "bg", ""),
    "date": ("txt", "bg", ""),
    "eventcolumn focus": ("txt", "bg", ""),
    "calendar": ("txt", "bg", ""),
    "calendar focus": ("txt", "bg", ""),
    "editbx": ("txt", "fld2", ""),
    "editcp": ("bg", "lbl", ""),
    "popupbg": ("txt", "pop", "bold"),
    "popupper": ("txt", "btn", ""),
    "caption": ("lbl", "bg", "bold"),
    "editor label": ("lbl", "bg", ""),
    "editor label focus": ("lbl", "row", ""),
    "editor field": ("txt", "bg", ""),
    "editor field focus": ("txt", "row", "bold"),
    "editor title": ("txt", "bg", "bold"),
    "editor title focus": ("txt", "row", "bold"),
    "editor headline": ("txt", "bg", "bold"),
    "editor headline focus": ("txt", "row", "bold"),
    "editor placeholder": ("dim", "bg", ""),
    "editor placeholder focus": ("dim", "row", ""),
    "editor dim": ("dim", "bg", ""),
    "editor dim focus": ("dim", "row", ""),
    "editor focus row": ("txt", "row", ""),
    "editor marker": ("acc", "row", "bold"),
    "editor rule": ("dim", "bg", ""),
    "editor section": ("lbl", "bg", "bold"),
    "editor button": ("txt", "btn", ""),
    "editor button focus": ("bg", "acc", "bold"),
    "editor adder": ("dim", "bg", ""),
    "editor adder focus": ("bg", "acc", ""),
    "editor delete": ("dim", "bg", ""),
    "editor delete focus": ("txt", "errbg", "bold"),
    "editor key": ("acc", "bg", "bold"),
    "editor hint": ("dim", "bg", ""),
    "editor status": ("yel", "bg", ""),
    "editor error": ("txt", "errbg", ""),
    "editor error hint": ("red", "bg", ""),
    "editor day on": ("bg", "acc", "bold"),
    "editor flash": ("yel", "bg", "bold"),
    "editor card": ("dim", "bg", ""),
    "editor card focus": ("acc", "bg", ""),
    "float border": ("acc", "bg", ""),
    "float title": ("acc", "bg", "bold"),
    "float hint": ("dim", "bg", ""),
    "float headline": ("txt", "bg", "bold"),
    "float text": ("lbl", "bg", ""),
    "float dim": ("dim", "bg", ""),
    "float key": ("acc", "bg", "bold"),
    "float answer": ("txt", "bg", ""),
    "float answer focus": ("txt", "row", "bold"),
    "float choice": ("txt", "bg", ""),
    "float choice focus": ("txt", "row", "bold"),
    "float choice tick": ("acc", "bg", "bold"),
    "float choice tick focus": ("acc", "row", "bold"),
    "float choice hint": ("dim", "bg", ""),
    "float choice hint focus": ("dim", "row", ""),
    "float choice placeholder": ("dim", "bg", "italics"),
    "finder match": ("acc", "bg", "bold"),
    "finder match focus": ("acc", "row", "bold"),
    "message ok": ("grn", "bg", "bold"),
    "message error": ("red", "bg", "bold"),
    "message info": ("lbl", "bg", ""),
    "footer key": ("acc", "bg", "bold"),
    "footer version": ("dim", "bg", ""),
    "details headline": ("txt", "bg", "bold"),
    "details label": ("lbl", "bg", ""),
    "details relative": ("acc", "bg", ""),
    "details text": ("txt", "bg", ""),
    "details dim": ("dim", "bg", ""),
    "details link": ("blu", "bg", "underline"),
    "attendee accepted": ("grn", "bg", ""),
    "attendee tentative": ("yel", "bg", ""),
    "attendee declined": ("red", "bg", ""),
    "agenda event": ("txt", "bg", ""),
    "agenda past": ("dim", "bg", ""),
    "agenda free": ("dim", "bg", ""),
    "agenda now": ("acc", "bg", "bold"),
    "agenda rule": ("dim", "bg", ""),
    "agenda day focus": ("acc", "bg", "bold"),
    # events marked for deletion: red ✕, struck through, the scope in red
    "agenda deleted": ("dim", "bg", "strikethrough"),
    "agenda deleted focus": ("dim", "row", "strikethrough"),
    "agenda deleted mark": ("red", "bg", "bold"),
    "agenda deleted mark focus": ("red", "row", "bold"),
    "agenda deleted scope": ("red", "bg", ""),
    "agenda deleted scope focus": ("red", "row", ""),
    "footer deleted": ("red", "bg", "bold"),
    # the header line: date, time, next event, view tabs
    "header date": ("txt", "bg", "bold"),
    "header time": ("acc", "bg", "bold"),
    "header next": ("txt", "bg", ""),
    "header dim": ("dim", "bg", ""),
    "header tab": ("dim", "bg", ""),
    "header tab active": ("acc", "bg", "bold"),
    # the log (L)
    "log time": ("dim", "bg", ""),
    "log text": ("txt", "bg", ""),
    "log error": ("red", "bg", "bold"),
    "log warning": ("yel", "bg", "bold"),
    "log info": ("lbl", "bg", ""),
    "log debug": ("dim", "bg", ""),
    # blocks marked for deletion in time based views without their own tints
    "timegrid deleted": ("dim", "row", "strikethrough"),
    "timegrid deleted focus": ("txt", "fld2", "strikethrough"),
    "timegrid deleted mark": ("red", "row", "bold"),
    "timegrid deleted scope": ("red", "row", ""),
    "timegrid deleted fill": ("dim", "row", ""),
    "timegrid deleted fill focus": ("dim", "fld2", ""),
    "details deleted": ("red", "bg", ""),
    # derived from the theme: accent blended into the background
    "day heat 1": ("txt", "heat1", ""),
    "day heat 2": ("txt", "heat2", ""),
    "day heat 3": ("txt", "heat3", "bold"),
}
HEAT_TINTS = {"heat1": 0.2, "heat2": 0.38, "heat3": 0.6}

BASIC_RGB: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "dark red": (205, 0, 0),
    "dark green": (0, 205, 0),
    "brown": (205, 205, 0),
    "dark blue": (0, 0, 238),
    "dark magenta": (205, 0, 205),
    "dark cyan": (0, 205, 205),
    "light gray": (229, 229, 229),
    "dark gray": (127, 127, 127),
    "light red": (255, 0, 0),
    "light green": (0, 255, 0),
    "yellow": (255, 255, 0),
    "light blue": (92, 92, 255),
    "light magenta": (255, 0, 255),
    "light cyan": (0, 255, 255),
    "white": (255, 255, 255),
}


def hex_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    if len(color) == 3:
        color = "".join(c * 2 for c in color)
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def luminance(color: str) -> float:
    r, g, b = hex_rgb(color)
    return 0.299 * r + 0.587 * g + 0.114 * b


def _distance(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    return sum((x - y) ** 2 for x, y in zip(a, b))


def nearest_basic(color: str) -> str:
    """the nearest of urwid's 16 standard colours"""
    rgb = hex_rgb(color)
    return min(BASIC_RGB, key=lambda name: _distance(BASIC_RGB[name], rgb))


def nearest_256(color: str) -> str:
    """the nearest colour of the 256 colour palette as `h<index>`"""
    rgb = hex_rgb(color)
    levels = (0x00, 0x5F, 0x87, 0xAF, 0xD7, 0xFF)
    candidates = {
        16 + r * 36 + g * 6 + b: (levels[r], levels[g], levels[b])
        for r in range(6)
        for g in range(6)
        for b in range(6)
    }
    candidates.update({232 + i: (0x08 + 10 * i,) * 3 for i in range(24)})
    return "h" + str(min(candidates, key=lambda i: _distance(candidates[i], rgb)))


def blend(color: str, towards: str, amount: float) -> str:
    """`color` moved `amount` (0..1) of the way to `towards`, as #rrggbb"""
    a, b = hex_rgb(color), hex_rgb(towards)
    r, g, bl = (round(x * (1 - amount) + y * amount) for x, y in zip(a, b))
    return f"#{r:02x}{g:02x}{bl:02x}"


def is_semantic_theme(theme) -> bool:
    return isinstance(theme, dict) and "bg" in theme and "txt" in theme


# 16 colour fallbacks per role. Nothing that must be visible uses "black" or
# "dark gray": many terminal palettes (e.g. Solarized) map bright black to
# the background colour.
BASIC_FG = {
    True: {  # dark themes
        "txt": "", "lbl": "light gray", "dim": "dark cyan", "acc": "light blue",
        "grn": "light green", "red": "light red", "yel": "yellow", "blu": "light blue",
        "pur": "light magenta", "bg": "black",
    },
    False: {  # light themes
        "txt": "", "lbl": "dark blue", "dim": "dark cyan", "acc": "dark blue",
        "grn": "dark green", "red": "dark red", "yel": "brown", "blu": "dark blue",
        "pur": "dark magenta", "bg": "white",
    },
}  # fmt: skip
BASIC_BG = {
    True: {
        "bg": "", "row": "dark blue", "pop": "dark blue", "btn": "dark cyan",
        "fld2": "dark blue", "errbg": "dark red", "acc": "dark cyan", "grn": "dark green",
        "lbl": "light gray", "heat1": "", "heat2": "dark blue", "heat3": "dark cyan",
    },
    False: {
        "bg": "", "row": "light gray", "pop": "light gray", "btn": "light gray",
        "fld2": "light gray", "errbg": "dark red", "acc": "dark blue", "grn": "dark green",
        "lbl": "dark blue", "heat1": "", "heat2": "light gray", "heat3": "dark cyan",
    },
}  # fmt: skip
# foreground on these fills is fixed (readable on the fill's 16 colour value)
BASIC_FG_ON = {"errbg": "white", "acc": "white", "grn": "white", "lbl": "white"}


def expand_theme(
    semantic: dict,
    color_mode: str = "rgb",
    names: list[str] | None = None,
    transparent: bool = False,
) -> list[tuple[str, ...]]:
    """a full urwid palette from a semantic theme (see ROLES)

    :param transparent: keep the terminal's background (for `dark`/`light`):
        entries on the background get no background colour
    """
    dark_theme = luminance(semantic["bg"]) < 128
    semantic = dict(semantic)
    for key, amount in HEAT_TINTS.items():
        semantic.setdefault(key, blend(semantic["bg"], semantic["acc"], amount))

    def high(role: str, background: bool = False) -> str:
        if background and transparent and role == "bg":
            return ""
        color = semantic.get(role, semantic["txt"])
        return nearest_256(color) if color_mode.startswith("256") else color

    def basic_fg(role: str, bg_role: str) -> str:
        if bg_role in BASIC_FG_ON:
            return BASIC_FG_ON[bg_role]
        table = BASIC_FG[dark_theme]
        if role in table and role not in ("acc", "blu", "grn", "red", "yel", "pur"):
            return table[role]
        name = nearest_basic(semantic.get(role, semantic["txt"]))
        if name in ("black", "dark gray", "white", "light gray") or role not in table:
            return table.get(role, "")
        return name

    palette = []
    if names is None:
        names = list(dict.fromkeys([entry[0] for entry in dark] + ["body"]))
    for name in names:
        fg_role, bg_role, settings = ROLES.get(name, ("txt", "bg", ""))
        fg16 = ",".join(filter(None, [basic_fg(fg_role, bg_role), settings]))
        bg16 = BASIC_BG[dark_theme].get(bg_role, "")
        fg_high = ",".join(filter(None, [high(fg_role), settings]))
        palette.append((name, fg16, bg16, None, fg_high, high(bg_role, background=True)))
    return palette


def theme_is_dark(theme, name: str = "") -> bool:
    if is_semantic_theme(theme):
        return luminance(theme["bg"]) < 128
    return "light" not in name and name != "paper"


# Credits: retrobox and retrobox-light are the colours of Vim's retrobox
# colour scheme by Maxim Kim (https://github.com/vim/colorschemes, values
# checked against vim91/colors/retrobox.vim), which is ported from Lifepillar's
# gruvbox8 (https://github.com/lifepillar/vim-gruvbox8), after gruvbox by
# morhetz (https://github.com/morhetz/gruvbox). ink, fjord, ember and paper are
# original for khal.
SEMANTIC_THEMES: dict[str, dict] = {
    "retrobox": {
        "bg": "#1c1c1c",
        "dim": "#7c6f64",
        "lbl": "#a89984",
        "txt": "#ebdbb2",
        "acc": "#fe8019",
        "grn": "#b8bb26",
        "blu": "#83a598",
        "red": "#fb5944",
        "yel": "#fabd2f",
        "pur": "#d3869b",
        "row": "#303030",
        "pop": "#3c3836",
        "btn": "#3c3836",
        "fld2": "#504945",
        "errbg": "#5a1f1a",
        "cal": ["#8ec07c", "#83a598", "#d3869b", "#fabd2f"],
        "calfg": "#1c1c1c",
    },  # fmt: skip
    "retrobox-light": {
        "bg": "#fbf1c7",
        "dim": "#a89984",
        "lbl": "#7c6f64",
        "txt": "#3c3836",
        "acc": "#ff5f00",
        "grn": "#79740e",
        "blu": "#076678",
        "red": "#9d0006",
        "yel": "#b57614",
        "pur": "#8f3f71",
        "row": "#e5d4b1",
        "pop": "#e5d4b1",
        "btn": "#e5d4b1",
        "fld2": "#bdae93",
        "errbg": "#f2c9b8",
        "cal": ["#427b58", "#076678", "#8f3f71", "#b57614"],
        "calfg": "#fbf1c7",
    },  # fmt: skip
    "ink": {
        "bg": "#16181c",
        "dim": "#5a606b",
        "lbl": "#9097a3",
        "txt": "#dfe2e7",
        "acc": "#f2a541",
        "grn": "#8fc78a",
        "blu": "#7aa7e8",
        "red": "#ef6f6c",
        "yel": "#e8c766",
        "pur": "#c39be6",
        "row": "#22262d",
        "pop": "#2a2f37",
        "btn": "#2a2f37",
        "fld2": "#343a44",
        "errbg": "#4a2124",
        "cal": ["#7dc7b5", "#7aa7e8", "#e78fb3", "#e8c766"],
        "calfg": "#16181c",
    },  # fmt: skip
    "fjord": {
        "bg": "#0d1620",
        "dim": "#4c6075",
        "lbl": "#8aa0b8",
        "txt": "#d6e2ef",
        "acc": "#5fd0e6",
        "grn": "#7fd1a7",
        "blu": "#7ba7ff",
        "red": "#ff7a85",
        "yel": "#f4cf73",
        "pur": "#b9a3ff",
        "row": "#15263a",
        "pop": "#1b3049",
        "btn": "#1b3049",
        "fld2": "#234065",
        "errbg": "#4a1e2a",
        "cal": ["#5fd0e6", "#7ba7ff", "#b9a3ff", "#7fd1a7"],
        "calfg": "#0d1620",
    },  # fmt: skip
    "ember": {
        "bg": "#1a1412",
        "dim": "#6e5d55",
        "lbl": "#a8968b",
        "txt": "#efe3d3",
        "acc": "#ff8a5c",
        "grn": "#b5c46a",
        "blu": "#8db4c9",
        "red": "#ff6b6b",
        "yel": "#f2c46d",
        "pur": "#d49ac2",
        "row": "#271e1a",
        "pop": "#33271f",
        "btn": "#33271f",
        "fld2": "#45342a",
        "errbg": "#55201d",
        "cal": ["#e6a35c", "#8db4c9", "#d49ac2", "#b5c46a"],
        "calfg": "#1a1412",
    },  # fmt: skip
    "paper": {
        "bg": "#f5f2ea",
        "dim": "#a39e92",
        "lbl": "#6f6a5f",
        "txt": "#2a2823",
        "acc": "#c2541a",
        "grn": "#5e7d1f",
        "blu": "#2f6ab3",
        "red": "#b8322f",
        "yel": "#a27a0a",
        "pur": "#8a4fa3",
        "row": "#e9e3d4",
        "pop": "#e2dccb",
        "btn": "#e2dccb",
        "fld2": "#d8cfb8",
        "errbg": "#f3d3cc",
        "cal": ["#cfe0a8", "#bcd3f2", "#e2c6ec", "#f1dca0"],
        "calfg": "#2a2823",
    },  # fmt: skip
}

themes.update(SEMANTIC_THEMES)  # type: ignore[arg-type]
for _palette in (dark, light):
    _palette.append(("body", "", ""))


# -- the new UI parts (editor, floating boxes, messages, details, heat) in the
# built-in `dark` and `light` themes: generated from neutral semantic colours,
# with fixed high colours (so 256/rgb terminals don't depend on the terminal's
# ANSI palette) and the terminal's own background
NEUTRAL_DARK = {
    "bg": "#000000", "txt": "#e4e4e4", "lbl": "#b2b2b2", "dim": "#8a8a8a", "acc": "#5f87ff",
    "row": "#303a4a", "pop": "#262626", "btn": "#3a3a3a", "fld2": "#303030", "errbg": "#870000",
    "grn": "#87d787", "blu": "#5fafff", "red": "#ff5f5f", "yel": "#ffd75f", "pur": "#d787ff",
}  # fmt: skip
NEUTRAL_LIGHT = {
    "bg": "#ffffff", "txt": "#1c1c1c", "lbl": "#4e4e4e", "dim": "#7a7a7a", "acc": "#005fd7",
    "row": "#dadada", "pop": "#e4e4e4", "btn": "#d0d0d0", "fld2": "#e4e4e4", "errbg": "#ffd7d7",
    "grn": "#008700", "blu": "#005faf", "red": "#af0000", "yel": "#af8700", "pur": "#8700af",
}  # fmt: skip
NEW_UI_PREFIXES = (
    "editor ", "float ", "message ", "footer key", "footer version", "footer deleted", "details ",
    "timegrid deleted",
    "attendee ", "day heat ", "agenda ", "finder ", "log ", "header ", "frame title",
    "frame hint", "frame warning",
)  # fmt: skip
NEW_UI_NAMES = [name for name in ROLES if name.startswith(NEW_UI_PREFIXES)]
dark.extend(expand_theme(NEUTRAL_DARK, names=NEW_UI_NAMES, transparent=True))
light.extend(expand_theme(NEUTRAL_LIGHT, names=NEW_UI_NAMES, transparent=True))
