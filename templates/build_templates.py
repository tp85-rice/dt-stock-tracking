from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.formatting.rule import CellIsRule, FormulaRule
from openpyxl.utils import get_column_letter

HDR_FILL = PatternFill("solid", fgColor="1F3864")
HDR_FONT = Font(bold=True, color="FFFFFF")
INPUT_FILL = PatternFill("solid", fgColor="FFF9E5")
CALC_FILL = PatternFill("solid", fgColor="EDEDED")
THIN = Side(style="thin", color="BFBFBF")
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
GREEN = PatternFill("solid", bgColor="C6EFCE", fgColor="C6EFCE")
YELLOW = PatternFill("solid", bgColor="FFEB9C", fgColor="FFEB9C")
RED = PatternFill("solid", bgColor="FFC7CE", fgColor="FFC7CE")
GREY = PatternFill("solid", bgColor="D9D9D9", fgColor="D9D9D9")
BLUE = PatternFill("solid", bgColor="DDEBF7", fgColor="DDEBF7")
ROWS = 500


def make_table(ws, headers, widths, calc_cols=(), rows=ROWS, wrap=True):
    for i, (h, w) in enumerate(zip(headers, widths), start=1):
        c = ws.cell(row=1, column=i, value=h)
        c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BORDER
        c.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[1].height = 32
    for r in range(2, rows + 1):
        for i in range(1, len(headers) + 1):
            c = ws.cell(row=r, column=i)
            c.fill = CALC_FILL if i in calc_cols else INPUT_FILL
            c.border = BORDER
            c.alignment = Alignment(wrap_text=wrap, vertical="top")
    ws.freeze_panes = "A2"


def dropdown(ws, col, items, rows=ROWS):
    dv = DataValidation(type="list", formula1='"' + ",".join(items) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col}2:{col}{rows}")


def color_cf(ws, rng):
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"GREEN"'], fill=GREEN))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"YELLOW"'], fill=YELLOW))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"RED"'], fill=RED))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"GREY"'], fill=GREY))
    ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"PENDING"'], fill=BLUE))


def readme(ws, lines, width=110):
    ws.column_dimensions["A"].width = 26
    ws.column_dimensions["B"].width = width
    r = 1
    for a, b, kind in lines:
        ca, cb = ws.cell(row=r, column=1, value=a), ws.cell(row=r, column=2, value=b)
        cb.alignment = Alignment(wrap_text=True, vertical="top")
        ca.alignment = Alignment(wrap_text=True, vertical="top")
        if kind == "title":
            ca.font = Font(bold=True, size=14)
        elif kind == "head":
            ca.font = cb.font = HDR_FONT
            ca.fill = cb.fill = HDR_FILL
        elif kind == "input":
            cb.fill = INPUT_FILL
            ca.font = Font(bold=True)
            cb.border = BORDER
        else:
            ca.font = Font(bold=True)
        r += 1


# ---------------------------------------------------------------- workbook 1
def build_ticker_template(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    readme(ws, [
        ("Per-ticker driver sheet (template v2)", "", "title"),
        ("Ticker", "", "input"),
        ("Archetype / template", "", "input"),
        ("Owner / last updated", "", "input"),
        ("", "", ""),
        ("Colour key", "", "head"),
        ("Yellow cells", "You type here.", ""),
        ("Grey cells", "Formula. Do not overwrite.", ""),
        ("", "", ""),
        ("Order of work", "", "head"),
        ("1. Drivers", "One row per driver (D1, D2, ...). Give each a unique Driver ID. Target 3-6 drivers. Columns N-P: driver type (Core / Option / Mechanism / Event), rough share of today's price it carries (0-1), and the Driver IDs it depends on (a Mechanism caps the drivers that sit on it).", ""),
        ("2. Signals", "One row per signal (S1, S2, ...), linked to a Driver ID. Max 5 per driver. At least one must be Tier A or B, otherwise the driver shows 'narrative-only'. Set polarity, tolerance band and max staleness here: these are the scoring rules. Columns N-P: mark the one binding-constraint signal per driver (Y), any kill-switch signal (Y), and the anchor that justifies the base case and tolerance (guidance, a competitor's disclosed figure, the stock's own history).", ""),
        ("3. Base case", "Quantified path per numeric signal and period, with a version label (v1, v2, ...) and snapshot date. Consensus rows are what colours are scored against. Management and Thesis rows are reference lines only (Thesis = our own base case from the thesis work). Never overwrite old versions: add a new version after each earnings call.", ""),
        ("4. Event ladder", "For milestone signals (launches, approvals, bill passage, contract awards). List the steps in order with a target date each; update status as they happen. Column K says what kind of step it is: Milestone, Catalyst, Falsification test, Thesis breaker or Disclosure.", ""),
        ("5. Source log", "Every source used: URL, access method, cost, ToS / redistribution note. Give each a Source ID (R1, R2, ...).", ""),
        ("6. Scoring log", "WHERE YOU SCORE. Add one row per observation of a numeric signal: date, Signal ID, observed value, base case version, period. Everything else fills in. You only choose the arrow and add a source ID.", ""),
        ("", "", ""),
        ("How colour is decided (Scoring log)", "", "head"),
        ("Variance %", "(Observed - Base case) / |Base case|", ""),
        ("Higher is better", "GREEN if variance >= 0. YELLOW if within the tolerance band below base. RED if worse than tolerance.", ""),
        ("Lower is better", "GREEN if variance <= 0. YELLOW if within the tolerance band above base. RED if worse than tolerance.", ""),
        ("RED (Withheld)", "Value missing AND column P = Y: the company skipped a natural chance to disclose it (an earnings call, a launch). A withheld metric is a signal, so it scores RED. The first time a metric is simply not available, leave P blank: it shows GREY.", ""),
        ("GREY", "Value missing (not marked withheld), observation older than the signal's Max staleness (days), or no matching base case row. 'Data status' says which. Grey never means 'in line'.", ""),
        ("Arrow", "Your judgement of momentum from the last 2-3 observations: Accelerating / Flat / Decelerating / n/a. It is separate from colour.", ""),
        ("Green means", "Ahead of the base case, not 'the stock goes up'. If consensus is already optimistic, in line is already priced in.", ""),
        ("", "", ""),
        ("Rules", "", "head"),
        ("Definition changes", "If a company redefines a metric (e.g. a backlog definition), note it in Signals > Definition change. Start a new Signal ID or new base case version at the break. Do not splice the series.", ""),
        ("No advice", "No price targets and no buy/sell wording anywhere in this sheet.", ""),
    ])

    # Drivers
    d = wb.create_sheet("Drivers")
    make_table(d,
        ["Driver ID", "Driver", "Thesis (1-2 sentences)", "Valuation mechanism", "Horizon (years)", "Impact", "Direction", "Evidence / citation (Source ID or page)", "Confidence", "# Signals", "# Tier A/B signals", "Driver status", "Notes", "Driver type", "Share of price (0-1)", "Depends on (Driver IDs)"],
        [10, 26, 48, 32, 12, 9, 14, 32, 12, 10, 12, 18, 30, 14, 12, 16], calc_cols=(10, 11, 12))
    dropdown(d, "E", ["1", "2", "3", "4", "5"])
    dropdown(d, "F", ["H", "M", "L"])
    dropdown(d, "G", ["Upside", "Downside", "Both"])
    dropdown(d, "I", ["High", "Medium", "Low"])
    dropdown(d, "N", ["Core", "Option", "Mechanism", "Event"])
    for r in range(2, ROWS + 1):
        d[f"J{r}"] = f'=IF(A{r}="","",COUNTIF(Signals!$B$2:$B${ROWS},A{r}))'
        d[f"K{r}"] = f'=IF(A{r}="","",COUNTIFS(Signals!$B$2:$B${ROWS},A{r},Signals!$E$2:$E${ROWS},"A")+COUNTIFS(Signals!$B$2:$B${ROWS},A{r},Signals!$E$2:$E${ROWS},"B"))'
        d[f"L{r}"] = f'=IF(A{r}="","",IF(J{r}=0,"no signals",IF(K{r}=0,"narrative-only",IF(J{r}>5,"over cap (5)","OK"))))'
        d[f"O{r}"].number_format = "0%"

    # Signals
    s = wb.create_sheet("Signals")
    make_table(s,
        ["Signal ID", "Driver ID", "Signal", "Source (name / Source ID)", "Tier (A/B/C)", "Cadence", "Unit", "Polarity (for this driver)", "Tolerance band (e.g. 0.10 = 10%)", "Max staleness (days)", "Reliability (1-5)", "Definition change (date / note)", "Notes", "Binding constraint (Y/N)", "Kill switch (Y/N)", "Threshold anchor (why this base case / tolerance)"],
        [10, 10, 34, 28, 10, 12, 12, 18, 16, 14, 12, 30, 30, 12, 11, 40])
    dropdown(s, "E", ["A", "B", "C"])
    dropdown(s, "F", ["Daily", "Weekly", "Monthly", "Quarterly", "Event"])
    dropdown(s, "H", ["Higher is better", "Lower is better", "Event ladder"])
    dropdown(s, "K", ["1", "2", "3", "4", "5"])
    dropdown(s, "N", ["Y", "N"])
    dropdown(s, "O", ["Y", "N"])
    for r in range(2, ROWS + 1):
        s[f"I{r}"].number_format = "0%"

    # Base case
    b = wb.create_sheet("Base case")
    make_table(b,
        ["Version (v1, v2, ...)", "Snapshot date", "Case type", "Signal ID", "Period (e.g. Q4 FY26)", "Value", "Unit", "Source ID", "Basis / notes"],
        [14, 14, 16, 12, 18, 14, 12, 12, 40])
    dropdown(b, "C", ["Consensus", "Management", "Thesis"])
    for r in range(2, ROWS + 1):
        b[f"B{r}"].number_format = "yyyy-mm-dd"

    # Event ladder
    e = wb.create_sheet("Event ladder")
    make_table(e,
        ["Signal ID", "Step #", "Milestone", "Base case target date", "Status", "Actual date", "Days late", "Colour", "Source ID", "Notes", "Kind"],
        [11, 8, 40, 16, 14, 14, 11, 12, 11, 36, 18], calc_cols=(7, 8))
    dropdown(e, "E", ["Pending", "Occurred", "Slipped", "Failed"])
    dropdown(e, "K", ["Milestone", "Catalyst", "Falsification test", "Thesis breaker", "Disclosure"])
    for r in range(2, ROWS + 1):
        e[f"D{r}"].number_format = "yyyy-mm-dd"
        e[f"F{r}"].number_format = "yyyy-mm-dd"
        e[f"G{r}"] = f'=IF(AND(ISNUMBER(F{r}),ISNUMBER(D{r})),F{r}-D{r},"")'
        e[f"H{r}"] = (f'=IF(A{r}="","",IF(OR(E{r}="Failed",E{r}="Slipped"),"RED",'
                      f'IF(E{r}="Occurred",IF(N(G{r})<=0,"GREEN","YELLOW"),'
                      f'IF(AND(ISNUMBER(D{r}),TODAY()>D{r}),"YELLOW","PENDING"))))')
    color_cf(e, f"H2:H{ROWS}")

    # Source log
    sl = wb.create_sheet("Source log")
    make_table(sl,
        ["Source ID", "Date accessed", "Source name", "URL", "Tier (A/B/C)", "Access method", "Cost", "ToS / licensing note", "Redistribute on site?", "Used for (Signal IDs)", "Reliability note"],
        [10, 14, 28, 44, 10, 16, 12, 40, 14, 20, 30])
    dropdown(sl, "E", ["A", "B", "C"])
    dropdown(sl, "F", ["API", "Download", "Scrape", "Manual", "Vendor"])
    dropdown(sl, "G", ["Free", "Paid", "Unknown"])
    dropdown(sl, "I", ["Yes", "No", "Unknown"])
    for r in range(2, ROWS + 1):
        sl[f"B{r}"].number_format = "yyyy-mm-dd"

    # Scoring log
    sc = wb.create_sheet("Scoring log")
    make_table(sc,
        ["Date observed", "Signal ID", "Observed value", "Base case version", "Period", "Base case value", "Variance %", "Polarity", "Tolerance", "Max staleness (days)", "Data status", "Colour", "Arrow (momentum)", "Source ID", "Notes", "Withheld? (Y = company skipped a natural chance to disclose)"],
        [14, 11, 15, 14, 16, 15, 12, 17, 11, 13, 12, 12, 18, 11, 36, 16], calc_cols=(6, 7, 8, 9, 10, 11, 12))
    dropdown(sc, "M", ["Accelerating", "Flat", "Decelerating", "n/a"])
    dropdown(sc, "P", ["Y", "N"])
    SIG = f"Signals!$A$2:$A${ROWS}"
    for r in range(2, ROWS + 1):
        sc[f"A{r}"].number_format = "yyyy-mm-dd"
        sc[f"G{r}"].number_format = "0.0%"
        sc[f"I{r}"].number_format = "0%"
        crit = (f"'Base case'!$D$2:$D${ROWS},B{r},'Base case'!$A$2:$A${ROWS},D{r},"
                f"'Base case'!$E$2:$E${ROWS},E{r},'Base case'!$C$2:$C${ROWS},\"Consensus\"")
        sc[f"F{r}"] = f'=IF(B{r}="","",IF(COUNTIFS({crit})=0,"",SUMIFS(\'Base case\'!$F$2:$F${ROWS},{crit})))'
        sc[f"G{r}"] = f'=IF(OR(NOT(ISNUMBER(C{r})),NOT(ISNUMBER(F{r}))),"",IF(F{r}=0,"",(C{r}-F{r})/ABS(F{r})))'
        sc[f"H{r}"] = f'=IF(B{r}="","",IFERROR(INDEX(Signals!$H$2:$H${ROWS},MATCH(B{r},{SIG},0)),""))'
        sc[f"I{r}"] = f'=IF(B{r}="","",IFERROR(IF(INDEX(Signals!$I$2:$I${ROWS},MATCH(B{r},{SIG},0))="","",INDEX(Signals!$I$2:$I${ROWS},MATCH(B{r},{SIG},0))),""))'
        sc[f"J{r}"] = f'=IF(B{r}="","",IFERROR(IF(INDEX(Signals!$J$2:$J${ROWS},MATCH(B{r},{SIG},0))="","",INDEX(Signals!$J$2:$J${ROWS},MATCH(B{r},{SIG},0))),""))'
        sc[f"K{r}"] = (f'=IF(B{r}="","",IF(NOT(ISNUMBER(C{r})),IF(UPPER(P{r})="Y","Withheld","Missing"),'
                       f'IF(AND(ISNUMBER(J{r}),ISNUMBER(A{r}),TODAY()-A{r}>J{r}),"Stale",'
                       f'IF(NOT(ISNUMBER(F{r})),"No base case","OK"))))')
        sc[f"L{r}"] = (f'=IF(B{r}="","",IF(K{r}="Withheld","RED",IF(K{r}<>"OK","GREY",IF(NOT(ISNUMBER(G{r})),"GREY",'
                       f'IF(H{r}="Higher is better",IF(G{r}>=0,"GREEN",IF(G{r}>=-N(I{r}),"YELLOW","RED")),'
                       f'IF(H{r}="Lower is better",IF(G{r}<=0,"GREEN",IF(G{r}<=N(I{r}),"YELLOW","RED")),"GREY"))))))')
    color_cf(sc, f"L2:L{ROWS}")
    sc.conditional_formatting.add(f"K2:K{ROWS}", FormulaRule(formula=['AND(K2<>"",K2<>"OK")'], fill=GREY))

    wb.save(path)


# ---------------------------------------------------------------- workbook 2
def build_eval_template(path):
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    readme(ws, [
        ("LLM extraction scorecard", "", "title"),
        ("Purpose", "Measure how often the LLM layer gets driver, KPI and event extraction right, and whether every claim cites a passage that supports it. Re-run after every prompt or model change.", ""),
        ("", "", ""),
        ("Order of work", "", "head"),
        ("1. Gold set", "Build 20-30 cases by hand BEFORE running the model. One row per case: a real passage from a filing, call or press release, the task, and the correct answer as you read it. Mix tasks and tickers (see 'Coverage' below). Include hard cases: restated numbers, definition changes, negations ('no longer expects'), and passages with no answer.", ""),
        ("2. Runs", "WHERE YOU SCORE. For each prompt/model version, add one row per Gold case: paste the model output, the passage it cited, and score each check 1 or 0.", ""),
        ("3. Summary", "Reads from Runs automatically. Type your prompt version labels in column A, set pass targets, and read PASS / FAIL.", ""),
        ("", "", ""),
        ("How to score (Runs)", "", "head"),
        ("Value correct", "1 if the extracted value, unit, period and entity all match the gold label. 0 otherwise. Wrong period or unit is a 0.", ""),
        ("Event / type correct", "1 if the event type or driver label matches gold (e.g. 'guidance raise', 'milestone slipped'). Use n/a (leave blank) if the task has no type.", ""),
        ("Citation valid", "1 only if the cited passage, read by itself, supports the claim. A real passage that does not support the claim is a 0.", ""),
        ("Hallucination", "1 if the output states something not in the source (invented number, entity, date, or a claim with no support). Otherwise 0. Note this is bad when 1.", ""),
        ("Schema valid", "1 if the output parsed against the JSON schema without repair.", ""),
        ("Should-abstain cases", "If the gold answer is 'not in passage', the model is correct only if it returns nothing or flags low confidence. Inventing a value counts as a hallucination.", ""),
        ("", "", ""),
        ("Coverage", "Aim for at least 4 cases per task type, across at least 5 tickers and 3 document types (10-K/10-Q, call transcript, press release). Keep at least 20% of cases as hard cases. Do not edit gold labels after seeing model output. Add new cases instead.", ""),
        ("Contamination note", "Models may have seen older filings in training. Prefer passages dated after the model's knowledge cutoff for any test that claims to measure real extraction skill.", ""),
        ("Reviewer", "Have a second person score about 20% of rows blind. If you disagree on more than 1 in 10, tighten the rubric before trusting the numbers.", ""),
    ])

    tasks = ["Driver extraction", "KPI extraction", "Event extraction", "Q&A theme", "Other"]

    g = wb.create_sheet("Gold set")
    make_table(g,
        ["Case ID", "Ticker", "Doc type", "Doc date", "Source URL / file", "Section / page", "Passage (verbatim excerpt)", "Task", "Gold answer (value / label)", "Unit", "Period", "Entity", "Should abstain? (Y/N)", "Hard case? (Y/N)", "Labeller", "Notes"],
        [9, 8, 16, 12, 34, 16, 60, 18, 28, 10, 12, 18, 12, 11, 12, 30])
    dropdown(g, "C", ["10-K / 10-Q", "20-F / 6-K", "8-K", "Call transcript", "Press release", "Investor deck", "Other"])
    dropdown(g, "H", tasks)
    dropdown(g, "M", ["Y", "N"])
    dropdown(g, "N", ["Y", "N"])
    for r in range(2, ROWS + 1):
        g[f"D{r}"].number_format = "yyyy-mm-dd"

    rn = wb.create_sheet("Runs")
    make_table(rn,
        ["Run ID", "Case ID", "Prompt / model version", "Task (auto)", "Model output (value / label)", "Cited passage (paste)", "Value correct (1/0)", "Event / type correct (1/0)", "Citation valid (1/0)", "Hallucination (1/0)", "Schema valid (1/0)", "Reviewer", "Date scored", "Notes"],
        [9, 9, 20, 18, 30, 40, 11, 13, 11, 13, 11, 12, 13, 30], calc_cols=(4,))
    for col in "GHIJK":
        dropdown(rn, col, ["1", "0"])
    for r in range(2, ROWS + 1):
        rn[f"D{r}"] = f'=IF(B{r}="","",IFERROR(INDEX(\'Gold set\'!$H$2:$H${ROWS},MATCH(B{r},\'Gold set\'!$A$2:$A${ROWS},0)),"case not found"))'
        rn[f"M{r}"].number_format = "yyyy-mm-dd"

    sm = wb.create_sheet("Summary")
    sm.column_dimensions["A"].width = 26
    for c in "BCDEFGHI":
        sm.column_dimensions[c].width = 16
    sm["A1"] = "Pass targets (edit)"
    sm["A1"].font = Font(bold=True, size=12)
    targets = [("Value correct, min", 0.90), ("Citation valid, min", 0.95), ("Hallucination, max", 0.02), ("Schema valid, min", 0.99)]
    for i, (lab, v) in enumerate(targets, start=2):
        sm[f"A{i}"] = lab
        sm[f"B{i}"] = v
        sm[f"B{i}"].number_format = "0%"
        sm[f"B{i}"].fill = INPUT_FILL
        sm[f"B{i}"].border = BORDER

    sm["A8"] = "By prompt / model version"
    sm["A8"].font = Font(bold=True, size=12)
    hdr = ["Version (type label)", "Runs scored", "Value correct", "Event / type correct", "Citation valid", "Hallucination rate", "Schema valid", "Result"]
    for i, h in enumerate(hdr, start=1):
        c = sm.cell(row=9, column=i, value=h)
        c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BORDER
        c.alignment = Alignment(wrap_text=True)
    RN = lambda col: f"Runs!${col}$2:${col}${ROWS}"
    for r in range(10, 20):
        sm[f"A{r}"].fill = INPUT_FILL
        sm[f"A{r}"].border = BORDER
        sm[f"B{r}"] = f'=IF(A{r}="","",COUNTIFS({RN("C")},A{r}))'
        for col, src in zip("CDEFG", "GHIJK"):
            sm[f"{col}{r}"] = f'=IF(OR(A{r}="",COUNTIFS({RN("C")},A{r},{RN(src)},"<>")=0),"",AVERAGEIFS({RN(src)},{RN("C")},A{r}))'
            sm[f"{col}{r}"].number_format = "0.0%"
        sm[f"H{r}"] = (f'=IF(OR(A{r}="",NOT(ISNUMBER(C{r})),NOT(ISNUMBER(E{r})),NOT(ISNUMBER(F{r})),NOT(ISNUMBER(G{r}))),"",'
                       f'IF(AND(C{r}>=$B$2,E{r}>=$B$3,F{r}<=$B$4,G{r}>=$B$5),"PASS","FAIL"))')
        for col in "BCDEFGH":
            sm[f"{col}{r}"].fill = CALC_FILL
            sm[f"{col}{r}"].border = BORDER
    sm.conditional_formatting.add("H10:H19", CellIsRule(operator="equal", formula=['"PASS"'], fill=GREEN))
    sm.conditional_formatting.add("H10:H19", CellIsRule(operator="equal", formula=['"FAIL"'], fill=RED))

    sm["A22"] = "By task type, for the version typed here:"
    sm["A22"].font = Font(bold=True, size=12)
    sm["D22"].fill = INPUT_FILL
    sm["D22"].border = BORDER
    hdr2 = ["Task", "Runs scored", "Value correct", "Event / type correct", "Citation valid", "Hallucination rate", "Schema valid"]
    for i, h in enumerate(hdr2, start=1):
        c = sm.cell(row=23, column=i, value=h)
        c.fill, c.font, c.border = HDR_FILL, HDR_FONT, BORDER
        c.alignment = Alignment(wrap_text=True)
    for i, t in enumerate(tasks):
        r = 24 + i
        sm[f"A{r}"] = t
        sm[f"B{r}"] = f'=IF($D$22="","",COUNTIFS({RN("C")},$D$22,{RN("D")},A{r}))'
        for col, src in zip("CDEFG", "GHIJK"):
            sm[f"{col}{r}"] = (f'=IF(OR($D$22="",COUNTIFS({RN("C")},$D$22,{RN("D")},$A{r},{RN(src)},"<>")=0),"",'
                               f'AVERAGEIFS({RN(src)},{RN("C")},$D$22,{RN("D")},$A{r}))')
            sm[f"{col}{r}"].number_format = "0.0%"
        for col in "ABCDEFG":
            sm[f"{col}{r}"].fill = CALC_FILL
            sm[f"{col}{r}"].border = BORDER

    wb.move_sheet("Summary", offset=-2)
    wb.save(path)


if __name__ == "__main__":
    import sys
    build_ticker_template("stock_driver_template.xlsx")
    if "--driver-only" not in sys.argv:
        build_eval_template("llm_eval_scorecard.xlsx")
    print("ok")
