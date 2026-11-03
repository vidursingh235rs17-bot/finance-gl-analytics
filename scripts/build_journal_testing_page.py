"""Generate the 'Journal testing' report page (PBIR format) for GL_Analytics.pbip.

Uses the formatting helpers of build_balance_sheet_page.py so every page matches
the 'Performance' page. Positions of visuals on an existing copy of this page
are kept, so a layout adjusted by hand survives a rebuild.

Run with Power BI Desktop closed (save first):
    python scripts/build_journal_testing_page.py [--reset-layout]
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

PAGE_NAME = "Journal testing"


def build_visuals(style):
    slicer_tpl = first_of(style, "slicer")
    card_tpl = next(v for v in style if v["visual"]["visualType"] == "cardVisual")
    line_tpl = first_of(style, "lineChart")
    header_tpl = next(v for v in style if v["visual"]["visualType"] == "textbox"
                      and "Performance summary" in json.dumps(v, ensure_ascii=False))

    specs = []

    header = copy.deepcopy(header_tpl["visual"])
    header["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = \
        "Journal entry testing – Northfield Industrial Supplies"
    specs.append(("header", (0, 0, 1920, 48), header, {}))

    # Same slicer as Performance: synced year across pages, (Blank) hidden.
    slicer = copy.deepcopy(slicer_tpl["visual"])
    specs.append(("slicer", (0, 48, 264, 168), slicer, {"filterConfig": slicer_tpl.get("filterConfig")}))

    cards = [
        ("Manual Journals", "Manual journals"),
        ("Flagged Journals", "Flagged journals"),
        ("Flagged % of Manual Journals", "% of manual flagged"),
        ("Flagged Value (L)", "Flagged value ₹ L"),
        ("Duplicate Payment Exposure (L)", "Duplicate payments ₹ L"),
    ]
    card_w = (1920 - 272) // len(cards)
    for i, (prop, label) in enumerate(cards):
        v = copy.deepcopy(card_tpl["visual"])
        v["query"] = {"queryState": {"Data": {"projections": [measure(prop, label)]}}}
        specs.append((f"card|{prop}", (272 + i * card_w, 48, card_w - 8, 168), v, {}))

    def sort_by_column(entity, prop, direction="Ascending"):
        return {"sort": [{"field": {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}},
                          "direction": direction}], "isDefaultSort": False}

    def sort_by_measure(prop, direction="Descending"):
        return {"sort": [{"field": {"Measure": {"Expression": {"SourceRef": {"Entity": "Measures (2)"}},
                                                "Property": prop}}, "direction": direction}],
                "isDefaultSort": False}

    # Clean bars: names on the left, the count printed at the end of each bar,
    # no value axis or gridlines to read.
    bar_objects = {
        "dataPoint": [{"properties": {"fill": {"solid": {"color": lit("'#C62828'")}}}}],
        "labels": [{"properties": {"show": lit("true"), "fontSize": lit("14D"), "labelPosition": lit("'OutsideEnd'")}}],
        "categoryAxis": [{"properties": {"fontSize": lit("14D"), "showAxisTitle": lit("false")}}],
        "valueAxis": [{"properties": {"show": lit("false"), "gridlineShow": lit("false"), "showAxisTitle": lit("false")}}],
        "legend": [{"properties": {"show": lit("false")}}],
    }

    tests = {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": {
                "Category": {"projections": [column("JournalFlags", "check_label", "Check", True)]},
                "Y": {"projections": [measure("Flagged Journals", "Journals flagged")]},
                "Tooltips": {"projections": [measure("Flagged Value (L)", "Value ₹ L")]},
            },
            "sortDefinition": sort_by_measure("Flagged Journals"),
        },
        "objects": copy.deepcopy(bar_objects),
        "visualContainerObjects": chart_frame(line_tpl, "How many journals failed each check (click a bar to see them)"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("tests", (0, 224, 760, 496), tests, {}))

    users_objects = copy.deepcopy(bar_objects)
    users_objects["dataPoint"] = [{"properties": {"fill": {"solid": {"color": lit("'#1F4E79'")}}}}]
    users = {
        "visualType": "clusteredBarChart",
        "query": {
            "queryState": {
                "Category": {"projections": [column("User", "user_name", "Prepared by", True)]},
                "Y": {"projections": [measure("Flagged Journals", "Journals flagged")]},
            },
            "sortDefinition": sort_by_measure("Flagged Journals"),
        },
        "objects": users_objects,
        "visualContainerObjects": chart_frame(line_tpl, "Who prepared the flagged journals"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("users", (0, 728, 760, 352), users, {}))


    detail = {
        "visualType": "tableEx",
        "query": {
            "queryState": {"Values": {"projections": [
                column("Journal", "journal_id", "Journal"),
                column("Journal", "posting_date", "Posted"),
                column("Journal", "description", "Description"),
                column("Journal", "journal_amount", "Amount ₹"),
                column("Journal", "prepared_by", "Prepared"),
                column("Journal", "approved_by", "Approved"),
                # Blank for journals with no flag, so only flagged journals are listed.
                measure("Tests Failed", "Why it was flagged"),
            ]}},
            "sortDefinition": sort_by_column("Journal", "journal_amount", "Descending"),
        },
        "objects": {
            "values": [{"properties": {"fontSize": lit("14D")}}],
            "columnHeaders": [{"properties": {"fontSize": lit("14D"), "bold": lit("true")}}],
            "total": [{"properties": {"totals": lit("false")}}],
        },
        "visualContainerObjects": chart_frame(line_tpl, "Flagged journals to review (largest first)"),
        "drillFilterOtherVisuals": True,
    }
    specs.append(("detail", (768, 224, 1152, 856), detail, {}))
    return specs


def visual_key(doc):
    v = doc["visual"]
    vt = v["visualType"]
    if vt == "cardVisual":
        return "card|" + v["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]["Property"]
    if vt == "clusteredBarChart":
        entity = v["query"]["queryState"]["Category"]["projections"][0]["field"]["Column"]["Expression"]["SourceRef"]["Entity"]
        return "users" if entity == "User" else "tests"
    return {"textbox": "header", "slicer": "slicer", "tableEx": "detail"}.get(vt, vt)


def main():
    style_dir = load_page(STYLE_PAGE)
    if not style_dir:
        sys.exit(f"Page '{STYLE_PAGE}' not found under {PAGES}")
    style = load_visuals(style_dir)
    schema = style[0]["$schema"]
    specs = build_visuals(style)

    pages_json = PAGES / "pages.json"
    meta = json.loads(pages_json.read_text(encoding="utf-8"))

    kept = {}
    old = load_page(PAGE_NAME)
    if old:
        if (old / "visuals").exists() and "--reset-layout" not in sys.argv:
            kept = {visual_key(doc): doc["position"] for doc in load_visuals(old)}
        print(f"Replacing page folder {old.name}")
        shutil.rmtree(old)
    meta["pageOrder"] = [p for p in meta["pageOrder"] if (PAGES / p).is_dir()]

    page_id = new_id()
    page_dir = PAGES / page_id
    (page_dir / "visuals").mkdir(parents=True)
    ids = {}
    for z, (key, (x, y, w, h), visual, extra) in enumerate(specs):
        position = kept.get(key) or {"x": x, "y": y, "z": z * 100, "height": h, "width": w, "tabOrder": z * 100}
        vid = ids[key] = new_id()
        doc = {"$schema": schema, "name": vid, "position": position, "visual": visual}
        doc.update({k: val for k, val in extra.items() if val})
        (page_dir / "visuals" / vid).mkdir()
        (page_dir / "visuals" / vid / "visual.json").write_text(
            json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  {key:<40} {'kept position' if key in kept else 'default position'}")

    # The cards summarise the year; clicking a bar or a table row must not change them.
    interactions = [{"source": ids[src], "target": ids[key], "type": "NoFilter"}
                    for src in ("tests", "users", "detail") for key in ids if key.startswith("card|")]
    page = {"$schema": PAGE_SCHEMA, "name": page_id, "displayName": PAGE_NAME,
            "displayOption": "FitToPage", "height": 1080, "width": 1920, "visualInteractions": interactions}
    (page_dir / "page.json").write_text(json.dumps(page, indent=2, ensure_ascii=False), encoding="utf-8")

    meta["pageOrder"].append(page_id)
    meta["activePageName"] = page_id
    pages_json.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Created page '{PAGE_NAME}' ({page_id}) with {len(specs)} visuals.")


if __name__ == "__main__":
    main()
