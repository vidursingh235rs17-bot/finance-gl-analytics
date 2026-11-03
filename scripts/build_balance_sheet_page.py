"""Generate the 'Balance sheet' report page (PBIR format) for GL_Analytics.pbip.

Formatting is copied from the existing 'Performance' page so all pages match.
If the page already exists, visuals keep the positions they have there, so a
layout adjusted by hand in Power BI Desktop survives a rebuild.

Run with Power BI Desktop closed (save first):
    python scripts/build_balance_sheet_page.py
Then reopen powerbi/GL_Analytics.pbip.
"""
import copy
import json
import secrets
import shutil
import sys
from pathlib import Path

REPORT = Path(__file__).resolve().parent.parent / "powerbi" / "GL_Analytics.Report" / "definition"
PAGES = REPORT / "pages"
PAGE_SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json"
MEASURES = "Measures (2)"
PAGE_NAME = "Balance sheet"
STYLE_PAGE = "Performance"


def new_id():
    return secrets.token_hex(10)


def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def text(value):
    return lit("'" + value.replace("'", "''") + "'")


def color(hex_code):
    return {"solid": {"color": lit("'" + hex_code + "'")}}


def column(entity, prop, display=None, active=False):
    p = {
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
        "queryRef": f"{entity}.{prop}",
        "nativeQueryRef": display or prop,
    }
    if display:
        p["displayName"] = display
    if active:
        p["active"] = True
    return p


def measure(prop, display=None):
    p = {
        "field": {"Measure": {"Expression": {"SourceRef": {"Entity": MEASURES}}, "Property": prop}},
        "queryRef": f"{MEASURES}.{prop}",
        "nativeQueryRef": display or prop,
    }
    if display:
        p["displayName"] = display
    return p


# ---------------------------------------------------------------- style source
def load_page(display_name):
    for page_dir in PAGES.iterdir():
        page_file = page_dir / "page.json"
        if page_file.exists():
            page = json.loads(page_file.read_text(encoding="utf-8"))
            if page.get("displayName", "").strip().lower() == display_name.lower():
                return page_dir
    return None


def load_visuals(page_dir):
    out = []
    for f in (page_dir / "visuals").glob("*/visual.json"):
        out.append(json.loads(f.read_text(encoding="utf-8")))
    return out


def first_of(visuals, visual_type):
    for v in visuals:
        if v["visual"]["visualType"] == visual_type:
            return copy.deepcopy(v)
    sys.exit(f"No {visual_type} on the '{STYLE_PAGE}' page to copy formatting from.")


def measure_expr(prop):
    return {"expr": {"Measure": {"Expression": {"SourceRef": {"Entity": MEASURES}}, "Property": prop}}}


def chart_frame(style_chart, title=None, title_measure=None):
    """Container formatting (border, padding, title size) of the Performance charts.
    title_measure makes the title follow the slicer (a text measure)."""
    vco = copy.deepcopy(style_chart["visual"].get("visualContainerObjects", {}))
    title_text = measure_expr(title_measure) if title_measure else text(title)
    vco["title"] = [{"properties": {"show": lit("true"), "text": title_text, "titleWrap": lit("true"),
                                    "fontSize": lit("20D"), "bold": lit("true"), "italic": lit("false")}}]
    vco["subTitle"] = [{"properties": {"show": lit("false")}}]
    return vco


# ---------------------------------------------------------------- visuals
def build_visuals(style):
    slicer_tpl = first_of(style, "slicer")
    card_tpl = next(v for v in style if v["visual"]["visualType"] == "cardVisual")
    line_tpl = first_of(style, "lineChart")
    header_tpl = next(v for v in style if v["visual"]["visualType"] == "textbox"
                      and "Performance summary" in json.dumps(v, ensure_ascii=False))
    axis_style = line_tpl["visual"]["objects"]["categoryAxis"]
    legend_style = line_tpl["visual"]["objects"]["legend"]

    specs = []  # (key, default position, visual dict, extra container keys)

    header = copy.deepcopy(header_tpl["visual"])
    header["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = \
        "Balance sheet & working capital – Northfield Industrial Supplies"
    specs.append(("header", (0, 0, 1920, 48), header, {}))

    # Same slicer as Performance: synced year, FY2025-26 selected, (Blank) hidden.
    slicer = copy.deepcopy(slicer_tpl["visual"])
    specs.append(("slicer", (0, 48, 264, 168), slicer, {"filterConfig": slicer_tpl.get("filterConfig")}))

    cards = [
        ("Bank Balance (Cr)", "Bank ₹ Cr"),
        ("Net Working Capital (Cr)", "Net working capital ₹ Cr"),
        ("Borrowings (Cr)", "Borrowings ₹ Cr"),
        ("DSO", "DSO days"),
        ("DIO", "DIO days"),
        ("Balance Sheet Check", "BS check (= 0)"),
    ]
    card_w = (1920 - 272) // len(cards)
    for i, (prop, label) in enumerate(cards):
        v = copy.deepcopy(card_tpl["visual"])
        v["query"] = {"queryState": {"Data": {"projections": [measure(prop, label)]}}}
        specs.append((f"card|{prop}", (272 + i * card_w, 48, card_w - 8, 168), v, {}))

    matrix = {
        "visualType": "pivotTable",
        "query": {"queryState": {
            "Rows": {"projections": [column("Account", "account_class", "Balance sheet line", True),
                                     column("Account", "account_name")]},
            "Values": {"projections": [measure("BS Year End (Cr)", "Year end ₹ Cr"),
                                       measure("BS Previous Year End (Cr)", "Year earlier ₹ Cr"),
                                       measure("BS Change (Cr)", "Change ₹ Cr")]},
        }},
        "objects": {
            "values": [{"properties": {"fontSize": lit("15D")}}],
            "columnHeaders": [{"properties": {"fontSize": lit("15D"), "bold": lit("true")}}],
            "rowHeaders": [{"properties": {"fontSize": lit("15D"), "bold": lit("false")}}],
            "grid": [{"properties": {"rowPadding": lit("1D")}}],
        },
        "visualContainerObjects": chart_frame(line_tpl, "Balance sheet (₹ crore) – year end vs a year earlier"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("matrix", (0, 224, 752, 856), matrix, {}))

    line = {
        "visualType": "lineChart",
        "query": {"queryState": {
            "Category": {"projections": [column("Date", "month_label", None, True)]},
            "Y": {"projections": [measure("DSO", "DSO (days)"), measure("DIO", "DIO (days)")]},
        }},
        "objects": {
            "dataPoint": [{"properties": {"fill": color("#1F4E79")}, "selector": {"metadata": f"{MEASURES}.DSO"}},
                          {"properties": {"fill": color("#E08A00")}, "selector": {"metadata": f"{MEASURES}.DIO"}}],
            "labels": [{"properties": {"show": lit("true"), "labelPrecision": lit("0L")}}],
            "categoryAxis": copy.deepcopy(axis_style),
            "valueAxis": [{"properties": {"showAxisTitle": lit("false")}}],
            "legend": copy.deepcopy(legend_style),
        },
        "visualContainerObjects": chart_frame(line_tpl, "DSO & DIO by month (days)"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("line", (760, 224, 1160, 400), line, {"filterConfig": {"filters": [month_filter()]}}))

    ageing = {
        "visualType": "clusteredColumnChart",
        "query": {
            "queryState": {
                "Category": {"projections": [column("AR Ageing Bucket", "ageing_bucket", "Days past due", True)]},
                "Y": {"projections": [measure("Open AR (As At Cr)", "Open AR ₹ Cr")]},
            },
            "sortDefinition": {"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "AR Ageing Bucket"}},
                                                              "Property": "ageing_bucket"}},
                                         "direction": "Ascending"}], "isDefaultSort": False},
        },
        "objects": {
            "dataPoint": [{"properties": {"fill": color("#1F4E79")}}],
            "labels": [{"properties": {"show": lit("true"), "labelPrecision": lit("2L")}}],
            "categoryAxis": copy.deepcopy(axis_style),
            "valueAxis": [{"properties": {"showAxisTitle": lit("false")}}],
            "legend": [{"properties": {"show": lit("false")}}],
        },
        "visualContainerObjects": chart_frame(line_tpl, title_measure="AR Ageing Title"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("ageing", (760, 632, 576, 448), ageing, {}))

    sort_field = {"Measure": {"Expression": {"SourceRef": {"Entity": MEASURES}},
                              "Property": "Overdue over 90 Days (As At L)"}}
    table = {
        "visualType": "tableEx",
        "query": {
            "queryState": {"Values": {"projections": [
                column("Customer", "customer_name", "Customer"),
                measure("Overdue over 90 Days (As At L)", "Over 90 days ₹ L"),
            ]}},
            "sortDefinition": {"sort": [{"field": sort_field, "direction": "Descending"}], "isDefaultSort": False},
        },
        "objects": {
            "values": [{"properties": {"fontSize": lit("15D")}}],
            "columnHeaders": [{"properties": {"fontSize": lit("15D"), "bold": lit("true")}}],
        },
        "visualContainerObjects": chart_frame(line_tpl, title_measure="Overdue Title"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("table", (1344, 632, 576, 288), table, {}))

    rec = copy.deepcopy(card_tpl["visual"])
    rec["query"] = {"queryState": {"Data": {"projections": [
        measure("AR Rec Difference (As At L)", "AR: ledger less invoice list ₹ L")]}}}
    specs.append(("card|AR Reconciliation Difference", (1344, 928, 576, 152), rec, {}))
    return specs


def month_filter():
    """Hide Apr and May 2024: a 3-month DSO/DIO needs three months of history."""
    ml = {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "month_label"}}
    return {
        "name": new_id(),
        "field": {"Column": {"Expression": {"SourceRef": {"Entity": "Date"}}, "Property": "month_label"}},
        "type": "Categorical",
        "filter": {
            "Version": 2,
            "From": [{"Name": "d", "Entity": "Date", "Type": 0}],
            "Where": [{"Condition": {"Not": {"Expression": {"In": {
                "Expressions": [ml],
                "Values": [[{"Literal": {"Value": "'Apr 2024'"}}], [{"Literal": {"Value": "'May 2024'"}}]],
            }}}}}],
        },
        "objects": {"general": [{"properties": {"isInvertedSelectionMode": lit("true")}}]},
    }


def visual_key(doc):
    """Stable key used to carry positions over from an earlier build."""
    v = doc["visual"]
    vt = v["visualType"]
    if vt == "cardVisual":
        prop = v["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]["Property"]
        if prop.startswith(("AR Rec", "AR Reconciliation")):
            return "card|AR Reconciliation Difference"
        return "card|" + prop
    return {"textbox": "header", "slicer": "slicer", "pivotTable": "matrix", "lineChart": "line",
            "clusteredColumnChart": "ageing", "tableEx": "table"}.get(vt, vt)


def main():
    style_dir = load_page(STYLE_PAGE)
    if not style_dir:
        sys.exit(f"Page '{STYLE_PAGE}' not found under {PAGES}")
    specs = build_visuals(load_visuals(style_dir))

    pages_json = PAGES / "pages.json"
    meta = json.loads(pages_json.read_text(encoding="utf-8"))

    # Keep positions from an existing copy of the page, then remove it.
    kept = {}
    for page_dir in [p for p in PAGES.iterdir() if p.is_dir()]:
        page_file = page_dir / "page.json"
        name = json.loads(page_file.read_text(encoding="utf-8")).get("displayName", "") if page_file.exists() else ""
        if not page_file.exists() or name.strip().lower() == PAGE_NAME.lower():
            if page_file.exists() and (page_dir / "visuals").exists():
                for doc in load_visuals(page_dir):
                    kept[visual_key(doc)] = doc["position"]
            print(f"Replacing page folder {page_dir.name} ({name or 'empty'})")
            shutil.rmtree(page_dir)
    meta["pageOrder"] = [p for p in meta["pageOrder"] if (PAGES / p).is_dir()]

    page_id = new_id()
    page_dir = PAGES / page_id
    (page_dir / "visuals").mkdir(parents=True)

    for z, (key, (x, y, w, h), visual, extra) in enumerate(specs):
        position = kept.get(key) or {"x": x, "y": y, "z": z * 100, "height": h, "width": w, "tabOrder": z * 100}
        vid = new_id()
        doc = {"$schema": copy.deepcopy(next(iter(load_visuals(style_dir))))["$schema"],
               "name": vid, "position": position, "visual": visual}
        doc.update({k: val for k, val in extra.items() if val})
        (page_dir / "visuals" / vid).mkdir()
        (page_dir / "visuals" / vid / "visual.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {key:<40} {'kept position' if key in kept else 'default position'}")

    page = {"$schema": PAGE_SCHEMA, "name": page_id, "displayName": PAGE_NAME,
            "displayOption": "FitToPage", "height": 1080, "width": 1920}
    (page_dir / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False), encoding="utf-8")

    meta["pageOrder"].append(page_id)
    meta["activePageName"] = page_id
    pages_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created page '{PAGE_NAME}' ({page_id}) with {len(specs)} visuals.")


if __name__ == "__main__":
    main()
