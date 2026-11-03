"""Restyle the report and add the cash flow page.

Run with Power BI Desktop closed. Rewrites the PBIR files under powerbi/GL_Analytics.Report:

- a new theme: light grey canvas, white rounded cards with a soft shadow, one palette
- a navy header band on every page
- even 24 px margins and 16 px gutters (visuals no longer touch or overlap)
- Performance and Budget variance pages re-laid out with KPI cards that show the change
  against last year or budget in green or red
- a revenue mix donut, a colour-graded receivables ageing chart
- a new Cash flow page (waterfall, statement, bank balance trend, monthly operating cash)
- the Checks page hidden in reading view

The measures it uses (Cash Flow, KPI Labels folders) live in the semantic model.
It re-grids the hand-built layout, so run it once; to run it again, restore the report from
powerbi/backup first.

    python scripts/restyle_report.py                                      light style
    python scripts/restyle_report.py --dark                               dark navy style
    python scripts/restyle_report.py --report GL_Analytics_Light.Report   another report folder
"""
import argparse
import json
import secrets
import shutil
from pathlib import Path

ARGS = argparse.ArgumentParser()
ARGS.add_argument("--dark", action="store_true", help="dark navy style")
ARGS.add_argument("--root", default=str(Path(__file__).resolve().parents[1] / "powerbi"))
ARGS.add_argument("--report", default="GL_Analytics.Report")
ARGS = ARGS.parse_args()

ROOT = Path(ARGS.root)
REPORT = ROOT / ARGS.report
PAGES = REPORT / "definition" / "pages"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/visualContainer/2.13.0/schema.json"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
M_TABLE = "Measures (2)"

LIGHT = dict(
    PRIMARY="#1F3A5F", TEAL="#2A9D8F", AMBER="#E9A23B", RED="#C8553D", SLATE="#6C7A89", PY="#C5CED8",
    EXTRA=["#8AB6D6", "#B5838D", "#4F6D7A"],
    CANVAS="#F2F4F8", CARD="#FFFFFF", BORDER="#E1E6EE", SHADOW="#1F3A5F", SHADOW_T=88,
    INK="#1B2B41", BODY="#3C4650", MUTED="#6B7785", AXIS="#5B6775", GRID="#E3E8EF",
    HEADER="#14263D", HEADER_SUB="#A9BCD3", VALUE="#1F3A5F",
    TABLE_HEAD="#EEF2F7", TABLE_LINE="#EDF0F4", TABLE_BAND="#F8FAFC", SUBTOTAL="#F4F6FA",
)
DARK = dict(
    PRIMARY="#4EA8DE", TEAL="#2EC4B6", AMBER="#F4A261", RED="#FF6B6B", SLATE="#8A9BB5", PY="#3A4A66",
    EXTRA=["#7BD389", "#C792EA", "#5C7CFA"],
    CANVAS="#0B1220", CARD="#131C2E", BORDER="#22304A", SHADOW="#000000", SHADOW_T=60,
    INK="#E8EEF7", BODY="#C3CEDF", MUTED="#8A9BB5", AXIS="#8A9BB5", GRID="#1F2B42",
    HEADER="#0F1A2E", HEADER_SUB="#2EC4B6", VALUE="#FFFFFF",
    TABLE_HEAD="#1A2540", TABLE_LINE="#1E2A40", TABLE_BAND="#162036", SUBTOTAL="#1A2540",
)
P = DARK if ARGS.dark else LIGHT
NAVY, TEAL, AMBER, RED, SLATE = P["PRIMARY"], P["TEAL"], P["AMBER"], P["RED"], P["SLATE"]
CANVAS, INK, MUTED, HEADER = P["CANVAS"], P["INK"], P["MUTED"], P["HEADER"]

PAGE_IDS = {
    "Performance": "aa78538ba812cf77f500",
    "Budget variance": "7daf83f8642cbadfdeaa",
    "Balance sheet": "1ceaabbca245cd4a030e",
    "Journal testing": "67c7e44225842bd83871",
    "Journal detail": "d1147fe52cbf1c9e7e46",
    "Checks": "b1666b96dd1523daa603",
}
CASH_PAGE = "c45f1a0b9e3d27c8a6f1"

HEADERS = {
    "Performance": ("Performance summary", "Revenue, margin and profit against budget and last year"),
    "Budget variance": ("Budget variance", "Which accounts and product lines drive the gap to budget"),
    "Balance sheet": ("Balance sheet and working capital", "Year-end position and where cash is tied up"),
    "Cash flow": ("Cash flow", "From profit to cash: where the money went"),
    "Journal testing": ("Journal entry testing", "Manual journals and payments that fail audit tests"),
    "Journal detail": ("Journal detail", "The full double entry behind a flagged journal"),
}

# Old colours used by hand-built visuals, mapped onto the theme palette.
COLOUR_MAP = {
    "#1A7F37": TEAL, "#C62828": RED, "#1F4E79": NAVY, "#E08A00": AMBER,
    "#808080": SLATE, "#BFBFBF": P["PY"], "#000000": INK,
}


# ---------------------------------------------------------------- helpers
def L(value):
    return {"expr": {"Literal": {"Value": value}}}


def text(s):
    return L("'" + s.replace("'", "''") + "'")


def M(name):
    return {"Measure": {"Expression": {"SourceRef": {"Entity": M_TABLE}}, "Property": name}}


def C(entity, column):
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": column}}


def solid(hex_):
    return {"solid": {"color": L(f"'{hex_}'")}}


def solid_m(measure):
    return {"solid": {"color": {"expr": M(measure)}}}


def proj(field, display=None):
    kind = next(iter(field))
    ref = f"{field[kind]['Expression']['SourceRef']['Entity']}.{field[kind]['Property']}"
    p = {"field": field, "queryRef": ref, "nativeQueryRef": display or field[kind]["Property"]}
    if display:
        p["displayName"] = display
    if kind == "Column":
        p["active"] = True
    return p


def new_id():
    return secrets.token_hex(10)


def container(title=None, note=None, note_colour=None):
    vco = {"title": [{"properties": {"show": L("true" if title else "false")}}]}
    if title:
        vco["title"][0]["properties"]["text"] = text(title)
    if note:
        props = {"show": L("true"), "text": {"expr": M(note)}, "fontSize": L("12D")}
        if note_colour:
            props["fontColor"] = solid_m(note_colour)
        vco["subTitle"] = [{"properties": props}]
    return vco


def visual(x, y, w, h, vtype, query=None, objects=None, vco=None, sort=None, z=1000, name=None):
    v = {"visualType": vtype}
    if query:
        v["query"] = {"queryState": query}
        if sort:
            v["query"]["sortDefinition"] = {"sort": sort, "isDefaultSort": True}
    if objects:
        v["objects"] = objects
    if vco:
        v["visualContainerObjects"] = vco
    v["drillFilterOtherVisuals"] = True
    name = name or new_id()
    return {
        "$schema": SCHEMA,
        "name": name,
        "position": {"x": x, "y": y, "z": z, "height": h, "width": w, "tabOrder": z},
        "visual": v,
    }


def kpi(x, y, w, h, title, measure, note, colour=None, z=2000):
    objects = {
        "label": [{"properties": {"show": L("false")}, "selector": {"id": "default"}}],
        "value": [{"properties": {"fontSize": L("30D"), "fontColor": solid(P["VALUE"])}, "selector": {"id": "default"}}],
    }
    return visual(x, y, w, h, "cardVisual", {"Data": {"projections": [proj(M(measure), title)]}},
                  objects, container(title, note, colour), z=z)


def header(page_key, name=None):
    title, sub = HEADERS[page_key]
    paragraphs = [
        {"textRuns": [
            {"value": title, "textStyle": {"fontFamily": "Segoe UI Semibold", "fontSize": "22pt", "color": "#FFFFFF"}},
            {"value": "     " + sub, "textStyle": {"fontFamily": "Segoe UI", "fontSize": "13pt", "color": P["HEADER_SUB"]}},
        ]},
    ]
    off = L("false")
    vco = {
        "title": [{"properties": {"show": off}}],
        "background": [{"properties": {"show": L("true"), "color": solid(HEADER), "transparency": L("0D")}}],
        "border": [{"properties": {"show": off}}],
        "dropShadow": [{"properties": {"show": off}}],
        "padding": [{"properties": {"top": L("14D"), "bottom": L("8D"), "left": L("28D"), "right": L("24D")}}],
    }
    return visual(0, 0, 1920, 72, "textbox", objects={"general": [{"properties": {"paragraphs": paragraphs}}]},
                  vco=vco, z=0, name=name)


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def visuals_of(page_id):
    out = {}
    for f in (PAGES / page_id / "visuals").glob("*/visual.json"):
        out[f.parent.name] = read(f)
    return out


def save_visual(page_id, v):
    write(PAGES / page_id / "visuals" / v["name"] / "visual.json", v)


def drop_visual(page_id, name):
    shutil.rmtree(PAGES / page_id / "visuals" / name)


def vtype(v):
    return v.get("visual", {}).get("visualType")


def measures_in(v):
    return json.dumps(v.get("visual", {}).get("query", {}))


def is_header(v):
    p = v["position"]
    return vtype(v) == "textbox" and p["y"] <= 1 and p["width"] >= 1900


# ------------------------------------------------------------------ theme
def write_theme():
    theme_file = REPORT / "StaticResources" / "RegisteredResources" / "GL_Analytics2835050582471734.json"
    theme = read(theme_file)
    theme["dataColors"] = [NAVY, TEAL, AMBER, RED, SLATE] + P["EXTRA"] + theme["dataColors"][8:]
    theme["background"] = P["CARD"]
    theme["backgroundLight"] = P["TABLE_BAND"]
    theme["backgroundNeutral"] = P["BORDER"]
    theme["foregroundNeutralSecondary"] = MUTED
    theme["foreground"] = INK
    theme["tableAccent"] = NAVY
    theme["textClasses"] = {
        "title": {"fontFace": "Segoe UI Semibold", "fontSize": 14, "color": INK},
        "header": {"fontFace": "Segoe UI Semibold", "fontSize": 12, "color": INK},
        "label": {"fontFace": "Segoe UI", "fontSize": 11, "color": P["BODY"]},
        "callout": {"fontFace": "Segoe UI Semibold", "fontSize": 30, "color": P["VALUE"]},
    }
    c = lambda h: {"solid": {"color": h}}
    theme["visualStyles"] = {
        "*": {"*": {
            "background": [{"show": True, "color": c(P["CARD"]), "transparency": 0}],
            "border": [{"show": True, "color": c(P["BORDER"]), "radius": 12, "width": 1}],
            "dropShadow": [{"show": True, "preset": "Custom", "position": "Outer", "color": c(P["SHADOW"]),
                            "transparency": P["SHADOW_T"], "shadowBlur": 14, "shadowDistance": 3, "shadowSpread": 0,
                            "angle": 90}],
            "padding": [{"top": 14, "bottom": 14, "left": 18, "right": 18}],
            "title": [{"show": True, "fontColor": c(INK), "fontSize": 14, "bold": True,
                       "fontFamily": "'Segoe UI Semibold', wf_segoe-ui_semibold, helvetica, arial, sans-serif"}],
            "subTitle": [{"show": False, "fontColor": c(MUTED), "fontSize": 11}],
            "categoryAxis": [{"gridlineShow": False, "labelColor": c(P["AXIS"]), "fontSize": 11}],
            "valueAxis": [{"gridlineShow": True, "gridlineStyle": "dotted", "gridlineColor": c(P["GRID"]),
                           "labelColor": c(P["AXIS"]), "fontSize": 11}],
            "legend": [{"labelColor": c(P["BODY"]), "fontSize": 11}],
            "labels": [{"color": c(P["BODY"]), "fontSize": 11}],
        }},
        "cardVisual": {"*": {
            "outline": [{"$id": "default", "show": False}],
            "borderCustom": [{"$id": "default", "show": False}],
        }},
        "lineChart": {"*": {"lineStyles": [{"lineChartType": "linear"}]}},
        "areaChart": {"*": {"lineStyles": [{"lineChartType": "linear"}]}},
        "lineClusteredColumnComboChart": {"*": {"lineStyles": [{"lineChartType": "linear"}]}},
        "page": {"*": {
            "background": [{"color": c(CANVAS), "transparency": 0}],
            "outspace": [{"color": c(CANVAS), "transparency": 0}],
        }},
        "tableEx": {"*": {
            "columnHeaders": [{"backColor": c(P["TABLE_HEAD"]), "fontColor": c(INK), "bold": True}],
            "grid": [{"gridHorizontal": True, "gridHorizontalColor": c(P["TABLE_LINE"]), "gridVertical": False,
                      "outlineColor": c(P["BORDER"]), "rowPadding": 4}],
            "values": [{"fontColorPrimary": c(P["BODY"]), "backColorPrimary": c(P["CARD"]),
                        "fontColorSecondary": c(P["BODY"]), "backColorSecondary": c(P["TABLE_BAND"])}],
            "total": [{"fontColor": c(INK), "backColor": c(P["SUBTOTAL"])}],
        }},
        "pivotTable": {"*": {
            "columnHeaders": [{"backColor": c(P["TABLE_HEAD"]), "fontColor": c(INK), "bold": True}],
            "rowHeaders": [{"fontColor": c(P["BODY"]), "backColor": c(P["CARD"])}],
            "grid": [{"gridHorizontal": True, "gridHorizontalColor": c(P["TABLE_LINE"]), "gridVertical": False,
                      "outlineColor": c(P["BORDER"]), "rowPadding": 4}],
            "values": [{"fontColorPrimary": c(P["BODY"]), "backColorPrimary": c(P["CARD"]),
                        "fontColorSecondary": c(P["BODY"]), "backColorSecondary": c(P["CARD"])}],
            "subTotals": [{"fontColor": c(INK), "backColor": c(P["SUBTOTAL"])}],
        }},
        "slicer": {"*": {
            "header": [{"fontColor": c(INK), "fontSize": 13, "bold": True}],
            "items": [{"fontColor": c(P["BODY"]), "fontSize": 12}],
        }},
    }
    write(theme_file, theme)
    write(ROOT / "theme.json", {k: v for k, v in theme.items() if k != "dataColors"} | {"dataColors": theme["dataColors"][:8]})


# ------------------------------------------------------- generic restyle
def clean(v):
    """Remove per-visual container styling so the theme applies, and swap old colours."""
    vco = v.get("visual", {}).get("visualContainerObjects", {})
    for key in ("background", "border", "dropShadow", "padding", "spacing"):
        vco.pop(key, None)
    for t in vco.get("title", []):
        for k in ("fontSize", "bold", "italic", "fontColor", "fontFamily"):
            t.get("properties", {}).pop(k, None)
    for t in vco.get("subTitle", []):
        t.get("properties", {}).pop("fontSize", None)
    objects = v.get("visual", {}).get("objects", {})
    for ax in objects.get("categoryAxis", []):
        ax.get("properties", {}).pop("bold", None)
    for entry in objects.get("items", []):
        entry.get("properties", {}).pop("fontColor", None)
    for key in ("columnHeaders", "values", "rowHeaders"):
        for entry in objects.get(key, []):
            props = entry.get("properties", {})
            props.pop("backColorPrimary", None)
            if key == "columnHeaders":
                props.pop("fontColor", None)
            if "fontColorPrimary" in props and "ThemeDataColor" in json.dumps(props["fontColorPrimary"]):
                props.pop("fontColorPrimary")
    s = json.dumps(v, ensure_ascii=False)
    for old, new in COLOUR_MAP.items():
        s = s.replace(f"'{old}'", f"'{new}'").replace(f'"{old}"', f'"{new}"')
    return json.loads(s)


TEXT_CARDS = ("Selected Journal", "Flag Status")


def modernise_card(v):
    """Give a hand-built card the KPI look: its label becomes the card title, value in navy."""
    proj0 = v["visual"]["query"]["queryState"]["Data"]["projections"][0]
    title = proj0.get("displayName") or proj0["nativeQueryRef"]
    is_text = proj0["field"].get("Measure", {}).get("Property") in TEXT_CARDS
    objects = v["visual"].setdefault("objects", {})
    objects["label"] = [{"properties": {"show": L("false")}, "selector": {"id": "default"}}]
    objects["value"] = [{"properties": {"fontSize": L("18D" if is_text else "30D"), "fontColor": solid(P["VALUE"])},
                         "selector": {"id": "default"}}]
    v["visual"].setdefault("visualContainerObjects", {})["title"] = [
        {"properties": {"show": L("true"), "text": text(title)}}]
    return v


def transform(v, origin_y):
    """Map the old edge-to-edge grid onto a canvas with a 72 px header, 24 px margins and 16 px gutters."""
    p = v["position"]
    sx, sy = 1888 / 1920, (1072 - 80) / (1080 - origin_y)
    x0, y0 = 16 + p["x"] * sx, 80 + (p["y"] - origin_y) * sy
    x1, y1 = 16 + (p["x"] + p["width"]) * sx, 80 + (p["y"] + p["height"] - origin_y) * sy
    p.update(x=round(x0 + 8), y=round(y0 + 8), width=round(x1 - x0 - 16), height=round(y1 - y0 - 16))


def place(v, x, y, w, h):
    v["position"].update(x=x, y=y, width=w, height=h)


def page_background(page_id, hidden=False):
    f = PAGES / page_id / "page.json"
    page = read(f)
    page["objects"] = page.get("objects", {})
    page["objects"]["background"] = [{"properties": {"color": solid(CANVAS), "transparency": L("0D")}}]
    page["objects"]["outspace"] = [{"properties": {"color": solid(CANVAS), "transparency": L("0D")}}]
    if hidden:
        page["visibility"] = "HiddenInViewMode"
    write(f, page)


def restyle_page(key, fixes=None, origin_y=48):
    """Apply fixes (old-grid positions), clean styling, re-grid, and swap the header."""
    pid = PAGE_IDS[key]
    for name, v in visuals_of(pid).items():
        if is_header(v):
            drop_visual(pid, name)
            continue
        if fixes and name in fixes:
            place(v, *fixes[name])
        v = clean(v)
        if vtype(v) == "cardVisual":
            v = modernise_card(v)
        if vtype(v) == "actionButton":
            place(v, 1776, 16, 120, 40)
            v["position"]["z"] = 50000
        else:
            transform(v, origin_y)
        save_visual(pid, v)
    save_visual(pid, header(key))
    page_background(pid)


def find(pid, vt, contains=""):
    for name, v in visuals_of(pid).items():
        if vtype(v) == vt and contains in measures_in(v):
            return name
    raise LookupError(f"{vt} with {contains!r} not found on page {pid}")


# ----------------------------------------------------------- performance
def performance():
    key, pid = "Performance", PAGE_IDS["Performance"]
    keep = {}
    for name, v in visuals_of(pid).items():
        t = vtype(v)
        if t == "cardVisual" or is_header(v):
            drop_visual(pid, name)
        else:
            keep[name] = clean(v)
    combo = find(pid, "lineClusteredColumnComboChart")
    gm_line = find(pid, "lineChart", "Gross Margin %")
    region = find(pid, "clusteredBarChart", "Revenue (Cr)")
    slicer = find(pid, "slicer")
    findings = next(n for n, v in keep.items() if vtype(v) == "textbox")
    layout = {
        slicer: (24, 88, 248, 168),
        combo: (24, 272, 1240, 416),
        gm_line: (24, 704, 608, 352),
        region: (648, 704, 608, 352),
        findings: (1272, 704, 624, 352),
    }
    for name, pos in layout.items():
        place(keep[name], *pos)
        save_visual(pid, keep[name])

    cards = [
        ("Revenue (₹ Cr)", "Revenue (Cr)", "Revenue Note", "Revenue Note Colour"),
        ("Gross margin", "Gross Margin %", "Gross Margin Note", "Gross Margin Note Colour"),
        ("EBITDA (₹ Cr)", "EBITDA (Cr)", "EBITDA Note", "EBITDA Note Colour"),
        ("Profit after tax (₹ Cr)", "PAT (Cr)", "PAT Note", "PAT Note Colour"),
        ("EBITDA vs budget (₹ Cr)", "EBITDA Var (Cr)", "EBITDA Var Note", "EBITDA Var Colour"),
    ]
    xs = [288, 612, 936, 1260, 1584]
    for i, (title, measure, note, colour) in enumerate(cards):
        w = 1896 - xs[i] if i == 4 else 308
        save_visual(pid, kpi(xs[i], 88, w, 168, title, measure, note, colour, z=2000 + i))

    donut = visual(
        1280, 272, 616, 416, "donutChart",
        {"Category": {"projections": [proj(C("Account", "product_line"), "Product line")]},
         "Y": {"projections": [proj(M("Revenue (Cr)"), "Revenue ₹ Cr")]}},
        {"labels": [{"properties": {"show": L("true"), "labelStyle": text("Category, percent of total"),
                                    "fontSize": L("12D")}}],
         "legend": [{"properties": {"show": L("false")}}],
         "slices": [{"properties": {"innerRadiusRatio": L("60L")}}]},
        container("Revenue mix by product line"),
        sort=[{"field": M("Revenue (Cr)"), "direction": "Descending"}], z=3000)
    save_visual(pid, donut)
    save_visual(pid, header(key))
    page_background(pid)


# ------------------------------------------------------- budget variance
def budget_variance():
    key, pid = "Budget variance", PAGE_IDS["Budget variance"]
    vs = {n: clean(v) for n, v in visuals_of(pid).items()}
    layout = {
        find(pid, "slicer"): (24, 88, 248, 168),
        find(pid, "clusteredColumnChart", "Gross Margin %"): (24, 272, 928, 400),
        find(pid, "waterfallChart"): (24, 688, 928, 368),
        find(pid, "pivotTable"): (968, 88, 928, 752),
        next(n for n, v in vs.items() if vtype(v) == "textbox"): (968, 856, 928, 200),
    }
    for name, pos in layout.items():
        place(vs[name], *pos)
    gm = vs[find(pid, "clusteredColumnChart", "Gross Margin %")]
    for pr in gm["visual"]["query"]["queryState"]["Y"]["projections"]:
        label = "Last year" if pr["queryRef"].endswith("PY") else "This year"
        pr["displayName"] = pr["nativeQueryRef"] = label
    wf = vs[find(pid, "waterfallChart")]
    wf["visual"]["objects"]["categoryAxis"] = [{"properties": {"fontSize": L("11D")}}]
    wf["visual"]["objects"]["sentimentColors"][0]["properties"]["totalFill"] = solid(NAVY)
    for name in layout:
        save_visual(pid, vs[name])
    save_visual(pid, kpi(288, 88, 320, 168, "Revenue vs budget (₹ Cr)", "Revenue Var (Cr)",
                         "Revenue Var Note", "Revenue Var Colour", z=2000))
    save_visual(pid, kpi(624, 88, 328, 168, "EBITDA vs budget (₹ Cr)", "EBITDA Var (Cr)",
                         "EBITDA Var Note", "EBITDA Var Colour", z=2001))
    save_visual(pid, header(key))
    page_background(pid)


# --------------------------------------------------------- balance sheet
def balance_sheet():
    pid = PAGE_IDS["Balance sheet"]
    vs = visuals_of(pid)
    by = lambda t, c="": find(pid, t, c)
    fixes = {
        by("slicer"): (0, 48, 272, 208),
        by("pivotTable"): (0, 256, 768, 360),
        by("clusteredColumnChart"): (0, 616, 768, 464),
        by("tableEx"): (768, 256, 592, 472),
        by("cardVisual", "AR Rec Difference"): (1360, 256, 560, 472),
        by("lineChart"): (768, 728, 1152, 352),
        by("cardVisual", "Balance Sheet Check"): (1648, 48, 272, 208),
    }
    restyle_page("Balance sheet", fixes)
    # Colour the ageing buckets from teal (not due) to deep red (over 180 days).
    name = by("clusteredColumnChart")
    v = read(PAGES / pid / "visuals" / name / "visual.json")
    v["visual"]["objects"]["dataPoint"] = [{
        "properties": {"fill": solid_m("Ageing Colour")},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]},
    }]
    save_visual(pid, v)


def journal_testing():
    pid = PAGE_IDS["Journal testing"]
    cards = sorted((n for n, v in visuals_of(pid).items() if vtype(v) == "cardVisual"),
                   key=lambda n: visuals_of(pid)[n]["position"]["x"])
    fixes = {find(pid, "slicer"): (0, 48, 208, 168)}
    xs = [208, 529, 850, 1171, 1492]
    for i, n in enumerate(cards):
        fixes[n] = (xs[i], 48, 428 if i == 4 else 321, 168)
    fixes[find(pid, "clusteredBarChart", "check_label")] = (0, 216, 720, 504)
    fixes[find(pid, "clusteredBarChart", "user_name")] = (0, 720, 720, 360)
    fixes[find(pid, "tableEx")] = (720, 216, 1200, 864)
    restyle_page("Journal testing", fixes)


def journal_detail():
    pid = PAGE_IDS["Journal detail"]
    fixes = {}
    for n, v in visuals_of(pid).items():
        if vtype(v) == "tableEx" and "line_no" in measures_in(v):
            fixes[n] = (0, 432, 1920, 648)
        elif vtype(v) == "tableEx":
            fixes[n] = (0, 208, 1440, 224)
    restyle_page("Journal detail", fixes)


# ------------------------------------------------------------- cash flow
def cash_flow():
    key, pid = "Cash flow", CASH_PAGE
    folder = PAGES / pid
    if folder.exists():
        shutil.rmtree(folder)
    write(folder / "page.json", {
        "$schema": PAGE_SCHEMA, "name": pid, "displayName": "Cash flow",
        "displayOption": "FitToPage", "height": 1080, "width": 1920,
    })
    page_background(pid)
    save_visual(pid, header(key))

    # Year slicer: copy the Balance sheet one so the default selection matches.
    src = read(PAGES / PAGE_IDS["Balance sheet"] / "visuals" / find(PAGE_IDS["Balance sheet"], "slicer") / "visual.json")
    src = clean(src)
    src["name"] = new_id()
    place(src, 24, 88, 248, 168)
    save_visual(pid, src)

    cards = [
        ("Opening cash (₹ Cr)", "Opening Cash (Cr)", "Opening Cash Note", None),
        ("Cash from operations (₹ Cr)", "Cash from Operations (Cr)", "Operating Cash Note", "Operating Cash Colour"),
        ("Investing (₹ Cr)", "Cash from Investing (Cr)", "Investing Note", None),
        ("Financing (₹ Cr)", "Cash from Financing (Cr)", "Financing Note", None),
        ("Closing cash (₹ Cr)", "Bank Balance (Cr)", "Closing Cash Note", "Net Cash Colour"),
    ]
    xs = [288, 612, 936, 1260, 1584]
    for i, (title, measure, note, colour) in enumerate(cards):
        w = 1896 - xs[i] if i == 4 else 308
        save_visual(pid, kpi(xs[i], 88, w, 168, title, measure, note, colour, z=2000 + i))

    line = C("Cash Flow Line", "cf_line")
    labels2 = {"show": L("true"), "labelPrecision": L("2L"), "fontSize": L("12D")}
    save_visual(pid, visual(
        24, 272, 1180, 440, "waterfallChart",
        {"Category": {"projections": [proj(line, "Line")]},
         "Y": {"projections": [proj(M("Cash Flow (Cr)"), "₹ Cr")]}},
        {"sentimentColors": [{"properties": {"increaseFill": solid(TEAL), "decreaseFill": solid(RED),
                                             "totalFill": solid(NAVY)}}],
         "labels": [{"properties": labels2}],
         "legend": [{"properties": {"show": L("false")}}],
         "categoryAxis": [{"properties": {"fontSize": L("12D")}}],
         "valueAxis": [{"properties": {"showAxisTitle": L("false")}}]},
        container("From profit to cash: movement in the year (₹ Cr)"),
        sort=[{"field": line, "direction": "Ascending"}], z=3000))

    save_visual(pid, visual(
        1220, 272, 676, 440, "pivotTable",
        {"Rows": {"projections": [proj(C("Cash Flow Line", "cf_section"), "Cash flow"), proj(line, "Line")]},
         "Values": {"projections": [proj(M("Cash Flow (Cr)"), "This year"),
                                    proj(M("Cash Flow PY (Cr)"), "Last year")]}},
        {"values": [{"properties": {"fontSize": L("13D")}},
                    {"properties": {"fontColor": solid_m("Cash Flow Colour")},
                     "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                  "metadata": f"{M_TABLE}.Cash Flow (Cr)"}}],
         "columnHeaders": [{"properties": {"fontSize": L("13D")}}],
         "rowHeaders": [{"properties": {"fontSize": L("13D")}}],
         "subTotals": [{"properties": {"rowSubtotals": L("true")}}]},
        container("Cash flow statement (₹ Cr)"), z=3001))

    month = C("Date", "month_label")
    save_visual(pid, visual(
        24, 728, 928, 328, "areaChart",
        {"Category": {"projections": [proj(month, "Month")]},
         "Y": {"projections": [proj(M("Bank Balance (Cr)"), "Bank balance ₹ Cr")]}},
        {"dataPoint": [{"properties": {"fill": solid(NAVY)}}],
         "labels": [{"properties": {"show": L("true"), "labelPrecision": L("1L"), "fontSize": L("10D")}}],
         "legend": [{"properties": {"show": L("false")}}],
         "valueAxis": [{"properties": {"showAxisTitle": L("false")}}],
         "categoryAxis": [{"properties": {"showAxisTitle": L("false")}}]},
        container("Bank balance at each month end (₹ Cr)"), z=3002))

    save_visual(pid, visual(
        968, 728, 928, 328, "clusteredColumnChart",
        {"Category": {"projections": [proj(month, "Month")]},
         "Y": {"projections": [proj(M("Cash from Operations (Cr)"), "Operating cash ₹ Cr")]}},
        {"dataPoint": [{"properties": {"fill": solid_m("Operating Cash Colour")},
                        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}]}}],
         "labels": [{"properties": {"show": L("true"), "labelPrecision": L("1L"), "fontSize": L("10D")}}],
         "legend": [{"properties": {"show": L("false")}}],
         "valueAxis": [{"properties": {"showAxisTitle": L("false")}}],
         "categoryAxis": [{"properties": {"showAxisTitle": L("false")}}]},
        container("Cash from operations by month (₹ Cr)"), z=3003))


def page_order():
    f = PAGES / "pages.json"
    meta = read(f)
    meta["pageOrder"] = [PAGE_IDS["Performance"], PAGE_IDS["Budget variance"], PAGE_IDS["Balance sheet"],
                         CASH_PAGE, PAGE_IDS["Journal testing"], PAGE_IDS["Journal detail"], PAGE_IDS["Checks"]]
    meta["activePageName"] = PAGE_IDS["Performance"]
    write(f, meta)


def main():
    write_theme()
    performance()
    budget_variance()
    balance_sheet()
    journal_testing()
    journal_detail()
    cash_flow()
    page_background(PAGE_IDS["Checks"], hidden=True)
    page_order()
    print("Report restyled. Open powerbi/GL_Analytics.pbip to review.")


if __name__ == "__main__":
    main()
