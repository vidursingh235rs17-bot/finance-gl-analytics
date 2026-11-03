# Expected results (control totals)

Produced by `scripts/validate.py` from the CSV files. Amounts are in INR crore unless stated.
If a Power BI measure disagrees with a figure here, the measure or a relationship is wrong.

## 1. Integrity

- Journals: 19,638; journal lines: 63,473; every journal balances to zero.
- Trial balance nets to -0.00.
- Journals by source: Sales 7,200, Receipt 7,025, Purchases 2,395, Payment 2,300, Manual 604, Bank 65, Payroll 24, Fixed Assets 24, Opening 1.

## 2. Profit & loss: actual vs budget

| Line | FY25 Actual | FY25 Budget | FY26 Actual | FY26 Budget | FY26 Var | FY26 vs FY25 |
|---|---:|---:|---:|---:|---:|---:|
| Revenue | 85.27 | 85.00 | 96.41 | 97.00 | -0.59 | +13.1% |
| COGS | 60.60 | 60.70 | 70.68 | 69.32 | -1.36 | +16.6% |
| Gross Profit | 24.67 | 24.30 | 25.73 | 27.68 | -1.95 | +4.3% |
| Operating Expenses | 16.41 | 16.01 | 18.58 | 17.47 | -1.11 | +13.2% |
| EBITDA | 8.26 | 8.29 | 7.15 | 10.20 | -3.05 | -13.5% |
| Depreciation | 2.25 | 2.20 | 2.39 | 2.35 | -0.05 | +6.6% |
| EBIT | 6.02 | 6.09 | 4.75 | 7.85 | -3.10 | -21.0% |
| Finance Costs | 1.43 | 1.50 | 1.22 | 1.40 | 0.18 | -14.0% |
| Profit Before Tax | 4.59 | 4.59 | 3.53 | 6.45 | -2.92 | -23.2% |
| Tax | 1.12 | 1.16 | 0.93 | 1.62 | 0.69 | -16.6% |
| Profit After Tax | 3.47 | 3.44 | 2.60 | 4.83 | -2.23 | -25.3% |

Variance is shown as favourable (+) / adverse (-).

| Ratio | FY25 Actual | FY26 Actual | FY26 Budget |
|---|---:|---:|---:|
| Gross margin % | 28.9% | 26.7% | 28.5% |
| EBITDA margin % | 9.7% | 7.4% | 10.5% |
| PAT margin % | 4.1% | 2.7% | 5.0% |

### FY26 variance by account (INR lakh, favourable + / adverse -)

| Account | Actual | Budget | Variance | Var % |
|---|---:|---:|---:|---:|
| 4000 Revenue - Fasteners | 4,732.3 | 4,950.0 | -217.7 | -4.4% |
| 4010 Revenue - Bearings | 3,846.4 | 3,600.0 | +246.4 | +6.8% |
| 4020 Revenue - Service & AMC | 1,062.1 | 1,150.0 | -87.9 | -7.6% |
| 5000 COGS - Fasteners | 3,469.6 | 3,564.0 | +94.4 | +2.6% |
| 5010 COGS - Bearings | 3,008.8 | 2,736.0 | -272.8 | -10.0% |
| 5020 COGS - Service & AMC | 589.8 | 632.5 | +42.7 | +6.7% |
| 6000 Salaries & Wages | 773.2 | 772.2 | -1.0 | -0.1% |
| 6100 Rent | 138.6 | 138.6 | +0.0 | +0.0% |
| 6110 Utilities | 68.7 | 69.3 | +0.6 | +0.8% |
| 6200 Freight Outward | 395.5 | 310.4 | -85.1 | -27.4% |
| 6300 Marketing & Promotion | 110.9 | 155.2 | +44.3 | +28.5% |
| 6400 IT & Software | 75.9 | 74.9 | -1.0 | -1.4% |
| 6500 Professional Fees | 104.3 | 50.4 | -53.9 | -106.9% |
| 6600 Travel & Conveyance | 62.1 | 63.0 | +0.9 | +1.4% |
| 6700 Repairs & Maintenance | 44.3 | 44.1 | -0.2 | -0.5% |
| 6800 Insurance | 25.0 | 25.2 | +0.2 | +1.0% |
| 6900 Office & General Expenses | 59.4 | 44.1 | -15.3 | -34.7% |
| 7000 Depreciation | 239.5 | 235.0 | -4.5 | -1.9% |
| 7100 Finance Costs | 122.5 | 140.0 | +17.5 | +12.5% |
| 8000 Income Tax Expense | 93.2 | 162.4 | +69.2 | +42.6% |

### Gross margin % by product line

| Product | FY25 | FY26 H1 | FY26 H2 |
|---|---:|---:|---:|
| Fasteners | 28.6% | 26.1% | 27.2% |
| Bearings | 24.1% | 23.1% | 20.6% |
| Service & AMC | 45.2% | 44.6% | 44.3% |

### Monthly revenue and EBITDA (INR lakh)

| Month | Revenue | Budget revenue | EBITDA |
|---|---:|---:|---:|
| Apr 2024 | 644.3 | 651.7 | 32.8 |
| May 2024 | 680.6 | 672.9 | 64.9 |
| Jun 2024 | 686.9 | 687.1 | 51.8 |
| Jul 2024 | 674.7 | 694.2 | 66.2 |
| Aug 2024 | 680.3 | 680.0 | 69.1 |
| Sep 2024 | 698.3 | 708.3 | 65.4 |
| Oct 2024 | 750.2 | 743.8 | 78.8 |
| Nov 2024 | 726.2 | 722.5 | 66.0 |
| Dec 2024 | 700.4 | 708.3 | 62.4 |
| Jan 2025 | 730.6 | 729.6 | 76.4 |
| Feb 2025 | 739.4 | 736.7 | 68.9 |
| Mar 2025 | 815.0 | 765.0 | 123.4 |
| Apr 2025 | 716.3 | 743.7 | 30.8 |
| May 2025 | 772.8 | 767.9 | 64.8 |
| Jun 2025 | 779.8 | 784.1 | 64.2 |
| Jul 2025 | 799.3 | 792.2 | 70.1 |
| Aug 2025 | 749.8 | 776.0 | 50.5 |
| Sep 2025 | 832.6 | 808.3 | 88.5 |
| Oct 2025 | 801.8 | 848.8 | 37.7 |
| Nov 2025 | 811.9 | 824.5 | 7.7 |
| Dec 2025 | 792.8 | 808.3 | 57.3 |
| Jan 2026 | 818.2 | 832.6 | 51.9 |
| Feb 2026 | 829.3 | 840.7 | 50.2 |
| Mar 2026 | 936.3 | 873.0 | 141.1 |

## 3. Balance sheet

| Account | 31 Mar 2025 | 31 Mar 2026 |
|---|---:|---:|
| 1000 Bank - Current Account | 7.33 | 5.12 |
| 1100 Trade Receivables | 15.35 | 22.32 |
| 1150 Unbilled Revenue | 0.38 | 0.62 |
| 1200 Inventory | 14.97 | 18.25 |
| 1300 GST Input Credit | 1.17 | 1.41 |
| 1400 Prepaid Expenses | 0.16 | 0.01 |
| 1500 Property, Plant & Equipment | 22.95 | 24.55 |
| 1510 Accumulated Depreciation | -8.25 | -10.64 |
| 2000 Trade Payables | 9.96 | 12.54 |
| 2100 GST Output Payable | 1.40 | 1.57 |
| 2200 Accrued Expenses | 0.86 | 1.09 |
| 2300 Provision for Income Tax | 0.04 | 0.03 |
| 2400 Working Capital Loan | -0.00 | 4.00 |
| 2500 Term Loan | 13.00 | 11.00 |
| 3000 Share Capital | 5.00 | 5.00 |
| 3100 Retained Earnings | 20.34 | 20.34 |
| Cumulative profit since 1 Apr 2024 (not yet closed to 3100) | 3.47 | 6.07 |

Assets are shown positive; liabilities and equity are shown positive (credit balances).
Lowest bank balance in the period: INR 3.63 crore on 01 Apr 2024.

## 4. Receivables

- Receivables per general ledger (account 1100) at 31 Mar 2026: INR 223,197,514.62
- Open invoices per sub-ledger at 31 Mar 2026: INR 223,515,964.62
- Unreconciled difference (GL less sub-ledger): INR -318,450.00

| Ageing bucket (days past due) | Amount (INR crore) | Invoices | Share |
|---|---:|---:|---:|
| Not due | 14.91 | 443 | 66.7% |
| 1-30 | 4.61 | 147 | 20.6% |
| 31-60 | 1.02 | 38 | 4.6% |
| 61-90 | 0.68 | 16 | 3.0% |
| 91-180 | 0.43 | 15 | 1.9% |
| Over 180 | 0.69 | 15 | 3.1% |

| Top overdue customers (over 90 days) | Amount (INR lakh) | Invoices |
|---|---:|---:|
| C020 Trident Fabricators | 111.2 | 28 |
| C004 Deccan Engineering Works | 0.9 | 1 |
| C037 Quantum Fabricators | 0.6 | 1 |

| Quarter end | Receivables (INR crore) | Gross invoiced in quarter (INR crore) | DSO (days) |
|---|---:|---:|---:|
| 30 Jun 2024 | 14.23 | 23.74 | 55 |
| 30 Sep 2024 | 13.73 | 24.23 | 52 |
| 31 Dec 2024 | 13.40 | 25.69 | 48 |
| 31 Mar 2025 | 15.35 | 26.51 | 52 |
| 30 Jun 2025 | 17.34 | 27.22 | 58 |
| 30 Sep 2025 | 18.11 | 27.82 | 60 |
| 31 Dec 2025 | 19.57 | 28.68 | 63 |
| 31 Mar 2026 | 22.32 | 29.76 | 68 |

## 5. Journal entry testing

Population: 604 manual journals with a total value of INR 11.99 crore (3.1% of all journals by count).

| Test | Journals flagged | Value (INR lakh) |
|---|---:|---:|
| T1 Entered on a weekend | 9 | 17.4 |
| T2 Entered after hours (21:00-06:00) | 7 | 18.6 |
| T3 Round amount (multiple of INR 1,00,000) | 10 | 30.0 |
| T4 Just below approval limit (INR 4.5-5.0 lakh) | 13 | 62.4 |
| T5 Prepared and approved by same user | 7 | 78.9 |
| T6 Missing or weak description | 8 | 11.9 |
| T7 Backdated more than 10 days | 5 | 9.3 |
| T8 Above limit without controller approval | 4 | 88.3 |
| T9 Manual journal to revenue | 5 | 186.2 |
| T10 Manual journal to receivables control | 1 | 3.2 |
| T11 Possible duplicate vendor payment (same vendor and amount within 7 days) | 10 (5 pairs) | 88.5 |

- Manual journals with at least one flag (T1-T10): 65
- Manual journals with two or more flags: 3
- All flagged journals including duplicate payments (T1-T11): 75
- Total flag hits (rows in the JournalFlags table): 79
- Amount at risk from duplicate payments (one payment of each pair): INR 44.2 lakh

| Journals with the most flags | Posting date | Amount (INR) | Flags | Description |
|---|---|---:|---:|---|
| JE019632 | 31 Mar 2026 | 6,207,300 | 3 | Revenue accrual - goods dispatched not invoiced |
| JE007945 | 22 Jan 2025 | 256,216 | 2 | Expense reclassification - office & general expenses |
| JE007866 | 20 Jan 2025 | 100,000 | 2 | adj |
| JE009815 | 31 Mar 2025 | 3,804,250 | 1 | Revenue accrual - goods dispatched not invoiced |
| JE009908 | 03 Apr 2025 | 3,804,250 | 1 | Reversal of revenue accrual |
| JE014757 | 30 Sep 2025 | 2,401,800 | 1 | Revenue accrual - goods dispatched not invoiced |
| JE014885 | 06 Oct 2025 | 2,401,800 | 1 | Reversal of revenue accrual |
| JE007117 | 23 Dec 2024 | 1,240,133 | 1 | Expense reclassification - repairs & maintenance |

### Check against the seeded exceptions

- Seeded journals: 70; found by the tests: 70; missed: 0.
- Flagged journals that were not seeded (false positives to clear by enquiry): 5.

## 6. Cash flow (indirect method)

| Section | Line | FY25 | FY26 |
|---|---|---:|---:|
| Operating | Profit after tax | 3.47 | 2.60 |
| Operating | Depreciation added back | 2.25 | 2.39 |
| Operating | Trade receivables | -2.31 | -6.97 |
| Operating | Inventory | 0.03 | -3.27 |
| Operating | Trade payables | 3.96 | 2.58 |
| Operating | Other working capital | -0.11 | 0.06 |
| Investing | Capital expenditure | -0.95 | -1.60 |
| Financing | Borrowings | -2.00 | 2.00 |
| Financing | Equity | -0.00 | -0.00 |
| **Operating** | **Total** | **7.28** | **-2.61** |
| **Investing** | **Total** | **-0.95** | **-1.60** |
| **Financing** | **Total** | **-2.00** | **2.00** |

- Net cash flow: FY25 4.33, FY26 -2.21; equals the movement in account 1000.
- Opening cash: FY25 3.00, FY26 7.33. Closing cash: FY25 7.33, FY26 5.12.
