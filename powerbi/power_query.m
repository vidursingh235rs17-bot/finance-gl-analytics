// Power Query (M) for the GL analytics report.
//
// How to use: in Power BI Desktop choose Home > Transform data. For each block
// below create a Blank Query (Home > New Source > Blank Query), open Advanced
// Editor, paste the block, and rename the query to the name in the heading.
// Create the DataFolder parameter first.

// ===================================================================
// Parameter: DataFolder   (Manage Parameters > New, type Text)
// Value: the full path of the data folder, for example
//   C:\Users\Sammu\Documents\finance-gl-analytics\data
// ===================================================================


// ===================================================================
// Query: Date
// ===================================================================
let
    Source = Csv.Document(File.Contents(DataFolder & "\dim_date.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"date", type date}, {"year", Int64.Type}, {"month_no", Int64.Type}, {"month_name", type text},
        {"month_start", type date}, {"month_label", type text}, {"month_sort", Int64.Type},
        {"fiscal_year", type text}, {"fiscal_month_no", Int64.Type}, {"fiscal_quarter", type text},
        {"day_name", type text}, {"is_weekend", type logical}}, "en-US")
in
    Typed


// ===================================================================
// Query: Account
// ===================================================================
let
    Source = Csv.Document(File.Contents(DataFolder & "\dim_account.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"account_id", Int64.Type}, {"account_name", type text}, {"account_class", type text},
        {"account_subclass", type text}, {"statement", type text}, {"class_sort", Int64.Type},
        {"product_line", type text}}, "en-US"),
    Labelled = Table.AddColumn(Typed, "account_label", each Text.From([account_id]) & " " & [account_name], type text)
in
    Labelled


// ===================================================================
// Query: CostCentre
// ===================================================================
let
    Source = Csv.Document(File.Contents(DataFolder & "\dim_cost_centre.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"cost_centre_id", type text}, {"cost_centre_name", type text}, {"function", type text}})
in
    Typed


// ===================================================================
// Query: User
// ===================================================================
let
    Source = Csv.Document(File.Contents(DataFolder & "\dim_user.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"user_id", type text}, {"user_name", type text}, {"role", type text}})
in
    Typed


// ===================================================================
// Query: Customer
// ===================================================================
let
    Source = Csv.Document(File.Contents(DataFolder & "\dim_customer.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"customer_id", type text}, {"customer_name", type text}, {"region", type text},
        {"segment", type text}, {"credit_terms_days", Int64.Type}}, "en-US")
in
    Typed


// ===================================================================
// Query: Vendor
// ===================================================================
let
    Source = Csv.Document(File.Contents(DataFolder & "\dim_vendor.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {{"vendor_id", type text}, {"vendor_name", type text}, {"vendor_category", type text}})
in
    Typed


// ===================================================================
// Query: GL   (journal lines; amount is debit positive, credit negative)
// ===================================================================
let
    Source = Csv.Document(File.Contents(DataFolder & "\journal_lines.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"journal_id", type text}, {"line_no", Int64.Type}, {"account_id", Int64.Type}, {"cost_centre_id", type text},
        {"debit", type number}, {"credit", type number}, {"amount", type number}}, "en-US")
in
    Typed


// ===================================================================
// Query: Budget   (amounts in natural sign: revenue and costs both positive)
// ===================================================================
let
    Source = Csv.Document(File.Contents(DataFolder & "\budget.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"month_start", type date}, {"account_id", Int64.Type}, {"cost_centre_id", type text},
        {"budget_amount", type number}}, "en-US")
in
    Typed


// ===================================================================
// Query: ARInvoice   (receivables sub-ledger, aged as at 31 Mar 2026)
// ===================================================================
let
    AsAt = #date(2026, 3, 31),
    Source = Csv.Document(File.Contents(DataFolder & "\ar_invoices.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"invoice_no", type text}, {"journal_id", type text}, {"customer_id", type text}, {"invoice_date", type date},
        {"due_date", type date}, {"product_line", type text}, {"net_amount", type number}, {"gst_amount", type number},
        {"gross_amount", type number}, {"paid_date", type date}, {"status", type text}}, "en-US"),
    DaysOverdue = Table.AddColumn(Typed, "days_overdue",
        each if [status] = "Open" then Duration.Days(AsAt - [due_date]) else null, Int64.Type),
    Bucket = Table.AddColumn(DaysOverdue, "ageing_bucket", each
        if [days_overdue] = null then null
        else if [days_overdue] <= 0 then "Not due"
        else if [days_overdue] <= 30 then "1-30"
        else if [days_overdue] <= 60 then "31-60"
        else if [days_overdue] <= 90 then "61-90"
        else if [days_overdue] <= 180 then "91-180"
        else "Over 180", type text),
    BucketSort = Table.AddColumn(Bucket, "ageing_sort", each
        if [days_overdue] = null then null
        else if [days_overdue] <= 0 then 1
        else if [days_overdue] <= 30 then 2
        else if [days_overdue] <= 60 then 3
        else if [days_overdue] <= 90 then 4
        else if [days_overdue] <= 180 then 5
        else 6, Int64.Type),
    DaysToPay = Table.AddColumn(BucketSort, "days_to_pay",
        each if [paid_date] = null then null else Duration.Days([paid_date] - [invoice_date]), Int64.Type)
in
    DaysToPay


// ===================================================================
// Query: Journal   (journal headers with the eleven audit tests)
// Depends on: GL
// ===================================================================
let
    ApprovalLimit = 500000,          // manual journals at or above this need the Financial Controller
    ControllerId = "U08",

    Source = Csv.Document(File.Contents(DataFolder & "\journal_header.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Promoted = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed = Table.TransformColumnTypes(Promoted, {
        {"journal_id", type text}, {"posting_date", type date}, {"created_at", type datetime}, {"source", type text},
        {"prepared_by", type text}, {"approved_by", type text}, {"description", type text}, {"party_id", type text},
        {"journal_amount", type number}}, "en-US"),
    Clean = Table.ReplaceValue(Typed, null, "", Replacer.ReplaceValue, {"description", "approved_by", "party_id"}),

    // journals that touch revenue (4000-4999) or the receivables control account (1100)
    RevenueIds = List.Buffer(List.Distinct(Table.SelectRows(GL, each [account_id] >= 4000 and [account_id] < 5000)[journal_id])),
    ReceivableIds = List.Buffer(List.Distinct(Table.SelectRows(GL, each [account_id] = 1100)[journal_id])),

    // payments to the same vendor for the same amount within 7 days of each other
    Payments = Table.SelectColumns(Table.SelectRows(Clean, each [source] = "Payment"),
        {"journal_id", "party_id", "journal_amount", "posting_date"}),
    Other = Table.RenameColumns(Payments, {{"journal_id", "o_id"}, {"party_id", "o_party"},
        {"journal_amount", "o_amount"}, {"posting_date", "o_date"}}),
    Pairs = Table.Join(Payments, {"party_id", "journal_amount"}, Other, {"o_party", "o_amount"}, JoinKind.Inner),
    Close = Table.SelectRows(Pairs, each [journal_id] <> [o_id]
        and Number.Abs(Duration.Days([posting_date] - [o_date])) <= 7),
    DuplicateIds = List.Buffer(List.Distinct(Close[journal_id])),

    T1 = Table.AddColumn(Clean, "T1", each [source] = "Manual"
        and Date.DayOfWeek([created_at], Day.Monday) >= 5, type logical),
    T2 = Table.AddColumn(T1, "T2", each [source] = "Manual"
        and (Time.Hour([created_at]) >= 21 or Time.Hour([created_at]) < 6), type logical),
    T3 = Table.AddColumn(T2, "T3", each [source] = "Manual"
        and [journal_amount] >= 100000 and Number.Mod([journal_amount], 100000) = 0, type logical),
    T4 = Table.AddColumn(T3, "T4", each [source] = "Manual"
        and [journal_amount] >= 0.9 * ApprovalLimit and [journal_amount] < ApprovalLimit, type logical),
    T5 = Table.AddColumn(T4, "T5", each [source] = "Manual"
        and [prepared_by] = [approved_by], type logical),
    T6 = Table.AddColumn(T5, "T6", each [source] = "Manual"
        and Text.Length(Text.Trim([description])) < 6, type logical),
    T7 = Table.AddColumn(T6, "T7", each [source] = "Manual"
        and Duration.Days(Date.From([created_at]) - [posting_date]) > 10, type logical),
    T8 = Table.AddColumn(T7, "T8", each [source] = "Manual"
        and [journal_amount] >= ApprovalLimit and [approved_by] <> ControllerId, type logical),
    T9 = Table.AddColumn(T8, "T9", each [source] = "Manual"
        and List.Contains(RevenueIds, [journal_id]), type logical),
    T10 = Table.AddColumn(T9, "T10", each [source] = "Manual"
        and List.Contains(ReceivableIds, [journal_id]), type logical),
    T11 = Table.AddColumn(T10, "T11", each [source] = "Payment"
        and List.Contains(DuplicateIds, [journal_id]), type logical),

    FlagCount = Table.AddColumn(T11, "flag_count", each List.Count(List.Select(
        {[T1], [T2], [T3], [T4], [T5], [T6], [T7], [T8], [T9], [T10], [T11]}, each _ = true)), Int64.Type),
    IsFlagged = Table.AddColumn(FlagCount, "is_flagged", each [flag_count] > 0, type logical),
    EntryLag = Table.AddColumn(IsFlagged, "entry_lag_days",
        each Duration.Days(Date.From([created_at]) - [posting_date]), Int64.Type)
in
    EntryLag


// ===================================================================
// Query: JournalFlags   (one row per journal per test failed)
// Depends on: Journal
// ===================================================================
let
    Source = Table.SelectColumns(Table.SelectRows(Journal, each [is_flagged]),
        {"journal_id", "journal_amount", "T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "T9", "T10", "T11"}),
    Unpivoted = Table.UnpivotOtherColumns(Source, {"journal_id", "journal_amount"}, "test_code", "failed"),
    Failed = Table.RemoveColumns(Table.SelectRows(Unpivoted, each [failed] = true), {"failed"}),
    Names = #table(type table [test_code = text, test_name = text, test_sort = Int64.Type, risk_area = text], {
        {"T1", "T1 Entered on a weekend", 1, "Timing"},
        {"T2", "T2 Entered after hours", 2, "Timing"},
        {"T3", "T3 Round amount", 3, "Amount"},
        {"T4", "T4 Just below approval limit", 4, "Authorisation"},
        {"T5", "T5 Prepared and approved by same user", 5, "Authorisation"},
        {"T6", "T6 Missing or weak description", 6, "Documentation"},
        {"T7", "T7 Backdated more than 10 days", 7, "Timing"},
        {"T8", "T8 Above limit without controller approval", 8, "Authorisation"},
        {"T9", "T9 Manual journal to revenue", 9, "Revenue"},
        {"T10", "T10 Manual journal to receivables control", 10, "Reconciliation"},
        {"T11", "T11 Possible duplicate vendor payment", 11, "Payments"}}),
    Joined = Table.NestedJoin(Failed, {"test_code"}, Names, {"test_code"}, "n", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Joined, "n", {"test_name", "test_sort", "risk_area"}),
    Typed = Table.TransformColumnTypes(Expanded, {{"journal_amount", type number}, {"test_sort", Int64.Type}})
in
    Typed
