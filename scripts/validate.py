"""Independent check of the CSV files and control totals for the Power BI report.

Reads only the files in data/ (not the generator), re-performs every calculation
the report uses, and writes validation/expected_results.md. Use those figures to
confirm that the Power BI measures return the same numbers.

Run:  python scripts/validate.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
VAL = ROOT / "validation"
AS_AT = pd.Timestamp("2026-03-31")
LIMIT = 500_000

H = pd.read_csv(DATA / "journal_header.csv", parse_dates=["posting_date", "created_at"], keep_default_na=False)
L = pd.read_csv(DATA / "journal_lines.csv")
A = pd.read_csv(DATA / "dim_account.csv")
B = pd.read_csv(DATA / "budget.csv", parse_dates=["month_start"])
AR = pd.read_csv(DATA / "ar_invoices.csv", parse_dates=["invoice_date", "due_date", "paid_date"])
C = pd.read_csv(DATA / "dim_customer.csv")
KEY = pd.read_csv(VAL / "seeded_exceptions.csv")

out = []


def w(text=""):
    out.append(text)


def cr(x):
    return f"{x / 1e7:,.2f}"


def fy(d):
    return "FY2024-25" if d < pd.Timestamp("2025-04-01") else "FY2025-26"


# ---------------------------------------------------------------- integrity
bal = L.groupby("journal_id")["amount"].sum().round(2)
assert (bal == 0).all(), "unbalanced journals"
assert abs(L.amount.sum()) < 0.01, "trial balance does not net to zero"
assert set(L.journal_id) == set(H.journal_id)
assert H.journal_id.is_unique and AR.invoice_no.is_unique

G = L.merge(H, on="journal_id").merge(A, on="account_id")
G["fy"] = G.posting_date.map(fy)
B = B.merge(A, on="account_id")
B["fy"] = B.month_start.map(fy)

w("# Expected results (control totals)")
w()
w("Produced by `scripts/validate.py` from the CSV files. Amounts are in INR crore unless stated.")
w("If a Power BI measure disagrees with a figure here, the measure or a relationship is wrong.")
w()
w("## 1. Integrity")
w()
w(f"- Journals: {len(H):,}; journal lines: {len(L):,}; every journal balances to zero.")
w(f"- Trial balance nets to {L.amount.sum():.2f}.")
w(f"- Journals by source: " + ", ".join(f"{k} {v:,}" for k, v in H.source.value_counts().items()) + ".")

# ---------------------------------------------------------------------- P&L
ORDER = ["Revenue", "COGS", "Operating Expenses", "Depreciation", "Finance Costs", "Tax"]


def pnl(frame, col, sign_actual):
    s = frame[frame.statement == "Profit & Loss"].groupby(["fy", "account_class"])[col].sum().unstack(0)
    s = s.reindex(ORDER)
    if sign_actual:
        s.loc["Revenue"] = -s.loc["Revenue"]
    rows = {"Revenue": s.loc["Revenue"], "COGS": s.loc["COGS"]}
    rows["Gross Profit"] = rows["Revenue"] - rows["COGS"]
    rows["Operating Expenses"] = s.loc["Operating Expenses"]
    rows["EBITDA"] = rows["Gross Profit"] - rows["Operating Expenses"]
    rows["Depreciation"] = s.loc["Depreciation"]
    rows["EBIT"] = rows["EBITDA"] - rows["Depreciation"]
    rows["Finance Costs"] = s.loc["Finance Costs"]
    rows["Profit Before Tax"] = rows["EBIT"] - rows["Finance Costs"]
    rows["Tax"] = s.loc["Tax"]
    rows["Profit After Tax"] = rows["Profit Before Tax"] - rows["Tax"]
    return pd.DataFrame(rows).T


act, bud = pnl(G, "amount", True), pnl(B, "budget_amount", False)
w()
w("## 2. Profit & loss: actual vs budget")
w()
w("| Line | FY25 Actual | FY25 Budget | FY26 Actual | FY26 Budget | FY26 Var | FY26 vs FY25 |")
w("|---|---:|---:|---:|---:|---:|---:|")
COSTS = {"COGS", "Operating Expenses", "Depreciation", "Finance Costs", "Tax"}
for line in act.index:
    a25, b25, a26, b26 = act.loc[line, "FY2024-25"], bud.loc[line, "FY2024-25"], act.loc[line, "FY2025-26"], bud.loc[line, "FY2025-26"]
    var = (b26 - a26) if line in COSTS else (a26 - b26)
    w(f"| {line} | {cr(a25)} | {cr(b25)} | {cr(a26)} | {cr(b26)} | {cr(var)} | {(a26 / a25 - 1) * 100:+.1f}% |")
w()
w("Variance is shown as favourable (+) / adverse (-).")
w()
w("| Ratio | FY25 Actual | FY26 Actual | FY26 Budget |")
w("|---|---:|---:|---:|")
for name, num in [("Gross margin %", "Gross Profit"), ("EBITDA margin %", "EBITDA"), ("PAT margin %", "Profit After Tax")]:
    w(f"| {name} | {act.loc[num, 'FY2024-25'] / act.loc['Revenue', 'FY2024-25'] * 100:.1f}% | "
      f"{act.loc[num, 'FY2025-26'] / act.loc['Revenue', 'FY2025-26'] * 100:.1f}% | "
      f"{bud.loc[num, 'FY2025-26'] / bud.loc['Revenue', 'FY2025-26'] * 100:.1f}% |")

w()
w("### FY26 variance by account (INR lakh, favourable + / adverse -)")
w()
w("| Account | Actual | Budget | Variance | Var % |")
w("|---|---:|---:|---:|---:|")
a_acc = G[(G.fy == "FY2025-26") & (G.statement == "Profit & Loss")].groupby(["account_id", "account_name", "account_class"])["amount"].sum()
b_acc = B[B.fy == "FY2025-26"].groupby("account_id")["budget_amount"].sum()
for (aid, name, cls), amt in a_acc.items():
    actual = -amt if cls == "Revenue" else amt
    budget = b_acc.get(aid, 0.0)
    var = actual - budget if cls == "Revenue" else budget - actual
    w(f"| {aid} {name} | {actual / 1e5:,.1f} | {budget / 1e5:,.1f} | {var / 1e5:+,.1f} | {var / budget * 100:+.1f}% |")

w()
w("### Gross margin % by product line")
w()
w("| Product | FY25 | FY26 H1 | FY26 H2 |")
w("|---|---:|---:|---:|")
G["half"] = G.posting_date.map(lambda d: "FY25" if d < pd.Timestamp("2025-04-01") else ("FY26 H1" if d < pd.Timestamp("2025-10-01") else "FY26 H2"))
for rev, cogs, name in [(4000, 5000, "Fasteners"), (4010, 5010, "Bearings"), (4020, 5020, "Service & AMC")]:
    r = -G[G.account_id == rev].groupby("half")["amount"].sum()
    c = G[G.account_id == cogs].groupby("half")["amount"].sum()
    gm = (r - c) / r * 100
    w(f"| {name} | {gm['FY25']:.1f}% | {gm['FY26 H1']:.1f}% | {gm['FY26 H2']:.1f}% |")

w()
w("### Monthly revenue and EBITDA (INR lakh)")
w()
w("| Month | Revenue | Budget revenue | EBITDA |")
w("|---|---:|---:|---:|")
G["month"] = G.posting_date.dt.to_period("M")
B["month"] = B.month_start.dt.to_period("M")
for m in sorted(G.month.unique()):
    g = G[G.month == m]
    rev = -g[g.account_class == "Revenue"].amount.sum()
    ebitda = rev - g[g.account_class.isin(["COGS", "Operating Expenses"])].amount.sum()
    brev = B[(B.month == m) & (B.account_class == "Revenue")].budget_amount.sum()
    w(f"| {m.strftime('%b %Y')} | {rev / 1e5:,.1f} | {brev / 1e5:,.1f} | {ebitda / 1e5:,.1f} |")

# ------------------------------------------------------------ balance sheet
w()
w("## 3. Balance sheet")
w()
w("| Account | 31 Mar 2025 | 31 Mar 2026 |")
w("|---|---:|---:|")
bs = {}
for label, cut in [("31 Mar 2025", pd.Timestamp("2025-03-31")), ("31 Mar 2026", AS_AT)]:
    g = G[G.posting_date <= cut]
    bs[label] = g[g.statement == "Balance Sheet"].groupby(["account_id", "account_name"])["amount"].sum()
    bs[label + " pnl"] = -g[g.statement == "Profit & Loss"].amount.sum()
for (aid, name) in bs["31 Mar 2026"].index:
    v25 = bs["31 Mar 2025"].get((aid, name), 0.0)
    v26 = bs["31 Mar 2026"][(aid, name)]
    sign = 1 if aid < 2000 else -1
    w(f"| {aid} {name} | {cr(sign * v25)} | {cr(sign * v26)} |")
w(f"| Cumulative profit since 1 Apr 2024 (not yet closed to 3100) | {cr(bs['31 Mar 2025 pnl'])} | {cr(bs['31 Mar 2026 pnl'])} |")
w()
w("Assets are shown positive; liabilities and equity are shown positive (credit balances).")
bank = G[G.account_id == 1000].sort_values("posting_date").groupby("posting_date")["amount"].sum().cumsum()
w(f"Lowest bank balance in the period: INR {cr(bank.min())} crore on {bank.idxmin():%d %b %Y}.")

# ------------------------------------------------------------- receivables
w()
w("## 4. Receivables")
w()
open_inv = AR[AR.paid_date.isna()].copy()
gl_ar = G[(G.account_id == 1100)].amount.sum()
w(f"- Receivables per general ledger (account 1100) at 31 Mar 2026: INR {gl_ar:,.2f}")
w(f"- Open invoices per sub-ledger at 31 Mar 2026: INR {open_inv.gross_amount.sum():,.2f}")
w(f"- Unreconciled difference (GL less sub-ledger): INR {gl_ar - open_inv.gross_amount.sum():,.2f}")
w()
open_inv["days_overdue"] = (AS_AT - open_inv.due_date).dt.days
bins = [-10_000, 0, 30, 60, 90, 180, 10_000]
labels = ["Not due", "1-30", "31-60", "61-90", "91-180", "Over 180"]
open_inv["bucket"] = pd.cut(open_inv.days_overdue, bins=bins, labels=labels)
age = open_inv.groupby("bucket", observed=False)["gross_amount"].agg(["sum", "count"])
w("| Ageing bucket (days past due) | Amount (INR crore) | Invoices | Share |")
w("|---|---:|---:|---:|")
for b, row in age.iterrows():
    w(f"| {b} | {cr(row['sum'])} | {int(row['count'])} | {row['sum'] / age['sum'].sum() * 100:.1f}% |")
w()
w("| Top overdue customers (over 90 days) | Amount (INR lakh) | Invoices |")
w("|---|---:|---:|")
top = open_inv[open_inv.days_overdue > 90].merge(C, on="customer_id").groupby(["customer_id", "customer_name"])["gross_amount"].agg(["sum", "count"])
for (cid, name), row in top.sort_values("sum", ascending=False).head(5).iterrows():
    w(f"| {cid} {name} | {row['sum'] / 1e5:,.1f} | {int(row['count'])} |")
w()
w("| Quarter end | Receivables (INR crore) | Gross invoiced in quarter (INR crore) | DSO (days) |")
w("|---|---:|---:|---:|")
for q_end in pd.date_range("2024-06-30", "2026-03-31", freq="QE"):
    q_start = (q_end - pd.offsets.QuarterBegin(startingMonth=1)).normalize()
    arbal = G[(G.account_id == 1100) & (G.posting_date <= q_end)].amount.sum()
    invoiced = AR[(AR.invoice_date >= q_start) & (AR.invoice_date <= q_end)].gross_amount.sum()
    days = (q_end - q_start).days + 1
    w(f"| {q_end:%d %b %Y} | {cr(arbal)} | {cr(invoiced)} | {arbal / invoiced * days:.0f} |")

# --------------------------------------------------------- journal testing
M = H[H.source == "Manual"].copy()
M["desc_len"] = M.description.str.strip().str.len()
rev_journals = set(G[(G.account_class == "Revenue")].journal_id)
ar_journals = set(G[(G.account_id == 1100)].journal_id)
tests = {
    "T1 Entered on a weekend": M.created_at.dt.weekday >= 5,
    "T2 Entered after hours (21:00-06:00)": (M.created_at.dt.hour >= 21) | (M.created_at.dt.hour < 6),
    "T3 Round amount (multiple of INR 1,00,000)": (M.journal_amount >= 100_000) & (M.journal_amount % 100_000 == 0),
    "T4 Just below approval limit (INR 4.5-5.0 lakh)": (M.journal_amount >= 450_000) & (M.journal_amount < LIMIT),
    "T5 Prepared and approved by same user": M.prepared_by == M.approved_by,
    "T6 Missing or weak description": M.desc_len < 6,
    "T7 Backdated more than 10 days": (M.created_at.dt.normalize() - M.posting_date).dt.days > 10,
    "T8 Above limit without controller approval": (M.journal_amount >= LIMIT) & (M.approved_by != "U08"),
    "T9 Manual journal to revenue": M.journal_id.isin(rev_journals),
    "T10 Manual journal to receivables control": M.journal_id.isin(ar_journals),
}
P = H[H.source == "Payment"][["journal_id", "party_id", "journal_amount", "posting_date"]]
pair = P.merge(P, on=["party_id", "journal_amount"], suffixes=("", "_other"))
pair = pair[(pair.journal_id != pair.journal_id_other) & ((pair.posting_date - pair.posting_date_other).dt.days.abs() <= 7)]
dup_ids = set(pair.journal_id)

flags = pd.DataFrame(tests)
M["flag_count"] = flags.sum(axis=1)
w()
w("## 5. Journal entry testing")
w()
w(f"Population: {len(M):,} manual journals with a total value of INR {cr(M.journal_amount.sum())} crore "
  f"({len(M) / len(H) * 100:.1f}% of all journals by count).")
w()
w("| Test | Journals flagged | Value (INR lakh) |")
w("|---|---:|---:|")
for name, mask in tests.items():
    w(f"| {name} | {int(mask.sum())} | {M.loc[mask, 'journal_amount'].sum() / 1e5:,.1f} |")
dup_val = H[H.journal_id.isin(dup_ids)].journal_amount.sum()
w(f"| T11 Possible duplicate vendor payment (same vendor and amount within 7 days) | {len(dup_ids)} "
  f"({len(dup_ids) // 2} pairs) | {dup_val / 1e5:,.1f} |")
w()
w(f"- Manual journals with at least one flag (T1-T10): {int((M.flag_count > 0).sum())}")
w(f"- Manual journals with two or more flags: {int((M.flag_count > 1).sum())}")
w(f"- All flagged journals including duplicate payments (T1-T11): {int((M.flag_count > 0).sum()) + len(dup_ids)}")
w(f"- Total flag hits (rows in the JournalFlags table): {int(flags.sum().sum()) + len(dup_ids)}")
w(f"- Amount at risk from duplicate payments (one payment of each pair): INR {dup_val / 2 / 1e5:,.1f} lakh")
w()
w("| Journals with the most flags | Posting date | Amount (INR) | Flags | Description |")
w("|---|---|---:|---:|---|")
for _, r in M.sort_values(["flag_count", "journal_amount"], ascending=False).head(8).iterrows():
    w(f"| {r.journal_id} | {r.posting_date:%d %b %Y} | {r.journal_amount:,.0f} | {r.flag_count} | {r.description or '(blank)'} |")

flagged = set(M[M.flag_count > 0].journal_id) | dup_ids
missed = set(KEY.journal_id) - flagged
w()
w("### Check against the seeded exceptions")
w()
w(f"- Seeded journals: {len(KEY)}; found by the tests: {len(set(KEY.journal_id) & flagged)}; missed: {len(missed)}.")
w(f"- Flagged journals that were not seeded (false positives to clear by enquiry): {len(flagged - set(KEY.journal_id))}.")

# ---------------------------------------------------------------- cash flow
# Indirect method: the movement in every non-cash account, sign reversed, excluding the
# opening balance journal. The lines must add up to the movement in the bank account.
w()
w("## 6. Cash flow (indirect method)")
w()
moves = G[G.source != "Opening"]
CF_LINES = [
    ("Operating", "Profit after tax", moves.statement == "Profit & Loss"),
    ("Operating", "Depreciation added back", moves.account_id == 1510),
    ("Operating", "Trade receivables", moves.account_id == 1100),
    ("Operating", "Inventory", moves.account_id == 1200),
    ("Operating", "Trade payables", moves.account_id == 2000),
    ("Operating", "Other working capital", moves.account_id.isin([1150, 1300, 1400, 2100, 2200, 2300])),
    ("Investing", "Capital expenditure", moves.account_id == 1500),
    ("Financing", "Borrowings", moves.account_id.isin([2400, 2500])),
    ("Financing", "Equity", moves.account_id.isin([3000, 3100])),
]
years = ["FY2024-25", "FY2025-26"]
cf = {line: [-moves[mask & (moves.fy == y)].amount.sum() for y in years] for _, line, mask in CF_LINES}
w("| Section | Line | FY25 | FY26 |")
w("|---|---|---:|---:|")
for section, line, _ in CF_LINES:
    w(f"| {section} | {line} | {cr(cf[line][0])} | {cr(cf[line][1])} |")
for section in ("Operating", "Investing", "Financing"):
    tot = [sum(cf[line][i] for s, line, _ in CF_LINES if s == section) for i in range(2)]
    w(f"| **{section}** | **Total** | **{cr(tot[0])}** | **{cr(tot[1])}** |")
net = [sum(v[i] for v in cf.values()) for i in range(2)]
bank = [moves[(moves.account_id == 1000) & (moves.fy == y)].amount.sum() for y in years]
assert all(abs(n - b) < 1 for n, b in zip(net, bank)), "cash flow does not reconcile to the bank account"
closing = [G[(G.account_id == 1000) & (G.posting_date <= pd.Timestamp(d))].amount.sum()
           for d in ("2025-03-31", "2026-03-31")]
w()
w(f"- Net cash flow: FY25 {cr(net[0])}, FY26 {cr(net[1])}; equals the movement in account 1000.")
w(f"- Opening cash: FY25 {cr(closing[0] - net[0])}, FY26 {cr(closing[1] - net[1])}. "
  f"Closing cash: FY25 {cr(closing[0])}, FY26 {cr(closing[1])}.")

(VAL / "expected_results.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
