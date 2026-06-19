
from io import BytesIO
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import database as db

SHEETS=["Project_Budget_Master","Daily_Worklog","Weekly_Summary_Input","Weekly_Report_Log","Project_Hour_Summary","Staff_Weekly_Summary","Missing_Weekly_Summary","Dashboard_Source","Master_Lists","User_Master","Role_Permission","Audit_Log"]

def scope_raw(table,u):
    raw=db.table(table)
    if not u or u["Role"]=="Admin": return raw
    if table=="project_budget_master": return db.scope_project(raw,u)
    if table=="daily_worklog": return db.scope_weekly(raw,u)
    if table=="weekly_report_log": return db.scope_weekly(raw,u)
    if table=="weekly_summary_input":
        if u["Role"]=="Staff": return raw[raw["Staff_Name"]==u["Staff_Name"]]
        if u["Role"]=="PD/PM": return raw[raw["Cost_Tracking_ID"].isin(db.owned_cost_ids(u["Staff_Name"]))]
        if u["Role"]=="Manager":
            ss=db.staff(); names=ss[ss["Department"]==u["Department"]]["Staff_Name"].tolist()
            return raw[raw["Staff_Name"].isin(names)]
        return raw.iloc[0:0]
    if table in ["user_master","role_permission","audit_log","master_lists"]: return raw.iloc[0:0]
    return raw

def frames(u=None):
    db.rebuild_weekly()
    return {
        "Project_Budget_Master": scope_raw("project_budget_master",u),
        "Daily_Worklog": scope_raw("daily_worklog",u),
        "Weekly_Summary_Input": scope_raw("weekly_summary_input",u),
        "Weekly_Report_Log": scope_raw("weekly_report_log",u),
        "Project_Hour_Summary": db.project_summary(u=u),
        "Staff_Weekly_Summary": db.staff_weekly_summary(u=u),
        "Missing_Weekly_Summary": db.missing_summary(u=u),
        "Dashboard_Source": db.project_summary(u=u),
        "Master_Lists": db.table("master_lists") if u and u["Role"]=="Admin" else pd.DataFrame(),
        "User_Master": db.table("user_master") if u and u["Role"]=="Admin" else pd.DataFrame(),
        "Role_Permission": db.table("role_permission") if u and u["Role"]=="Admin" else pd.DataFrame(),
        "Audit_Log": db.table("audit_log") if u and u["Role"]=="Admin" else pd.DataFrame(),
    }

def write_df(ws,df):
    hf=PatternFill("solid",fgColor="D9EAF7"); font=Font(bold=True)
    thin=Side(style="thin",color="DDDDDD"); border=Border(left=thin,right=thin,top=thin,bottom=thin)
    if df is None or df.empty:
        ws.append(["No Data"]); ws["A1"].font=font; return
    ws.append(list(df.columns))
    for cell in ws[1]:
        cell.font=font; cell.fill=hf; cell.alignment=Alignment(horizontal="center"); cell.border=border
    for _,r in df.iterrows(): ws.append([r[c] for c in df.columns])
    ws.freeze_panes="A2"; ws.auto_filter.ref=ws.dimensions
    percent={"Budget_Burn_Rate","Sales_Estimate_Burn_Rate"}
    for i,col in enumerate(df.columns,1):
        letter=get_column_letter(i)
        if col in percent:
            for rr in range(2,ws.max_row+1): ws[f"{letter}{rr}"].number_format="0.0%"
        elif any(k in str(col) for k in ["Hours","Rate","Count","Budget","Estimated","Remaining"]):
            for rr in range(2,ws.max_row+1): ws[f"{letter}{rr}"].number_format="0.0"
        m=len(str(col))
        for rr in range(2,min(ws.max_row,200)+1):
            v=ws[f"{letter}{rr}"].value
            if v is not None: m=max(m,min(len(str(v)),60))
        ws.column_dimensions[letter].width=max(12,min(m+2,65))
    for row in ws.iter_rows(min_row=2,max_row=ws.max_row):
        for cell in row:
            cell.border=border; cell.alignment=Alignment(vertical="top",wrap_text=True)

def export_full_workbook(u=None):
    fs=frames(u); wb=Workbook(); wb.remove(wb.active)
    for s in SHEETS:
        ws=wb.create_sheet(s); write_df(ws,fs.get(s,pd.DataFrame()))
    out=BytesIO(); wb.save(out); out.seek(0)
    suffix=(u["Role"].replace("/","_") if u else "ALL")
    return f"GLOBAL_Weekly_Report_Demo_v2_{suffix}_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", out.getvalue()

def export_query_result(df):
    wb=Workbook(); ws=wb.active; ws.title="Query_Result"; write_df(ws,df)
    out=BytesIO(); wb.save(out); out.seek(0)
    return f"GLOBAL_Weekly_Report_Query_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx", out.getvalue()
