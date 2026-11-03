"""Build the data file for the interactive web version of the dashboard (docs/index.html).

Reads only the CSV files in data/, recalculates every figure the web pages show for both
fiscal years, checks the key figures against the Power BI report, and writes docs/data.js.

Run:  python scripts/build_web.py
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "docs" / "data.js"
LIMIT = 500_000

H = pd.read_csv(DATA / "journal_header.csv", parse_dates=["posting_date", "created_at"], keep_default_na=False)
L = pd.read_csv(DATA / "journal_lines.csv")
A = pd.read_csv(DATA / "dim_account.csv")
B = pd.read_csv(DATA / "budget.csv", parse_dates=["month_start"])
AR = pd.read_csv(DATA / "ar_invoices.csv", parse_dates=["invoice_date", "due_date", "paid_date"])
C = pd.read_csv(DATA / "dim_customer.csv")
U = pd.read_csv(DATA / "dim_user.csv").set_index("user_id").user_name
CC = pd.read_csv(DATA / "dim_cost_centre.csv").set_index("cost_centre_id").cost_centre_name

FYS = ["FY2024-25", "FY2025-26"]
START = {"FY2024-25": pd.Timestamp("2024-04-01"), "FY2025-26": pd.Timestamp("2025-04-01")}
END = {"FY2024-25": pd.Timestamp("2025-03-31"), "FY2025-26": pd.Timestamp("2026-03-31")}
MONTHS = pd.period_range("2024-04", "2026-03", freq="M")


def fy(d):
    return "FY2024-25" if d < pd.Timestamp("2025-04-01") else "FY2025-26"


def cr(x):
    return float(x) / 1e7  # full precision, so the page rounds exactly as Power BI does


def lk(x):
    return float(x) / 1e5


G = L.merge(H, on="journal_id").merge(A, on="account_id")
G["fy"] = G.posting_date.map(fy)
G["month"] = G.posting_date.dt.to_period("M")
B = B.merge(A, on="account_id")
B["fy"] = B.month_start.map(fy)
B["month"] = B.month_start.dt.to_period("M")
COSTS = ["COGS", "Operating Expenses", "Depreciation", "Finance Costs", "Tax"]
CLASSES = ["Revenue"] + COSTS


def pnl(g, col="amount", actual=True):
    by = g[g.statement == "Profit & Loss"].groupby("account_class")[col].sum().reindex(CLASSES, fill_value=0)
    if actual:
        by["Revenue"] = -by["Revenue"]
    gp = by["Revenue"] - by["COGS"]
    ebitda = gp - by["Operating Expenses"]
    pat = ebitda - by["Depreciation"] - by["Finance Costs"] - by["Tax"]
    return {"revenue": by["Revenue"], "cogs": by["COGS"], "gp": gp, "ebitda": ebitda, "pat": pat}


out = {"years": FYS, "months": [m.strftime("%b %Y") for m in MONTHS], "fy": {}}

# ---------------------------------------------------------------- monthly series
monthly = []
for m in MONTHS:
    a = pnl(G[G.month == m])
    b = pnl(B[B.month == m], "budget_amount", False)
    monthly.append({
        "label": m.strftime("%b %Y"), "fy": fy(m.to_timestamp()),
        "rev": cr(a["revenue"]), "bud_rev": cr(b["revenue"]),
        "ebitda_margin": round(a["ebitda"] / a["revenue"], 4),
        "gm": round(a["gp"] / a["revenue"], 4),
    })
out["monthly"] = monthly

# ---------------------------------------------------------------- per fiscal year
CF_LINES = [
    ("Operating", "Profit after tax", lambda g: g.statement == "Profit & Loss"),
    ("Operating", "Depreciation added back", lambda g: g.account_id == 1510),
    ("Operating", "Trade receivables", lambda g: g.account_id == 1100),
    ("Operating", "Inventory", lambda g: g.account_id == 1200),
    ("Operating", "Trade payables", lambda g: g.account_id == 2000),
    ("Operating", "Other working capital", lambda g: g.account_id.isin([1150, 1300, 1400, 2100, 2200, 2300])),
    ("Investing", "Capital expenditure", lambda g: g.account_id == 1500),
    ("Financing", "Borrowings", lambda g: g.account_id.isin([2400, 2500])),
]
MOVES = G[G.source != "Opening"]


def balance(account_ids, at):
    return G[G.account_id.isin(account_ids) & (G.posting_date <= at)].amount.sum()


def open_invoices(at):
    o = AR[(AR.invoice_date <= at) & (AR.paid_date.isna() | (AR.paid_date > at))].copy()
    o["dpd"] = (at - o.due_date).dt.days
    return o


def days_ratio(numerator, flow_mask_frame, at, col="amount"):
    start = (at - pd.DateOffset(months=3)) + pd.Timedelta(days=1)
    flow = flow_mask_frame[(flow_mask_frame.date >= start) & (flow_mask_frame.date <= at)][col].sum()
    return numerator / flow * ((at - start).days + 1) if flow else None


INVOICED = AR.rename(columns={"invoice_date": "date"})
COGS_LINES = G[G.account_class == "COGS"].rename(columns={"posting_date": "date"})

# Journal tests (same rules as validate.py and the Power Query).
M = H[H.source == "Manual"].copy()
rev_j = set(G[G.account_class == "Revenue"].journal_id)
ar_j = set(G[G.account_id == 1100].journal_id)
TESTS = {
    "T1": ("Posted on a weekend", M.created_at.dt.weekday >= 5),
    "T2": ("Posted late at night", (M.created_at.dt.hour >= 21) | (M.created_at.dt.hour < 6)),
    "T3": ("Suspiciously round amount", (M.journal_amount >= 100_000) & (M.journal_amount % 100_000 == 0)),
    "T4": ("Just under the ₹5 L approval limit", (M.journal_amount >= 450_000) & (M.journal_amount < LIMIT)),
    "T5": ("Approved by the same person", M.prepared_by == M.approved_by),
    "T6": ("Vague or missing description", M.description.str.strip().str.len() < 6),
    "T7": ("Backdated by over 10 days", (M.created_at.dt.normalize() - M.posting_date).dt.days > 10),
    "T8": ("Over ₹5 L, no controller sign-off", (M.journal_amount >= LIMIT) & (M.approved_by != "U08")),
    "T9": ("Manual entry to sales", M.journal_id.isin(rev_j)),
    "T10": ("Manual entry to customer balances", M.journal_id.isin(ar_j)),
}
flag_rows = [(jid, code) for code, (_, mask) in TESTS.items() for jid in M.loc[mask, "journal_id"]]
P = H[H.source == "Payment"][["journal_id", "party_id", "journal_amount", "posting_date"]]
pair = P.merge(P, on=["party_id", "journal_amount"], suffixes=("", "_o"))
pair = pair[(pair.journal_id != pair.journal_id_o) & ((pair.posting_date - pair.posting_date_o).dt.days.abs() <= 7)]
flag_rows += [(jid, "T11") for jid in sorted(set(pair.journal_id))]
FLAGS = pd.DataFrame(flag_rows, columns=["journal_id", "code"]).merge(H, on="journal_id")
FLAGS["fy"] = FLAGS.posting_date.map(fy)
LABELS = {code: label for code, (label, _) in TESTS.items()} | {"T11": "Possible double payment to supplier"}
out["test_labels"] = LABELS

for y in FYS:
    g, b, end = G[G.fy == y], B[B.fy == y], END[y]
    a, bu = pnl(g), pnl(b, "budget_amount", False)
    d = {}
    d["kpi"] = {
        "revenue": cr(a["revenue"]), "budget_revenue": cr(bu["revenue"]),
        "gm": round(a["gp"] / a["revenue"], 4), "gp": cr(a["gp"]),
        "ebitda": cr(a["ebitda"]), "budget_ebitda": cr(bu["ebitda"]),
        "ebitda_margin": round(a["ebitda"] / a["revenue"], 4),
        "pat": cr(a["pat"]), "pat_margin": round(a["pat"] / a["revenue"], 4),
    }
    # Revenue by sales region (revenue lines carry the region's cost centre).
    regions = []
    for cc in ["CC10", "CC20", "CC30"]:
        regions.append({"name": CC[cc], "actual": cr(-g[(g.account_class == "Revenue") & (g.cost_centre_id == cc)].amount.sum()),
                        "budget": cr(b[(b.account_class == "Revenue") & (b.cost_centre_id == cc)].budget_amount.sum())})
    d["regions"] = regions
    d["mix"] = [{"name": k, "value": cr(-v)} for k, v in
                g[g.account_class == "Revenue"].groupby("product_line").amount.sum().sort_values().items()]
    gm_pl = []
    for rev, cogs, name in [(4020, 5020, "Service & AMC"), (4000, 5000, "Fasteners"), (4010, 5010, "Bearings")]:
        r, c = -g[g.account_id == rev].amount.sum(), g[g.account_id == cogs].amount.sum()
        gm_pl.append({"name": name, "gm": round((r - c) / r, 4)})
    d["gm_by_product"] = gm_pl

    # Budget variance by account (INR lakh, favourable +).
    accounts = []
    act_acc = g[g.statement == "Profit & Loss"].groupby("account_id").amount.sum()
    bud_acc = b.groupby("account_id").budget_amount.sum()
    for _, acc in A[A.statement == "Profit & Loss"].iterrows():
        actual = act_acc.get(acc.account_id, 0.0) * (-1 if acc.account_class == "Revenue" else 1)
        budget = bud_acc.get(acc.account_id, 0.0)
        var = actual - budget if acc.account_class == "Revenue" else budget - actual
        accounts.append({"cls": acc.account_class, "name": acc.account_name,
                         "actual": lk(actual), "budget": lk(budget), "var": lk(var)})
    d["variance"] = accounts

    # Balance sheet at the year end and a year earlier.
    bs = []
    for _, acc in A[A.statement == "Balance Sheet"].iterrows():
        sign = 1 if acc.account_class == "Assets" else -1
        prev = end - pd.DateOffset(years=1)
        bs.append({"cls": acc.account_class, "name": acc.account_name,
                   "ye": cr(sign * balance([acc.account_id], end)),
                   "py": cr(sign * balance([acc.account_id], prev)) if prev >= pd.Timestamp("2024-04-01") else None})
    d["balance_sheet"] = bs
    assets = balance(A[A.account_class == "Assets"].account_id, end)
    liab = -balance(A[A.account_class == "Liabilities"].account_id, end)
    equity = -balance(A[A.account_class == "Equity"].account_id, end)
    cum_profit = -balance(A[A.statement == "Profit & Loss"].account_id, end)
    ar_bal, inv_bal, ap_bal = balance([1100], end), balance([1200], end), -balance([2000], end)
    d["bs_cards"] = {
        "bank": cr(balance([1000], end)), "nwc": cr(ar_bal + inv_bal - ap_bal),
        "borrowings": cr(-balance([2400, 2500], end)),
        "dso": round(days_ratio(ar_bal, INVOICED, end, "gross_amount")),
        "dio": round(days_ratio(inv_bal, COGS_LINES, end)),
        "check": round(assets - liab - equity - cum_profit),
    }
    o = open_invoices(end)
    bins, names = [-10**6, 0, 30, 60, 90, 180, 10**6], ["Not due", "1-30", "31-60", "61-90", "91-180", "Over 180"]
    o["bucket"] = pd.cut(o.dpd, bins=bins, labels=names)
    d["ageing"] = [{"name": n, "value": cr(v)} for n, v in o.groupby("bucket", observed=False).gross_amount.sum().items()]
    over = o[o.dpd > 90].merge(C, on="customer_id").groupby("customer_name").gross_amount.sum().sort_values(ascending=False)
    d["overdue"] = [{"name": k, "value": lk(v)} for k, v in over.items()]
    d["ar_rec_diff"] = lk(ar_bal - o.gross_amount.sum())
    d["as_at"] = end.strftime("%d %b %Y").lstrip("0")

    # Cash flow (indirect): movement in every non-cash account, sign reversed.
    mv = MOVES[MOVES.fy == y]
    d["cash_flow"] = [{"section": s, "line": n, "value": cr(-mv[f(mv)].amount.sum())} for s, n, f in CF_LINES]
    net = sum(x["value"] for x in d["cash_flow"])
    bank_move = cr(mv[mv.account_id == 1000].amount.sum())
    assert abs(net - bank_move) < 0.0001, "cash flow does not tie to the bank account"
    d["cash_cards"] = {"opening": round(d["bs_cards"]["bank"] - net, 4), "closing": d["bs_cards"]["bank"],
                       "net": round(net, 4), "borrowings": d["bs_cards"]["borrowings"]}

    # Journal testing for journals posted in the year.
    mj = M[M.posting_date.map(fy) == y]
    fl = FLAGS[FLAGS.fy == y]
    by_j = fl.groupby("journal_id")
    flagged = by_j.first()
    flagged["codes"] = by_j.code.apply(lambda s: sorted(s, key=lambda c: int(c[1:])))
    d["jt_cards"] = {
        "manual": int(len(mj)), "flagged": int(len(flagged)),
        "flagged_manual_pct": round(flagged[flagged.source == "Manual"].shape[0] / len(mj), 4),
        "flagged_value": lk(flagged.journal_amount.sum()),
        "duplicate_exposure": lk(fl[fl.code == "T11"].journal_amount.sum() / 2),
    }
    d["tests"] = [{"code": c, "count": int((fl.code == c).sum())} for c in LABELS if (fl.code == c).any()]
    d["journals"] = [{
        "id": jid, "posted": r.posting_date.strftime("%d %b %Y"), "desc": r.description,
        "amount": round(float(r.journal_amount), 2), "prepared": r.prepared_by, "approved": r.approved_by,
        "prepared_name": U.get(r.prepared_by, ""), "approved_name": U.get(r.approved_by, ""), "codes": r.codes,
    } for jid, r in flagged.sort_values("journal_amount", ascending=False).iterrows()]
    out["fy"][y] = d

# Monthly cash series, DSO and DIO at each month end.
cash_m = []
for m in MONTHS:
    me = m.to_timestamp(how="end").normalize()
    mv = MOVES[MOVES.month == m]
    op = sum(-mv[f(mv)].amount.sum() for s, _, f in CF_LINES if s == "Operating")
    dso = days_ratio(balance([1100], me), INVOICED, me, "gross_amount") if m >= pd.Period("2024-06", "M") else None
    dio = days_ratio(balance([1200], me), COGS_LINES, me) if m >= pd.Period("2024-06", "M") else None
    cash_m.append({"label": m.strftime("%b %Y"), "fy": fy(me), "cfo": cr(op), "bank": cr(balance([1000], me)),
                   "dso": round(dso) if dso else None, "dio": round(dio) if dio else None})
out["cash_monthly"] = cash_m

# Full double entry for every flagged journal (for the drill-through page).
detail = {}
for jid in sorted(set(FLAGS.journal_id)):
    h = H[H.journal_id == jid].iloc[0]
    lines = G[G.journal_id == jid].sort_values("line_no")
    detail[jid] = {
        "source": h.source, "entered": h.created_at.strftime("%d %b %Y %H:%M"),
        "posted": h.posting_date.strftime("%d %b %Y"), "desc": h.description,
        "prepared": U.get(h.prepared_by, ""), "approved": U.get(h.approved_by, "No approver recorded"),
        "amount": round(float(h.journal_amount), 2),
        "codes": sorted(FLAGS[FLAGS.journal_id == jid].code.unique(), key=lambda c: int(c[1:])),
        "lines": [{"no": int(r.line_no), "acc": int(r.account_id), "name": r.account_name,
                   "cc": CC.get(r.cost_centre_id, ""), "dr": round(float(r.debit), 2), "cr": round(float(r.credit), 2)}
                  for _, r in lines.iterrows()],
    }
out["detail"] = detail

# ----------------------------------------------------- checks against Power BI
f26, f25 = out["fy"]["FY2025-26"], out["fy"]["FY2024-25"]
CHECKS = [
    (f26["kpi"]["revenue"], 96.41, 2), (f25["kpi"]["revenue"], 85.27, 2), (f26["kpi"]["ebitda"], 7.15, 2),
    (f26["kpi"]["pat"], 2.60, 2), (f26["bs_cards"]["bank"], 5.12, 2), (f26["bs_cards"]["nwc"], 28.03, 2),
    (f26["bs_cards"]["borrowings"], 15.00, 2), (f26["bs_cards"]["dso"], 68, 0), (f26["bs_cards"]["dio"], 88, 0),
    (f26["bs_cards"]["check"], 0, 0), (f26["ageing"][0]["value"], 14.91, 2), (f26["ar_rec_diff"], -3.18, 2),
    (sum(x["value"] for x in f26["cash_flow"] if x["section"] == "Operating"), -2.61, 2),
    (f26["cash_cards"]["opening"], 7.33, 2), (f26["jt_cards"]["manual"], 311, 0), (f26["jt_cards"]["flagged"], 49, 0),
    (f26["jt_cards"]["flagged_value"], 319.5, 1), (f26["jt_cards"]["duplicate_exposure"], 25.9, 1),
    (sum(x["var"] for x in f26["variance"]), -223.1, 1),
]
for got, want, nd in CHECKS:
    assert round(got, nd) == round(want, nd), f"web figure {got} does not match the report ({want})"

OUT.write_text("// Generated by scripts/build_web.py from the CSV files in data/. Do not edit.\n"
               "window.DATA = " + json.dumps(out, ensure_ascii=False, separators=(",", ":")) + ";\n", encoding="utf-8")
print(f"{OUT.relative_to(ROOT)} written ({OUT.stat().st_size / 1024:.0f} KB); {len(CHECKS)} figures match the Power BI report.")
