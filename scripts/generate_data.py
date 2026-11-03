"""Generate a synthetic double-entry general ledger for a fictional company.

Company : Northfield Industrial Supplies Pvt Ltd (fictional distributor)
Period  : 1 Apr 2024 - 31 Mar 2026 (FY2024-25 and FY2025-26, Indian fiscal year)
Currency: INR

Every journal balances. A small number of control exceptions are seeded on
purpose; they are listed in validation/seeded_exceptions.csv.

Run:  python scripts/generate_data.py
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 20260331
rng = np.random.default_rng(SEED)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
VAL = ROOT / "validation"
DATA.mkdir(exist_ok=True)
VAL.mkdir(exist_ok=True)

START = pd.Timestamp("2024-04-01")
END = pd.Timestamp("2026-03-31")
MONTHS = pd.period_range("2024-04", "2026-03", freq="M")
GST = 0.18
LAKH = 1e5
APPROVAL_LIMIT = 500_000  # manual journals at or above this need the Financial Controller

# ---------------------------------------------------------------- dimensions
ACCOUNTS = [
    # id, name, class, subclass, statement
    (1000, "Bank - Current Account", "Assets", "Cash & Bank", "Balance Sheet"),
    (1100, "Trade Receivables", "Assets", "Trade Receivables", "Balance Sheet"),
    (1150, "Unbilled Revenue", "Assets", "Other Current Assets", "Balance Sheet"),
    (1200, "Inventory", "Assets", "Inventory", "Balance Sheet"),
    (1300, "GST Input Credit", "Assets", "Other Current Assets", "Balance Sheet"),
    (1400, "Prepaid Expenses", "Assets", "Other Current Assets", "Balance Sheet"),
    (1500, "Property, Plant & Equipment", "Assets", "Fixed Assets", "Balance Sheet"),
    (1510, "Accumulated Depreciation", "Assets", "Fixed Assets", "Balance Sheet"),
    (2000, "Trade Payables", "Liabilities", "Trade Payables", "Balance Sheet"),
    (2100, "GST Output Payable", "Liabilities", "Statutory Dues", "Balance Sheet"),
    (2200, "Accrued Expenses", "Liabilities", "Other Current Liabilities", "Balance Sheet"),
    (2300, "Provision for Income Tax", "Liabilities", "Provisions", "Balance Sheet"),
    (2400, "Working Capital Loan", "Liabilities", "Borrowings", "Balance Sheet"),
    (2500, "Term Loan", "Liabilities", "Borrowings", "Balance Sheet"),
    (3000, "Share Capital", "Equity", "Share Capital", "Balance Sheet"),
    (3100, "Retained Earnings", "Equity", "Reserves", "Balance Sheet"),
    (4000, "Revenue - Fasteners", "Revenue", "Product Revenue", "Profit & Loss"),
    (4010, "Revenue - Bearings", "Revenue", "Product Revenue", "Profit & Loss"),
    (4020, "Revenue - Service & AMC", "Revenue", "Service Revenue", "Profit & Loss"),
    (5000, "COGS - Fasteners", "COGS", "Cost of Goods Sold", "Profit & Loss"),
    (5010, "COGS - Bearings", "COGS", "Cost of Goods Sold", "Profit & Loss"),
    (5020, "COGS - Service & AMC", "COGS", "Cost of Services", "Profit & Loss"),
    (6000, "Salaries & Wages", "Operating Expenses", "Employee Cost", "Profit & Loss"),
    (6100, "Rent", "Operating Expenses", "Premises", "Profit & Loss"),
    (6110, "Utilities", "Operating Expenses", "Premises", "Profit & Loss"),
    (6200, "Freight Outward", "Operating Expenses", "Selling & Distribution", "Profit & Loss"),
    (6300, "Marketing & Promotion", "Operating Expenses", "Selling & Distribution", "Profit & Loss"),
    (6400, "IT & Software", "Operating Expenses", "Administration", "Profit & Loss"),
    (6500, "Professional Fees", "Operating Expenses", "Administration", "Profit & Loss"),
    (6600, "Travel & Conveyance", "Operating Expenses", "Administration", "Profit & Loss"),
    (6700, "Repairs & Maintenance", "Operating Expenses", "Premises", "Profit & Loss"),
    (6800, "Insurance", "Operating Expenses", "Administration", "Profit & Loss"),
    (6900, "Office & General Expenses", "Operating Expenses", "Administration", "Profit & Loss"),
    (7000, "Depreciation", "Depreciation", "Depreciation", "Profit & Loss"),
    (7100, "Finance Costs", "Finance Costs", "Finance Costs", "Profit & Loss"),
    (8000, "Income Tax Expense", "Tax", "Income Tax", "Profit & Loss"),
]
CLASS_SORT = {"Revenue": 1, "COGS": 2, "Operating Expenses": 3, "Depreciation": 4,
              "Finance Costs": 5, "Tax": 6, "Assets": 7, "Liabilities": 8, "Equity": 9}

COST_CENTRES = [
    ("CC00", "Corporate / Balance Sheet", "Corporate"),
    ("CC10", "Sales - North", "Sales"),
    ("CC20", "Sales - South", "Sales"),
    ("CC30", "Sales - West", "Sales"),
    ("CC40", "Operations & Warehouse", "Operations"),
    ("CC50", "Finance & Admin", "Support"),
    ("CC60", "IT", "Support"),
]
REGION_CC = {"North": "CC10", "South": "CC20", "West": "CC30"}
REGION_SHARE = {"North": 0.40, "South": 0.35, "West": 0.25}

USERS = [
    ("U01", "SYSTEM", "System / integration batch"),
    ("U02", "Priya Nair", "AR Executive"),
    ("U03", "Rohit Verma", "AP Executive"),
    ("U04", "Anjali Deshmukh", "Payroll Executive"),
    ("U05", "Karan Mehta", "GL Accountant"),
    ("U06", "Sneha Iyer", "GL Accountant"),
    ("U07", "Arvind Rao", "Finance Manager"),
    ("U08", "Meera Kapoor", "Financial Controller"),
]

PRODUCTS = {  # key: (revenue acct, cogs acct, name, plan cogs ratio, invoices per month)
    "F": (4000, 5000, "Fasteners", 0.72, 150),
    "B": (4010, 5010, "Bearings", 0.76, 100),
    "S": (4020, 5020, "Service & AMC", 0.55, 50),
}
ANNUAL_REV_PLAN = {"F": [4500 * LAKH, 4950 * LAKH],
                   "B": [3000 * LAKH, 3600 * LAKH],
                   "S": [1000 * LAKH, 1150 * LAKH]}
SEAS = np.array([0.92, 0.95, 0.97, 0.98, 0.96, 1.00, 1.05, 1.02, 1.00, 1.03, 1.04, 1.08])
SEAS = SEAS / SEAS.mean()

# customers
_c1 = ["Apex", "Bharat", "Coral", "Deccan", "Eastern", "Falcon", "Ganga", "Horizon", "Indus", "Jupiter",
       "Kaveri", "Lotus", "Malabar", "Nimbus", "Orbit", "Pinnacle", "Quantum", "Regal", "Sahyadri", "Trident"]
_c2 = ["Auto Components", "Engineering Works", "Machine Tools", "Fabricators", "Industrial Spares",
       "Precision Parts", "Motors", "Agro Equipment", "Hydraulics", "Castings"]
customers = []
for i in range(60):
    region = ["North", "South", "West"][i % 3]
    name = f"{_c1[i % 20]} {_c2[(i * 7 + i // 20) % 10]}"
    customers.append((f"C{i + 1:03d}", name, region,
                      ["OEM", "Distributor", "Workshop"][int(rng.integers(0, 3))],
                      int(rng.choice([30, 45, 60], p=[0.35, 0.40, 0.25]))))
dim_customer = pd.DataFrame(customers, columns=["customer_id", "customer_name", "region", "segment", "credit_terms_days"])
CUST_BY_REGION = {r: dim_customer[dim_customer.region == r].reset_index(drop=True) for r in REGION_CC}
CUST_WEIGHT = {r: (1 / np.arange(1, len(d) + 1) ** 0.6) / (1 / np.arange(1, len(d) + 1) ** 0.6).sum()
               for r, d in CUST_BY_REGION.items()}
SLOW_CUSTOMERS = {"C004", "C011", "C017", "C026", "C033", "C042"}  # stretch payments in FY26 H2
DISTRESSED = {"C020": pd.Timestamp("2025-07-01"), "C037": pd.Timestamp("2025-11-01")}  # stop paying

# vendors
vendors = [(f"V{i:03d}", f"{n} {s}", "Materials") for i, (n, s) in enumerate(
    [("Sterling", "Steel Traders"), ("Vindhya", "Alloys"), ("Narmada", "Metals"), ("Unity", "Bearings Importers"),
     ("Konkan", "Fastener Mills"), ("Aravali", "Forgings"), ("Triveni", "Wire Products"), ("Meridian", "Industrial Imports"),
     ("Satpura", "Hardware"), ("Nilgiri", "Components"), ("Godavari", "Spares"), ("Everest", "Tooling")], start=1)]
SERVICE_VENDORS = {
    6100: [("V101", "Shreeji Warehousing LLP"), ("V102", "Crescent Office Parks")],
    6110: [("V103", "State Power Distribution Co"), ("V104", "Aqua Utility Services")],
    6200: [("V105", "Swift Roadlines"), ("V106", "Bluedot Cargo Movers"), ("V107", "Trans-Deccan Logistics")],
    6300: [("V108", "Brightside Media"), ("V109", "Expo Events India")],
    6400: [("V110", "Cloudnine IT Solutions"), ("V111", "Netlink Systems")],
    6500: [("V112", "Rao & Sen Chartered Accountants"), ("V113", "Lexpoint Legal Advisors"), ("V114", "Corebridge Consulting")],
    6600: [("V115", "Wayfarer Travel Desk")],
    6700: [("V116", "Techfix Maintenance"), ("V117", "Prime Facility Services")],
    6800: [("V118", "Suraksha General Insurance")],
    6900: [("V119", "Paperline Stationers"), ("V120", "Metro Office Supplies")],
}
for acct, lst in SERVICE_VENDORS.items():
    vendors += [(vid, name, "Services") for vid, name in lst]
vendors.append(("V121", "Stackwell Storage Systems", "Capital Goods"))
dim_vendor = pd.DataFrame(vendors, columns=["vendor_id", "vendor_name", "vendor_category"])
MATERIAL_VENDORS = [v[0] for v in vendors if v[2] == "Materials"]

# ------------------------------------------------------------------- helpers
headers = []   # tmp_id, posting_date, created_at, source, prepared_by, approved_by, description, party_id
lines = []     # tmp_id, account_id, cost_centre_id, amount (debit +, credit -)
seeded = []    # tmp_id, tag
budget = {}    # (month_start, account, cc) -> amount in natural sign


def bday(d, k=0):
    """Business day on or after d, then offset by k business days."""
    return pd.Timestamp(np.busday_offset(np.datetime64(pd.Timestamp(d).date(), "D"), k, roll="forward"))


def at(d, lo=8, hi=20):
    """Timestamp on date d at a random minute between lo:00 and hi:00."""
    return pd.Timestamp(d).normalize() + pd.Timedelta(minutes=int(rng.integers(lo * 60, hi * 60)))


def post(date, source, prep, appr, desc, entry, party="", created=None, tags=()):
    total = round(sum(a for _, _, a in entry), 2)
    assert abs(total) < 0.005, (desc, total)
    tmp = len(headers)
    headers.append((tmp, pd.Timestamp(date), created if created is not None else at(date),
                    source, prep, appr, desc, party))
    for acct, cc, amt in entry:
        if abs(amt) >= 0.005:
            lines.append((tmp, acct, cc, round(amt, 2)))
    for t in tags:
        seeded.append((tmp, t))
    return tmp


def add_budget(period, acct, cc, amt):
    key = (period.start_time.normalize(), acct, cc)
    budget[key] = budget.get(key, 0.0) + amt


def fy(period):
    return 0 if period < pd.Period("2025-04", "M") else 1


def fmonth(period):
    return (period.month - 4) % 12 + 1


def month_bdays(period):
    return pd.bdate_range(period.start_time, period.end_time)


def split(total, n, sigma=0.6):
    w = rng.lognormal(0, sigma, n)
    return np.round(total * w / w.sum(), 0)


def manual_approver(amount):
    return "U08" if amount >= APPROVAL_LIMIT else "U07"


def pay_delay(cust, inv_date):
    if cust in DISTRESSED and inv_date >= DISTRESSED[cust]:
        return None
    late_fy = inv_date >= pd.Timestamp("2025-04-01")
    if cust in SLOW_CUSTOMERS and inv_date >= pd.Timestamp("2025-09-01"):
        return int(rng.gamma(3, 18))
    return int(rng.gamma(2, 8 if late_fy else 4)) - 3


# ----------------------------------------------------- opening receivables
ar_rows = []  # invoice_no, tmp_id, customer, invoice_date, due_date, product, net, gst, gross, paid_date
inv_seq = {"2324": 0, "2425": 0, "2526": 0}


def fy_tag(d):
    y = d.year if d.month >= 4 else d.year - 1
    return f"{str(y)[2:]}{str(y + 1)[2:]}"


def make_invoices(period, rev_target, cogs_ratio, prod, region, n):
    """Return list of invoice dicts for one month / product / region."""
    out = []
    days = month_bdays(period)
    wts = np.linspace(1.0, 1.6, len(days))
    nets = split(rev_target, n, 0.8)
    dts = rng.choice(days, size=n, p=wts / wts.sum())
    cdf = CUST_BY_REGION[region]
    cidx = rng.choice(len(cdf), size=n, p=CUST_WEIGHT[region])
    for net, d, ci in zip(nets, dts, cidx):
        d = pd.Timestamp(d)
        cust = cdf.customer_id[ci]
        terms = int(cdf.credit_terms_days[ci])
        gst = round(net * GST, 2)
        delay = pay_delay(cust, d)
        due = d + pd.Timedelta(days=terms)
        paid = bday(due + pd.Timedelta(days=delay)) if delay is not None else pd.NaT
        if paid is not pd.NaT and paid <= d:
            paid = bday(d, 1)
        tag = fy_tag(d)
        inv_seq[tag] += 1
        out.append(dict(invoice_no=f"INV-{tag}-{inv_seq[tag]:05d}", customer=cust, date=d, due=due, prod=prod,
                        region=region, net=float(net), gst=gst, gross=round(net + gst, 2), paid=paid,
                        cogs=float(round(net * cogs_ratio * (1 + rng.normal(0, 0.02)), 0))))
    return out


opening_ar = 0.0
receipts = []  # (paid_date, invoice_no, customer, gross)
for per in pd.period_range("2024-02", "2024-03", freq="M"):
    for prod, (_, _, _, ratio, n_inv) in PRODUCTS.items():
        for region, share in REGION_SHARE.items():
            target = ANNUAL_REV_PLAN[prod][0] * 0.93 / 12 * share
            for inv in make_invoices(per, target, ratio, prod, region, max(2, round(n_inv * share))):
                if inv["paid"] is not pd.NaT and inv["paid"] < START:
                    continue  # settled before the opening date
                opening_ar += inv["gross"]
                ar_rows.append((inv["invoice_no"], -1, inv["customer"], inv["date"], inv["due"], PRODUCTS[prod][2],
                                inv["net"], inv["gst"], inv["gross"], inv["paid"]))
                if inv["paid"] is not pd.NaT and inv["paid"] <= END:
                    receipts.append((inv["paid"], inv["invoice_no"], inv["customer"], inv["gross"]))
opening_ar = round(opening_ar, 2)

# ------------------------------------------------------- opening balances
OPEN = {1000: 300 * LAKH, 1100: opening_ar, 1200: 1500 * LAKH, 1300: 40 * LAKH, 1400: 30 * LAKH,
        1500: 2200 * LAKH, 1510: -600 * LAKH, 2000: -600 * LAKH, 2100: -90 * LAKH, 2200: -50 * LAKH,
        2500: -1500 * LAKH, 3000: -500 * LAKH}
OPEN[3100] = -round(sum(OPEN.values()), 2)
post(START, "Opening", "U01", "", "Opening balances as at 1 Apr 2024",
     [(a, "CC00", v) for a, v in OPEN.items()], created=at(START, 8, 9))

# --------------------------------------------------------------- sales
actual_rev = {}    # (period, region) -> actual net revenue
plan_rev = {}      # (period, region) -> planned net revenue
month_cogs = {}    # period -> actual cogs
for per in MONTHS:
    f, m = fy(per), fmonth(per)
    for prod, (rev_acct, cogs_acct, pname, ratio, n_inv) in PRODUCTS.items():
        if f == 0:
            pf, act_ratio = 1 + rng.normal(0, 0.025), ratio + rng.normal(0, 0.005)
        else:
            pf = {"F": 0.97, "B": 1.05, "S": 0.98 if m <= 6 else 0.86}[prod] * (1 + rng.normal(0, 0.02))
            act_ratio = {"F": 0.725, "B": 0.78 if m <= 6 else 0.81, "S": 0.555}[prod] + rng.normal(0, 0.005)
        for region, share in REGION_SHARE.items():
            cc = REGION_CC[region]
            plan = ANNUAL_REV_PLAN[prod][f] / 12 * SEAS[m - 1] * share
            add_budget(per, rev_acct, cc, plan)
            add_budget(per, cogs_acct, cc, plan * ratio)
            plan_rev[(per, region)] = plan_rev.get((per, region), 0) + plan
            rf = 1.0 if f == 0 else {"North": 1.03, "South": 1.00, "West": 0.95}[region]
            target = plan * pf * rf * (1 + rng.normal(0, 0.015))
            for inv in make_invoices(per, target, act_ratio, prod, region, max(2, round(n_inv * share))):
                tmp = post(inv["date"], "Sales", "U01", "", f"Sales invoice {inv['invoice_no']} - {pname}",
                           [(1100, "CC00", inv["gross"]), (rev_acct, cc, -inv["net"]), (2100, "CC00", -inv["gst"]),
                            (cogs_acct, cc, inv["cogs"]), (1200, "CC00", -inv["cogs"])], party=inv["customer"])
                ar_rows.append((inv["invoice_no"], tmp, inv["customer"], inv["date"], inv["due"], pname,
                                inv["net"], inv["gst"], inv["gross"], inv["paid"]))
                if inv["paid"] is not pd.NaT and inv["paid"] <= END:
                    receipts.append((inv["paid"], inv["invoice_no"], inv["customer"], inv["gross"]))
                actual_rev[(per, region)] = actual_rev.get((per, region), 0) + inv["net"]
                month_cogs[per] = month_cogs.get(per, 0) + inv["cogs"]

for paid, inv_no, cust, gross in receipts:
    post(paid, "Receipt", "U02", "", f"Receipt against {inv_no}",
         [(1000, "CC00", gross), (1100, "CC00", -gross)], party=cust)

# ------------------------------------------------- vendor invoices / payments
payments = []  # (tmp_id of payment, vendor, gross, pay_date, ref)


def vendor_invoice(date, vendor, net, debit_lines, desc, source="Purchases"):
    gst = round(net * GST, 2)
    gross = round(net + gst, 2)
    post(date, source, "U01", "", desc, debit_lines + [(1300, "CC00", gst), (2000, "CC00", -gross)], party=vendor)
    pay = bday(pd.Timestamp(date) + pd.Timedelta(days=int(rng.choice([30, 45])) + int(rng.integers(0, 11))))
    if pay <= END:
        ref = f"Vendor payment {vendor} - {desc.split(' - ')[0]}"
        tmp = post(pay, "Payment", "U03", "U07", ref, [(2000, "CC00", gross), (1000, "CC00", -gross)], party=vendor)
        payments.append((tmp, vendor, gross, pay, ref))


# opening payables are cleared in the first two months
for amt in split(600 * LAKH, 40, 0.5):
    d = bday(START + pd.Timedelta(days=int(rng.integers(2, 55))))
    v = str(rng.choice(MATERIAL_VENDORS))
    post(d, "Payment", "U03", "U07", f"Vendor payment {v} - opening balance",
         [(2000, "CC00", float(amt)), (1000, "CC00", -float(amt))], party=v)

# material purchases follow the cost of goods sold, with a stock build-up in FY26
bill_no = 0
for per in MONTHS:
    factor = (1.0 if fy(per) == 0 else 1.045) * (1 + rng.normal(0, 0.03))
    days = month_bdays(per)
    for net in split(month_cogs[per] * factor, 50, 0.7):
        bill_no += 1
        v = str(rng.choice(MATERIAL_VENDORS))
        vendor_invoice(pd.Timestamp(rng.choice(days)), v, float(net), [(1200, "CC00", float(net))],
                       f"PINV-{bill_no:05d} - material purchase")

# operating expenses: (account, cost centre) -> FY25 annual plan, FY26 growth
OPEX_PLAN = {
    (6100, "CC40"): (96, 1.05), (6100, "CC50"): (36, 1.05),
    (6110, "CC40"): (54, 1.05), (6110, "CC50"): (12, 1.05),
    (6400, "CC60"): (57.6, 1.05), (6500, "CC50"): (48, 1.05),
    (6600, "CC10"): (20, 1.05), (6600, "CC20"): (18, 1.05), (6600, "CC30"): (14, 1.05), (6600, "CC50"): (8, 1.05),
    (6700, "CC40"): (42, 1.05), (6800, "CC40"): (18, 1.05), (6800, "CC50"): (6, 1.05),
    (6900, "CC50"): (30, 1.05), (6900, "CC40"): (12, 1.05),
}
for per in MONTHS:
    f, m = fy(per), fmonth(per)
    days = month_bdays(per)
    jobs = []  # (account, cc, actual amount, n invoices)
    for (acct, cc), (annual, growth) in OPEX_PLAN.items():
        plan = annual * LAKH / 12 * (growth if f else 1.0)
        add_budget(per, acct, cc, plan)
        actual = plan if acct == 6100 else plan * (1 + rng.normal(0, 0.04))
        jobs.append((acct, cc, actual, 1 if acct in (6100, 6800) else int(rng.integers(1, 4))))
    if per == pd.Period("2025-11", "M"):  # one-off, unbudgeted ERP advisory fee
        jobs.append((6500, "CC50", 45 * LAKH, 1))
    for region, cc in REGION_CC.items():
        add_budget(per, 6200, cc, plan_rev[(per, region)] * 0.032)
        add_budget(per, 6300, cc, plan_rev[(per, region)] * (0.015 if f == 0 else 0.016))
        frt = (0.0325 if f == 0 else (0.039 if m <= 6 else 0.043)) * (1 + rng.normal(0, 0.03))
        jobs.append((6200, cc, actual_rev[(per, region)] * frt, 6))
        mkt = plan_rev[(per, region)] * (0.015 if f == 0 else 0.016 * 0.70) * (1 + rng.normal(0, 0.08))
        jobs.append((6300, cc, mkt, 2))
    for acct, cc, actual, n in jobs:
        vlist = SERVICE_VENDORS[acct]
        for net in split(actual, n, 0.4):
            bill_no += 1
            if acct == 6100:
                v = vlist[0][0] if cc == "CC40" else vlist[1][0]
                d = bday(per.start_time, 2)
            else:
                v = vlist[int(rng.integers(0, len(vlist)))][0]
                d = pd.Timestamp(rng.choice(days))
            name = next(a[1] for a in ACCOUNTS if a[0] == acct)
            vendor_invoice(d, v, float(net), [(acct, cc, float(net))], f"PINV-{bill_no:05d} - {name.lower()}")

# capital expenditure
ppe_gross = 2200 * LAKH
CAPEX = {pd.Period("2024-07", "M"): 60, pd.Period("2025-01", "M"): 35,
         pd.Period("2025-06", "M"): 120, pd.Period("2025-12", "M"): 40}

# payroll, depreciation, loan
SALARY_PLAN = {"CC10": 110, "CC20": 95, "CC30": 70, "CC40": 260, "CC50": 120, "CC60": 60}
loan = 1500 * LAKH
for per in MONTHS:
    f, m = fy(per), fmonth(per)
    last = bday(per.end_time.normalize() - pd.Timedelta(days=3))
    entry, total = [], 0.0
    for cc, annual in SALARY_PLAN.items():
        plan = annual * LAKH / 12 * (1.08 if f else 1.0)
        add_budget(per, 6000, cc, plan)
        k = 1 + rng.normal(0, 0.012)
        if f and cc == "CC40" and m > 6:
            k *= 1.06   # overtime in the warehouse
        if f and cc == "CC60":
            k *= 0.88   # unfilled positions
        amt = round(plan * k, 0)
        entry.append((6000, cc, amt))
        total += amt
    post(last, "Payroll", "U04", "U08", f"Payroll for {per.strftime('%b %Y')}", entry + [(1000, "CC00", -total)])

    if per in CAPEX:
        net = CAPEX[per] * LAKH
        bill_no += 1
        vendor_invoice(bday(per.start_time, 9), "V121", net, [(1500, "CC00", net)],
                       f"PINV-{bill_no:05d} - warehouse racking and equipment")
    dep = round(ppe_gross * 0.10 / 12, 0)
    if per in CAPEX:
        ppe_gross += CAPEX[per] * LAKH
    dep_split = [("CC40", 0.8), ("CC50", 0.1), ("CC60", 0.1)]
    dep_50, dep_60 = round(dep * 0.1, 0), round(dep * 0.1, 0)
    post(per.end_time.normalize(), "Fixed Assets", "U01", "", f"Depreciation run {per.strftime('%b %Y')}",
         [(7000, "CC40", dep - dep_50 - dep_60), (7000, "CC50", dep_50), (7000, "CC60", dep_60), (1510, "CC00", -dep)],
         created=at(bday(per.end_time.normalize())))
    for cc, s in dep_split:
        add_budget(per, 7000, cc, (220 if f == 0 else 235) * LAKH / 12 * s)

    interest = round(loan * 0.10 / 12, 0)
    post(bday(per.end_time.normalize() - pd.Timedelta(days=1)), "Bank", "U01", "", f"Term loan interest {per.strftime('%b %Y')}",
         [(7100, "CC00", interest), (1000, "CC00", -interest)])
    add_budget(per, 7100, "CC00", (150 if f == 0 else 140) * LAKH / 12)
    if m % 3 == 0:
        post(bday(per.end_time.normalize() - pd.Timedelta(days=1)), "Bank", "U01", "", "Term loan principal repayment",
             [(2500, "CC00", 50 * LAKH), (1000, "CC00", -50 * LAKH)])
        loan -= 50 * LAKH

# working capital loan drawn when collections slowed
post(pd.Timestamp("2025-10-15"), "Bank", "U01", "", "Working capital loan drawdown",
     [(1000, "CC00", 400 * LAKH), (2400, "CC00", -400 * LAKH)])

# ------------------------------------------------------------ GST settlement
_l = pd.DataFrame(lines, columns=["tmp", "account", "cc", "amount"])
_h = pd.DataFrame(headers, columns=["tmp", "date", "created", "source", "prep", "appr", "desc", "party"])
_l = _l.merge(_h[["tmp", "date", "source"]], on="tmp")
_l["per"] = _l["date"].dt.to_period("M")
gst_mv = _l[_l.source != "Opening"].pivot_table(index="per", columns="account", values="amount", aggfunc="sum").fillna(0)
out_due, in_avail = -OPEN[2100], OPEN[1300]
for i, per in enumerate(MONTHS):
    used = min(in_avail, out_due)
    cash = round(out_due - used, 2)
    post(bday(per.start_time + pd.Timedelta(days=19)), "Bank", "U01", "", f"GST payment for {(per - 1).strftime('%b %Y')}",
         [(2100, "CC00", out_due), (1300, "CC00", -used), (1000, "CC00", -cash)])
    in_avail = round(in_avail - used + gst_mv.loc[per, 1300], 2)
    out_due = round(-gst_mv.loc[per, 2100], 2)

# ------------------------------------------------- routine manual journals
OPEX_ACCTS = [(6110, "CC40"), (6200, "CC10"), (6200, "CC20"), (6300, "CC10"), (6400, "CC60"), (6500, "CC50"),
              (6600, "CC20"), (6700, "CC40"), (6900, "CC50"), (6900, "CC40")]
for per in MONTHS:
    eom = per.end_time.normalize()
    close_day = bday(eom)
    for _ in range(int(rng.integers(6, 11))):
        acct, cc = OPEX_ACCTS[int(rng.integers(0, len(OPEX_ACCTS)))]
        amt = float(round(rng.lognormal(11.6, 0.7), 0))
        prep = str(rng.choice(["U05", "U06"]))
        name = next(a[1] for a in ACCOUNTS if a[0] == acct)
        created = at(bday(close_day, int(rng.integers(0, 4))), 9, 19)
        post(eom, "Manual", prep, manual_approver(amt), f"Accrual - {name.lower()} {per.strftime('%b %Y')}",
             [(acct, cc, amt), (2200, "CC00", -amt)], created=created)
        if per < MONTHS[-1]:
            post(eom + pd.Timedelta(days=1), "Manual", prep, manual_approver(amt),
                 f"Reversal of accrual - {name.lower()} {per.strftime('%b %Y')}",
                 [(acct, cc, -amt), (2200, "CC00", amt)], created=created + pd.Timedelta(minutes=1))
    for _ in range(int(rng.integers(3, 7))):
        acct = int(rng.choice([6600, 6900, 6110, 6800]))
        a, b = rng.choice(["CC10", "CC20", "CC30", "CC40", "CC50", "CC60"], size=2, replace=False)
        amt = float(round(rng.lognormal(10.8, 0.6), 0))
        d = pd.Timestamp(rng.choice(month_bdays(per)))
        post(d, "Manual", str(rng.choice(["U05", "U06"])), manual_approver(amt),
             f"Cost centre reallocation {a} to {b}", [(acct, str(b), amt), (acct, str(a), -amt)], created=at(d, 9, 19))
    post(eom, "Manual", "U05", "U07", f"Prepaid amortisation - software AMC {per.strftime('%b %Y')}",
         [(6400, "CC60", 120_000), (1400, "CC00", -120_000)], created=at(close_day, 9, 19))
    add_budget(per, 6400, "CC60", 120_000)

# income tax: monthly provision on profit before tax, advance tax paid quarterly
_l = pd.DataFrame(lines, columns=["tmp", "account", "cc", "amount"])
_h = pd.DataFrame(headers, columns=["tmp", "date", "created", "source", "prep", "appr", "desc", "party"])
_l = _l.merge(_h[["tmp", "date"]], on="tmp")
_l["per"] = _l["date"].dt.to_period("M")
pbt = -_l[(_l.account >= 4000) & (_l.account < 8000)].groupby("per")["amount"].sum()
unpaid = 0.0
for per in MONTHS:
    prov = float(max(0.0, round(pbt[per] * 0.2517, 0)))
    eom = per.end_time.normalize()
    post(eom, "Manual", "U05", "U08", f"Income tax provision {per.strftime('%b %Y')}",
         [(8000, "CC00", prov), (2300, "CC00", -prov)], created=at(bday(eom, 3), 9, 19))
    unpaid += prov
    bud_pbt = sum((1 if a < 5000 else -1) * v for (d, a, c), v in budget.items()
                  if d == per.start_time.normalize() and a < 8000)
    add_budget(per, 8000, "CC00", bud_pbt * 0.2517)
    if fmonth(per) % 3 == 0:
        pay = round(unpaid * 0.9, 0)
        post(bday(per.start_time + pd.Timedelta(days=14)), "Bank", "U01", "", "Advance income tax payment",
             [(2300, "CC00", pay), (1000, "CC00", -pay)])
        unpaid -= pay

# ----------------------------------------------------- seeded exceptions
ALL_BDAYS = pd.bdate_range(START + pd.Timedelta(days=10), END - pd.Timedelta(days=50))
WEEKENDS = [d for d in pd.date_range(START + pd.Timedelta(days=10), END - pd.Timedelta(days=20)) if d.weekday() >= 5]
EXP = [(6500, "CC50"), (6900, "CC50"), (6300, "CC10"), (6600, "CC20"), (6700, "CC40"), (6300, "CC20")]


def rand_bday():
    return pd.Timestamp(rng.choice(ALL_BDAYS))


def seed(tags, amount, posting=None, created=None, prep=None, appr=None, desc=None, dr=None, cr=(2200, "CC00")):
    posting = posting if posting is not None else rand_bday()
    created = created if created is not None else at(posting, 9, 19)
    prep = prep or str(rng.choice(["U05", "U06"]))
    appr = appr or manual_approver(amount)
    if dr is None:  # default: move cost between cost centres, no effect on total expense
        acct, _ = EXP[int(rng.integers(0, len(EXP)))]
        a, b = rng.choice(["CC10", "CC20", "CC30", "CC40", "CC50", "CC60"], size=2, replace=False)
        dr, cr = (acct, str(a)), (acct, str(b))
        name = next(x[1] for x in ACCOUNTS if x[0] == acct)
        desc = desc if desc is not None else f"Expense reclassification - {name.lower()}"
    name = next(a[1] for a in ACCOUNTS if a[0] == dr[0])
    desc = desc if desc is not None else f"Provision for {name.lower()} - pending invoice"
    return post(posting, "Manual", prep, appr, desc, [(dr[0], dr[1], amount), (cr[0], cr[1], -amount)],
                created=created, tags=tags)


for d in rng.choice(WEEKENDS, size=9, replace=False):          # entered on a weekend
    seed(["weekend"], float(rng.integers(60_000, 350_000)), posting=pd.Timestamp(d), created=at(d, 10, 18))
for i in range(7):                                             # entered late at night
    d = rand_bday()
    hour_lo, hour_hi = (22, 24) if i % 2 == 0 else (0, 5)
    seed(["after_hours"] + (["self_approved"] if i == 0 else []), float(rng.integers(40_000, 420_000)),
         posting=d, created=at(d, hour_lo, hour_hi), **({"prep": "U06", "appr": "U06"} if i == 0 else {}))
for i, amt in enumerate([100_000, 100_000, 200_000, 200_000, 200_000, 300_000, 300_000, 400_000, 500_000, 700_000]):
    seed(["round_amount"] + (["weak_description"] if i == 0 else []), float(amt),   # round-sum provisions, never reversed
         dr=(6900, "CC50"), **({"desc": "adj"} if i == 0 else {}))
split_days = [rand_bday(), rand_bday()]
for i in range(8):                                             # just under the approval limit
    d = split_days[i // 2] if i < 4 else rand_bday()
    seed(["below_limit"], float(rng.integers(4_800, 5_000) * 100), posting=d, prep="U06", appr="U07",
         dr=(6500, "CC50") if i < 4 else None,
         desc=f"Consultancy charges - part {i % 2 + 1}" if i < 4 else None)
for who in ["U05", "U05", "U06", "U06", "U07"]:                # prepared and approved by the same user
    seed(["self_approved"], float(rng.integers(50_000, 400_000)), prep=who, appr=who)
for desc in ["", "JV", "misc", "corr", "entry", "", "tfr"]:    # no meaningful narration
    seed(["weak_description"], float(rng.integers(30_000, 380_000)), desc=desc)
for _ in range(5):                                             # posted into an earlier period
    d = rand_bday()
    seed(["backdated"], float(rng.integers(80_000, 450_000)), posting=d,
         created=at(bday(d + pd.Timedelta(days=int(rng.integers(20, 46)))), 9, 19))
for amt in [560_000, 825_000, 1_240_000]:                      # above the limit without controller approval
    seed(["limit_breach"], float(amt + int(rng.integers(1, 900))), appr="U07")

# top-side revenue journals at period end
for d, amt, prep, appr, acct, rev_back in [
    ("2025-03-31", 38 * LAKH + 4_250, "U07", "U08", 4000, "2025-04-03"),
    ("2025-09-30", 24 * LAKH + 1_800, "U07", "U08", 4010, "2025-10-06"),
    ("2026-03-31", 62 * LAKH + 7_300, "U07", "U07", 4010, None),
]:
    d = pd.Timestamp(d)
    tags = ["manual_revenue"] + (["self_approved", "limit_breach"] if appr == "U07" else [])
    post(d, "Manual", prep, appr, "Revenue accrual - goods dispatched not invoiced",
         [(1150, "CC00", amt), (acct, "CC10", -amt)], created=at(bday(d), 17, 20), tags=tags)
    if rev_back:
        post(pd.Timestamp(rev_back), "Manual", prep, appr, "Reversal of revenue accrual",
             [(1150, "CC00", -amt), (acct, "CC10", amt)], created=at(rev_back, 10, 17), tags=["manual_revenue"])

# manual journal posted straight to the receivables control account
post(pd.Timestamp("2025-08-22"), "Manual", "U05", "U07", "Write-off of small customer balances",
     [(6900, "CC50", 318_450), (1100, "CC00", -318_450)], created=at("2025-08-22", 10, 17),
     tags=["ar_control_account"])

# vendor invoices paid twice
cands = [p for p in payments if p[3] <= END - pd.Timedelta(days=15) and p[2] > 150_000]
for i in rng.choice(len(cands), size=5, replace=False):
    _, vendor, gross, pay, ref = cands[int(i)]
    tmp = post(bday(pay, int(rng.integers(1, 5))), "Payment", "U03", "U07", ref,
               [(2000, "CC00", gross), (1000, "CC00", -gross)], party=vendor, tags=["duplicate_payment"])
    seeded.append((cands[int(i)][0], "duplicate_payment"))

# -------------------------------------------------------------------- output
H = pd.DataFrame(headers, columns=["tmp", "posting_date", "created_at", "source", "prepared_by", "approved_by",
                                   "description", "party_id"])
L = pd.DataFrame(lines, columns=["tmp", "account_id", "cost_centre_id", "amount"])
H = H.sort_values(["created_at", "tmp"], kind="stable").reset_index(drop=True)
H["journal_id"] = [f"JE{i + 1:06d}" for i in range(len(H))]
idmap = dict(zip(H.tmp, H.journal_id))
L["journal_id"] = L.tmp.map(idmap)
L = L.sort_values(["journal_id"], kind="stable").reset_index(drop=True)
L["line_no"] = L.groupby("journal_id").cumcount() + 1
L["debit"] = L.amount.clip(lower=0).round(2)
L["credit"] = (-L.amount).clip(lower=0).round(2)
H = H.merge(L.groupby("journal_id")["debit"].sum().round(2).rename("journal_amount"), on="journal_id")

H["posting_date"] = H.posting_date.dt.strftime("%Y-%m-%d")
H["created_at"] = H.created_at.dt.strftime("%Y-%m-%d %H:%M:%S")
H[["journal_id", "posting_date", "created_at", "source", "prepared_by", "approved_by", "description",
   "party_id", "journal_amount"]].to_csv(DATA / "journal_header.csv", index=False)
L[["journal_id", "line_no", "account_id", "cost_centre_id", "debit", "credit", "amount"]].to_csv(
    DATA / "journal_lines.csv", index=False)

AR = pd.DataFrame(ar_rows, columns=["invoice_no", "tmp", "customer_id", "invoice_date", "due_date", "product_line",
                                    "net_amount", "gst_amount", "gross_amount", "paid_date"])
AR["journal_id"] = AR.tmp.map(idmap).fillna("")
AR.loc[AR.paid_date > END, "paid_date"] = pd.NaT
AR["status"] = np.where(AR.paid_date.isna(), "Open", "Paid")
for c in ["invoice_date", "due_date", "paid_date"]:
    AR[c] = pd.to_datetime(AR[c]).dt.strftime("%Y-%m-%d")
AR.sort_values(["invoice_date", "invoice_no"])[
    ["invoice_no", "journal_id", "customer_id", "invoice_date", "due_date", "product_line", "net_amount",
     "gst_amount", "gross_amount", "paid_date", "status"]].to_csv(DATA / "ar_invoices.csv", index=False)

B = pd.Series(budget).rename("budget_amount").reset_index()
B.columns = ["month_start", "account_id", "cost_centre_id", "budget_amount"]
B["budget_amount"] = B.budget_amount.round(0)
B["month_start"] = B.month_start.dt.strftime("%Y-%m-%d")
B.sort_values(["month_start", "account_id", "cost_centre_id"]).to_csv(DATA / "budget.csv", index=False)

A = pd.DataFrame(ACCOUNTS, columns=["account_id", "account_name", "account_class", "account_subclass", "statement"])
A["class_sort"] = A.account_class.map(CLASS_SORT)
A["product_line"] = A.account_id.map({4000: "Fasteners", 5000: "Fasteners", 4010: "Bearings", 5010: "Bearings",
                                      4020: "Service & AMC", 5020: "Service & AMC"}).fillna("Not applicable")
A.to_csv(DATA / "dim_account.csv", index=False)
pd.DataFrame(COST_CENTRES, columns=["cost_centre_id", "cost_centre_name", "function"]).to_csv(
    DATA / "dim_cost_centre.csv", index=False)
pd.DataFrame(USERS, columns=["user_id", "user_name", "role"]).to_csv(DATA / "dim_user.csv", index=False)
dim_customer.to_csv(DATA / "dim_customer.csv", index=False)
dim_vendor.to_csv(DATA / "dim_vendor.csv", index=False)

D = pd.DataFrame({"date": pd.date_range(START, END)})
D["year"] = D.date.dt.year
D["month_no"] = D.date.dt.month
D["month_name"] = D.date.dt.strftime("%b")
D["month_start"] = D.date.dt.to_period("M").dt.start_time
D["month_label"] = D.date.dt.strftime("%b %Y")
D["month_sort"] = D.year * 100 + D.month_no
fy_start = np.where(D.month_no >= 4, D.year, D.year - 1)
D["fiscal_year"] = [f"FY{y}-{str(y + 1)[2:]}" for y in fy_start]
D["fiscal_month_no"] = (D.month_no - 4) % 12 + 1
D["fiscal_quarter"] = "Q" + ((D.fiscal_month_no - 1) // 3 + 1).astype(str)
D["day_name"] = D.date.dt.strftime("%a")
D["is_weekend"] = D.date.dt.weekday >= 5
D["date"] = D.date.dt.strftime("%Y-%m-%d")
D["month_start"] = D.month_start.dt.strftime("%Y-%m-%d")
D.to_csv(DATA / "dim_date.csv", index=False)

S = pd.DataFrame(seeded, columns=["tmp", "seeded_exception"])
S["journal_id"] = S.tmp.map(idmap)
S.groupby("journal_id")["seeded_exception"].agg(lambda s: "; ".join(sorted(set(s)))).reset_index().to_csv(
    VAL / "seeded_exceptions.csv", index=False)

print(f"journals {len(H):,} | lines {len(L):,} | AR invoices {len(AR):,} | budget rows {len(B):,} | "
      f"seeded journals {S.journal_id.nunique()}")
