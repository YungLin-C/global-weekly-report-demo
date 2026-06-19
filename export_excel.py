from io import BytesIO
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import database as db


SHEET_ORDER = [
    "Project_Budget_Master",
    "Daily_Worklog",
    "Weekly_Summary_Input",
    "Weekly_Report_Log",
    "Project_Hour_Summary",
    "Staff_Weekly_Summary",
    "Missing_Weekly_Summary",
    "Dashboard_Source",
    "Master_Lists",
]


def get_export_frames():
    db.rebuild_all_weekly_report_log()
    frames = {
        "Project_Budget_Master": db.get_table("project_budget_master"),
        "Daily_Worklog": db.get_table("daily_worklog"),
        "Weekly_Summary_Input": db.get_table("weekly_summary_input"),
        "Weekly_Report_Log": db.get_table("weekly_report_log"),
        "Project_Hour_Summary": db.get_project_hour_summary(),
        "Staff_Weekly_Summary": db.get_staff_weekly_summary(),
        "Missing_Weekly_Summary": db.get_missing_weekly_summary(),
        "Dashboard_Source": db.get_dashboard_source(),
        "Master_Lists": db.get_table("master_lists"),
    }
    return frames


def _write_dataframe(ws, df: pd.DataFrame):
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    header_font = Font(bold=True)
    thin = Side(style="thin", color="DDDDDD")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    if df is None or df.empty:
        ws.append(["No Data"])
        ws["A1"].font = header_font
        return

    ws.append(list(df.columns))
    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    for _, row in df.iterrows():
        ws.append([row[col] for col in df.columns])

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    percent_cols = {"Budget_Burn_Rate", "Sales_Estimate_Burn_Rate"}
    numeric_keywords = ["Hours", "Rate", "Count", "Budget", "Estimated", "Remaining"]

    for col_idx, column_name in enumerate(df.columns, start=1):
        col_letter = get_column_letter(col_idx)

        if column_name in percent_cols:
            for row_idx in range(2, ws.max_row + 1):
                ws[f"{col_letter}{row_idx}"].number_format = "0.0%"
        elif any(k in str(column_name) for k in numeric_keywords):
            for row_idx in range(2, ws.max_row + 1):
                ws[f"{col_letter}{row_idx}"].number_format = "0.0"

        max_len = len(str(column_name))
        for row_idx in range(2, min(ws.max_row, 200) + 1):
            value = ws[f"{col_letter}{row_idx}"].value
            if value is not None:
                max_len = max(max_len, min(len(str(value)), 60))
        ws.column_dimensions[col_letter].width = max(12, min(max_len + 2, 65))

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def export_full_workbook():
    frames = get_export_frames()
    wb = Workbook()
    default = wb.active
    wb.remove(default)

    for sheet_name in SHEET_ORDER:
        ws = wb.create_sheet(sheet_name)
        _write_dataframe(ws, frames.get(sheet_name, pd.DataFrame()))

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"GLOBAL_Weekly_Report_Demo_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return filename, output.getvalue()


def export_query_result(df: pd.DataFrame):
    wb = Workbook()
    ws = wb.active
    ws.title = "Query_Result"
    _write_dataframe(ws, df)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    filename = f"GLOBAL_Weekly_Report_Query_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return filename, output.getvalue()
