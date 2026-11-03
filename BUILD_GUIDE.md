# Build guide: from CSV files to a finished Power BI report

Work through the steps in order. Budget about two evenings: one for the model and measures, one for the pages.
Check your numbers against [validation/expected_results.md](validation/expected_results.md) as you go.

## 1. Install Power BI Desktop

Open the Microsoft Store, search for **Power BI Desktop**, and install it. It is free and needs no account to build reports.

## 2. Load the data

1. Open Power BI Desktop and choose **Home > Transform data**.
2. Choose **Manage Parameters > New**. Name it `DataFolder`, type **Text**, and set the value to the full path of the `data` folder.
3. For each query in [powerbi/power_query.m](powerbi/power_query.m): choose **New Source > Blank Query**, open **Advanced Editor**, paste the block, and rename the query to the name in its heading. Create them in the order they appear, because `Journal` depends on `GL` and `JournalFlags` depends on `Journal`.
4. Choose **Close & Apply**.

You should now have 11 tables. Row counts to confirm: `Journal` 19,638, `GL` 63,473, `ARInvoice` 7,699, `Budget` 1,200, `JournalFlags` 79.

Read each query before moving on. An interviewer may ask how a test such as T11 (duplicate payments) works, and the answer is in the `Journal` query.

## 3. Build the model

In **Model view**, delete any relationships Power BI created automatically, then create these. All are one-to-many with single-direction filtering.

| From (one side) | To (many side) |
|---|---|
| `Date[date]` | `Journal[posting_date]` |
| `Journal[journal_id]` | `GL[journal_id]` |
| `Account[account_id]` | `GL[account_id]` |
| `CostCentre[cost_centre_id]` | `GL[cost_centre_id]` |
| `Date[date]` | `Budget[month_start]` |
| `Account[account_id]` | `Budget[account_id]` |
| `CostCentre[cost_centre_id]` | `Budget[cost_centre_id]` |
| `Date[date]` | `ARInvoice[invoice_date]` |
| `Customer[customer_id]` | `ARInvoice[customer_id]` |
| `Journal[journal_id]` | `JournalFlags[journal_id]` |
| `User[user_id]` | `Journal[prepared_by]` |
| `Vendor[vendor_id]` | `Journal[party_id]` |

Then:

- Right-click `Date` and choose **Mark as date table**, using the `date` column.
- Set **Sort by column**: `Date[month_label]` by `month_sort`, `Account[account_class]` by `class_sort`, `ARInvoice[ageing_bucket]` by `ageing_sort`, `JournalFlags[test_name]` by `test_sort`.
- Hide the key columns on the fact tables (`GL[account_id]`, `Budget[account_id]` and so on) so report users pick fields from the dimension tables.

The posting date sits on the journal header, so date filters reach the ledger lines through `Date > Journal > GL`. This mirrors how an ERP stores a header table and a line table.

## 4. Add the measures

1. Choose **Home > Enter data**, name the table `Measures`, and load it.
2. Add each measure in [powerbi/measures.dax](powerbi/measures.dax) with **New measure**.
3. Apply formats: percentages to one decimal, day counts as whole numbers, and amounts with a thousands separator.

To show amounts in crore, add display measures such as `Revenue (Cr) = DIVIDE ( [Revenue], 10000000 )` and format them to two decimals. Keep the base measures in rupees so they tie to the control totals.

**Stop and check.** Put `Revenue`, `Budget Revenue`, `EBITDA` and `PAT` in a table with `Date[fiscal_year]`. You should see revenue of 85.27 crore and 96.41 crore, and EBITDA of 8.26 crore and 7.15 crore. `Balance Sheet Check` must be zero for any date.

## 5. Build the pages

Choose **View > Themes > Browse for themes** and load [powerbi/theme.json](powerbi/theme.json). Put a `Date[fiscal_year]` slicer on pages 1 to 3 and default it to FY2025-26.

### Page 1: Performance summary

| Visual | Fields |
|---|---|
| Six cards | `Revenue`, `Revenue Var %`, `Gross Margin %`, `EBITDA`, `EBITDA Var`, `PAT` |
| Line and clustered column chart | Axis `Date[month_label]`; columns `Revenue`, `Budget Revenue`; line `EBITDA Margin %` |
| Clustered bar chart | Axis `CostCentre[cost_centre_name]`; values `Revenue`, `Budget Revenue` (filter `CostCentre[function]` = Sales) |
| Line chart | Axis `Date[month_label]`; values `Gross Margin %`, `Gross Margin % PY` |
| Text box | Three lines of commentary, written by you |

### Page 2: Budget variance

| Visual | Fields |
|---|---|
| Waterfall chart | Category `Account[account_class]`; breakdown `Account[account_name]`; Y axis `Variance Fav/(Adv)` |
| Matrix | Rows `Account[account_class]` then `Account[account_label]`; values `Actual (P&L)`, `Budget (P&L)`, `Variance Fav/(Adv)`, `Variance %` |
| Clustered column chart | Axis `Account[product_line]` (exclude "Not applicable"); values `Gross Margin %`, `Gross Margin % PY` |
| Slicer | `CostCentre[cost_centre_name]` |

Add a page-level filter `Account[statement]` = Profit & Loss. Apply conditional formatting to `Variance Fav/(Adv)` so negative values are red. The matrix grand total for the variance equals `PAT Var`.

### Page 3: Balance sheet and working capital

| Visual | Fields |
|---|---|
| Cards | `Bank Balance`, `Net Working Capital`, `DSO`, `DIO`, `Borrowings`, `Balance Sheet Check` |
| Matrix | Rows `Account[account_class]` then `Account[account_label]`; columns `Date[fiscal_year]`; value `Balance (Display)` (page filter `Account[statement]` = Balance Sheet on this visual only) |
| Line chart | Axis `Date[month_label]`; values `DSO`, `DIO` (no fiscal year filter on this visual; exclude Apr and May 2024) |
| Stacked column chart | Axis `ARInvoice[ageing_bucket]`; value `Open AR` |
| Table | `Customer[customer_name]`, `Open AR`, `Overdue AR over 90 Days`, sorted by the last column |
| Card | `AR Reconciliation Difference` |

### Page 4: Journal entry testing

No fiscal year slicer on this page; use a `Date[fiscal_quarter]` and `Date[fiscal_year]` slicer pair if you want one.

| Visual | Fields |
|---|---|
| Cards | `Manual Journals`, `Manual % of Journals`, `Flagged Journals`, `Flagged Value`, `Journals with 2+ Flags`, `Duplicate Payment Exposure` |
| Bar chart | Axis `JournalFlags[test_name]`; value `Flagged Journals`; tooltip `Flagged Value` |
| Column chart | Axis `Date[month_label]`; value `Flagged Journals`; legend `JournalFlags[risk_area]` |
| Bar chart | Axis `User[user_name]`; value `Flagged Journals` |
| Table | `Journal[journal_id]`, `posting_date`, `created_at`, `description`, `journal_amount`, `prepared_by`, `approved_by`, `flag_count`; visual filter `Flagged Journals` is greater than 0 |

Clicking a test in the first bar chart filters the detail table to the journals that failed it.

### Page 5: Journal drill-through

Create a page with `Journal[journal_id]` in the **Drill through** well. Add a table of `Account[account_label]`, `CostCentre[cost_centre_name]`, `GL[debit]` and `GL[credit]`, and a multi-row card with the header fields. Right-clicking a journal on page 4 then opens its full double entry.

## 6. Final checks

- Every figure in [validation/expected_results.md](validation/expected_results.md) that appears on a page matches.
- `Balance Sheet Check` shows zero.
- `Flagged Journals` shows 75 and the T-test bar chart matches the counts in section 5 of the expected results.
- Each page has a title, a period label, and no default visual titles such as "Sum of amount by month".

## 7. Share it

A personal Gmail address cannot sign in to the Power BI service, so share the work as files:

1. Save the report as `GL_Analytics.pbix` in the `powerbi` folder.
2. Export each page (**File > Export > Export to PDF**) and save screenshots into a `screenshots` folder.
3. Record a three-minute walkthrough of the report with your own narration.
4. Push the folder to a public GitHub repository and link it from your resume and LinkedIn profile.
