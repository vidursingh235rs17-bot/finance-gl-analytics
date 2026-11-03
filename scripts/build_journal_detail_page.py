"""Generate the 'Journal detail' drill-through page (PBIR format) for GL_Analytics.pbip.

After the first build, open the page in Power BI Desktop and drag Journal[journal_id]
into the 'Drill through' well of the Build visual pane (one-off step). Rebuilding the
page keeps visual positions and that drill-through setting.

Run with Power BI Desktop closed (save first):
    python scripts/build_journal_detail_page.py [--reset-layout]
"""
import copy
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_balance_sheet_page import (  # noqa: E402
    PAGES, PAGE_SCHEMA, STYLE_PAGE, chart_frame, column, first_of, lit, load_page, load_visuals, measure, new_id,
)

PAGE_NAME = "Journal detail"


def build_visuals(style):
    card_tpl = next(v for v in style if v["visual"]["visualType"] == "cardVisual")
    line_tpl = first_of(style, "lineChart")
    header_tpl = next(v for v in style if v["visual"]["visualType"] == "textbox"
                      and "Performance summary" in json.dumps(v, ensure_ascii=False))

    specs = []

    header = copy.deepcopy(header_tpl["visual"])
    header["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = \
        "Journal detail – full double entry"
    specs.append(("header", (0, 0, 1920, 48), header, {}))

    def card(prop, label):
        v = copy.deepcopy(card_tpl["visual"])
        v["query"] = {"queryState": {"Data": {"projections": [measure(prop, label)]}}}
        return v

    specs.append(("card|Selected Journal", (0, 56, 1040, 160), card("Selected Journal", "Journal"), {}))
    for i, (prop, label) in enumerate([("Total Debits (L)", "Debits ₹ L"), ("Total Credits (L)", "Credits ₹ L"),
                                       ("Debits less Credits", "Difference (must be 0)")]):
        specs.append((f"card|{prop}", (1048 + i * 290, 56, 282, 160), card(prop, label), {}))

    table_objects = {
        "values": [{"properties": {"fontSize": lit("15D")}}],
        "columnHeaders": [{"properties": {"fontSize": lit("15D"), "bold": lit("true")}}],
    }

    about = {
        "visualType": "tableEx",
        "query": {"queryState": {"Values": {"projections": [
            column("Journal", "source", "Source"),
            column("Journal", "created_at", "Entered"),
            # Names come from measures: a User column here would ignore the drill-through
            # filter and list every user.
            measure("Prepared By Name", "Prepared by"),
            measure("Approved By Name", "Approved by"),
            column("Journal", "journal_amount", "Amount ₹"),
            measure("Flag Status", "Why it was flagged"),
        ]}}},
        "objects": {**copy.deepcopy(table_objects), "total": [{"properties": {"totals": lit("false")}}]},
        "visualContainerObjects": chart_frame(line_tpl, "Who posted it and why it was flagged"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("about", (0, 224, 1920, 216), about, {}))

    lines = {
        "visualType": "tableEx",
        "query": {
            "queryState": {"Values": {"projections": [
                column("GL", "line_no", "Line"),
                column("Account", "account_id", "Account"),
                column("Account", "account_name", "Account name"),
                column("CostCentre", "cost_centre_name", "Cost centre"),
                measure("Total Debits", "Debit ₹"),
                measure("Total Credits", "Credit ₹"),
            ]}},
            "sortDefinition": {"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": "GL"}},
                                                              "Property": "line_no"}},
                                         "direction": "Ascending"}], "isDefaultSort": False},
        },
        "objects": {**copy.deepcopy(table_objects), "total": [{"properties": {"totals": lit("true")}}]},
        "visualContainerObjects": chart_frame(line_tpl, "Accounts debited and credited"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("lines", (0, 448, 1920, 632), lines, {}))
    return specs


def visual_key(doc):
    v = doc["visual"]
    vt = v["visualType"]
    if vt == "cardVisual":
        return "card|" + v["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]["Property"]
    if vt == "tableEx" and "query" in v:
        first = v["query"]["queryState"]["Values"]["projections"][0]["queryRef"]
        return "lines" if first == "GL.line_no" else "about"
    return {"textbox": "header"}.get(vt, f"{vt}|{doc['name']}")


def main():
    style_dir = load_page(STYLE_PAGE)
    if not style_dir:
        sys.exit(f"Page '{STYLE_PAGE}' not found under {PAGES}")
    style = load_visuals(style_dir)
    schema = style[0]["$schema"]
    specs = build_visuals(style)

    pages_json = PAGES / "pages.json"
    meta = json.loads(pages_json.read_text(encoding="utf-8"))

    kept, old_page, extras = {}, {}, []
    spec_keys = {key for key, *_ in specs}
    old = load_page(PAGE_NAME)
    if old:
        old_page = json.loads((old / "page.json").read_text(encoding="utf-8"))
        if (old / "visuals").exists():
            old_visuals = load_visuals(old)
            # Visuals added by hand (such as the drill-through Back button) are carried over as they are.
            extras = [doc for doc in old_visuals if visual_key(doc) not in spec_keys]
            if "--reset-layout" not in sys.argv:
                kept = {visual_key(doc): doc["position"] for doc in old_visuals}
        print(f"Replacing page folder {old.name}")
        shutil.rmtree(old)
    meta["pageOrder"] = [p for p in meta["pageOrder"] if (PAGES / p).is_dir()]

    page_id = new_id()
    page_dir = PAGES / page_id
    (page_dir / "visuals").mkdir(parents=True)
    for z, (key, (x, y, w, h), visual, extra) in enumerate(specs):
        position = kept.get(key) or {"x": x, "y": y, "z": z * 100, "height": h, "width": w, "tabOrder": z * 100}
        vid = new_id()
        doc = {"$schema": schema, "name": vid, "position": position, "visual": visual}
        doc.update({k: val for k, val in extra.items() if val})
        (page_dir / "visuals" / vid).mkdir()
        (page_dir / "visuals" / vid / "visual.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {key:<40} {'kept position' if key in kept else 'default position'}")
    for doc in extras:
        (page_dir / "visuals" / doc["name"]).mkdir()
        (page_dir / "visuals" / doc["name"] / "visual.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {visual_key(doc):<40} carried over (added by hand)")

    page = {"$schema": PAGE_SCHEMA, "name": page_id, "displayName": PAGE_NAME,
            "displayOption": "FitToPage", "height": 1080, "width": 1920}
    # Keep a drill-through set up by hand in Power BI Desktop on an earlier copy.
    for k in ("pageBinding", "filterConfig", "visibility"):
        if k in old_page:
            page[k] = old_page[k]
    (page_dir / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False), encoding="utf-8")

    meta["pageOrder"].append(page_id)
    meta["activePageName"] = page_id
    pages_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created page '{PAGE_NAME}' ({page_id}) with {len(specs)} visuals.")


if __name__ == "__main__":
    main()
