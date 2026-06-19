import streamlit as st
import pandas as pd
from datetime import date

import database as db
from export_excel import export_full_workbook, export_query_result


st.set_page_config(
    page_title="GLOBAL Weekly Report Demo",
    page_icon="🗓️",
    layout="wide",
)

db.init_db()


def section_title(title, caption=None):
    st.title(title)
    if caption:
        st.caption(caption)


def safe_success(message):
    st.success(message)
    db.rebuild_all_weekly_report_log()


def dataframe(df, height=360):
    st.dataframe(df, use_container_width=True, hide_index=True, height=height)


def get_select_options(base, include_all=False):
    options = list(base)
    if include_all:
        options = ["ALL"] + options
    return options


def page_budget_setting():
    section_title("預算設定", "新增與編輯 project_budget_master。Cost_Tracking_ID 不可重複；若已存在，會更新原資料。")

    product_lines = db.get_master_values("Product_Line")
    platform_lines = db.get_master_values("Platform_Line")
    status_list = db.get_master_values("Status")
    staff_names = db.get_staff()["Staff_Name"].tolist()

    with st.form("budget_form", clear_on_submit=False):
        st.subheader("新增 / 編輯預算資料")

        col1, col2, col3 = st.columns(3)
        with col1:
            opportunity_id = st.text_input("Opportunity_ID", value="OPP-2026-NEW")
            cost_id = st.text_input("Cost_Tracking_ID / 工番號・依賴號", value="")
            customer = st.text_input("Customer", value="")
        with col2:
            project_name = st.text_input("Project_Name", value="")
            product_line = st.selectbox("Product_Line", product_lines)
            platform_line = st.selectbox("Platform_Line", platform_lines)
        with col3:
            budget_hours = st.number_input("Budget_Hours", min_value=0.0, value=100.0, step=10.0)
            sales_est_hours = st.number_input("Sales_Estimated_Hours", min_value=0.0, value=100.0, step=10.0)
            owner = st.selectbox("Owner", staff_names)
            status = st.selectbox("Status", status_list, index=status_list.index("Active") if "Active" in status_list else 0)

        submitted = st.form_submit_button("儲存預算資料", type="primary")

        if submitted:
            try:
                db.upsert_project_budget({
                    "Opportunity_ID": opportunity_id.strip(),
                    "Cost_Tracking_ID": cost_id.strip(),
                    "Customer": customer.strip(),
                    "Project_Name": project_name.strip(),
                    "Product_Line": product_line,
                    "Platform_Line": platform_line,
                    "Budget_Hours": budget_hours,
                    "Sales_Estimated_Hours": sales_est_hours,
                    "Owner": owner,
                    "Status": status,
                })
                safe_success("預算資料已儲存。")
            except Exception as e:
                st.error(str(e))

    st.subheader("目前 Project_Budget_Master")
    dataframe(db.get_table("project_budget_master"))


def page_daily_worklog():
    section_title("日報輸入", "單筆輸入每日工時。一筆日報只對應一個 Cost_Tracking_ID。")

    staff_df = db.get_staff()
    staff_names = staff_df["Staff_Name"].tolist()
    cost_ids = db.get_active_cost_ids()
    work_categories = db.get_master_values("Work_Category")

    with st.form("daily_worklog_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            work_date = st.date_input("Work_Date / 作業日期", value=date.today())
            staff_name = st.selectbox("Staff_Name / 人員", staff_names)
        with col2:
            cost_id = st.selectbox("Cost_Tracking_ID / 工番號・依賴號", cost_ids)
            work_category = st.selectbox("Work_Category / 工作分類", work_categories)
        with col3:
            hours = st.number_input("Hours / 工時", min_value=0.5, max_value=24.0, value=1.0, step=0.5)
            work_content = st.text_input("Work_Content / 簡短內容", max_chars=100)

        submitted = st.form_submit_button("儲存日報", type="primary")

        if submitted:
            try:
                worklog_id = db.add_daily_worklog(
                    work_date=work_date,
                    staff_name=staff_name,
                    cost_tracking_id=cost_id,
                    work_category=work_category,
                    hours=hours,
                    work_content=work_content,
                )
                safe_success(f"日報已儲存：{worklog_id}")
            except Exception as e:
                st.error(str(e))

    st.subheader("最近 20 筆日報紀錄")
    recent = db.query_df("""
        SELECT Worklog_ID, Work_Date, Report_Week, Staff_Name, Department,
               Cost_Tracking_ID, Work_Category, Hours, Work_Content, Created_At
        FROM daily_worklog
        ORDER BY Created_At DESC
        LIMIT 20
    """)
    dataframe(recent)


def page_weekly_summary():
    section_title("週報輸入", "每週每人針對有投入工時的 Cost_Tracking_ID 填寫本週總結與下週目標。")

    week_options = db.get_week_options()
    staff_names = db.get_staff()["Staff_Name"].tolist()
    health_list = db.get_master_values("Health")

    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        report_week = st.selectbox("Report_Week / 週次", week_options)
    with col_filter2:
        staff_name = st.selectbox("Staff_Name / 人員", staff_names)

    cost_ids = db.get_cost_ids_for_staff_week(staff_name, report_week)

    with st.form("weekly_summary_form", clear_on_submit=False):
        cost_id = st.selectbox("Cost_Tracking_ID / 工番號・依賴號", cost_ids)
        weekly_summary = st.text_area("Weekly_Summary / 本週總結（500 字以內）", height=130, max_chars=500)
        next_week_target = st.text_area("Next_Week_Target / 下週目標（500 字以內）", height=130, max_chars=500)
        health = st.selectbox("Health / 狀態", health_list)

        submitted = st.form_submit_button("儲存週報", type="primary")

        if submitted:
            try:
                weekly_input_id = db.upsert_weekly_summary(
                    report_week=report_week,
                    staff_name=staff_name,
                    cost_tracking_id=cost_id,
                    weekly_summary=weekly_summary,
                    next_week_target=next_week_target,
                    health=health,
                )
                safe_success(f"週報已儲存 / 更新：{weekly_input_id}")
            except Exception as e:
                st.error(str(e))

    st.subheader("目前選定條件的週報 Log")
    selected = db.get_weekly_report_filtered(
        start_week=report_week,
        end_week=report_week,
        staff_name=staff_name,
        cost_tracking_id=None,
    )
    dataframe(selected)


def page_free_query():
    section_title("自由彙整", "依時間範圍、人員、部門、Cost_Tracking_ID 查詢週報資料。")

    db.rebuild_all_weekly_report_log()

    week_options = sorted(db.get_week_options())
    if not week_options:
        week_options = [db.get_current_week()]

    departments = get_select_options(db.get_master_values("Department"), include_all=True)
    staff_names = get_select_options(db.get_staff()["Staff_Name"].tolist(), include_all=True)
    cost_ids = get_select_options(db.query_df("SELECT Cost_Tracking_ID FROM project_budget_master ORDER BY Cost_Tracking_ID")["Cost_Tracking_ID"].tolist(), include_all=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        start_week = st.selectbox("Start_Week", week_options, index=0)
    with c2:
        end_week = st.selectbox("End_Week", week_options, index=len(week_options) - 1)
    with c3:
        department = st.selectbox("Department", departments)
    with c4:
        staff_name = st.selectbox("Staff_Name", staff_names)
    with c5:
        cost_id = st.selectbox("Cost_Tracking_ID", cost_ids)

    result = db.get_weekly_report_filtered(
        start_week=start_week,
        end_week=end_week,
        department=department,
        staff_name=staff_name,
        cost_tracking_id=cost_id,
    )

    st.subheader("查詢結果")
    dataframe(result, height=460)

    filename, data = export_query_result(result)
    st.download_button(
        "匯出目前查詢結果 Excel",
        data=data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def page_dashboard():
    section_title("自動彙整 Dashboard", "即時彙整每個工番號 / 依賴號的累計工時、預算消耗率與缺漏週報。")

    db.rebuild_all_weekly_report_log()
    current_week = db.get_current_week()

    project_summary = db.get_project_hour_summary(current_week)
    staff_summary = db.get_staff_weekly_summary()
    missing = db.get_missing_weekly_summary()

    active_count = db.query_df("SELECT COUNT(*) AS cnt FROM project_budget_master WHERE Status='Active'").iloc[0]["cnt"]
    week_hours = float(project_summary["Weekly_Hours"].sum()) if not project_summary.empty else 0
    cumulative_hours = float(project_summary["Cumulative_Hours"].sum()) if not project_summary.empty else 0
    missing_count = len(missing)
    over_budget_count = int((project_summary["Cumulative_Hours"] > project_summary["Budget_Hours"]).sum()) if not project_summary.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Active Cost_Tracking_ID 數", int(active_count))
    c2.metric("本週總工時", f"{week_hours:.1f}")
    c3.metric("累計總工時", f"{cumulative_hours:.1f}")
    c4.metric("Missing Weekly Summary 數", int(missing_count))
    c5.metric("超過 Budget_Hours 工番數", int(over_budget_count))

    st.subheader("Project Hour Summary")
    dataframe(project_summary, height=360)

    if not project_summary.empty:
        chart_df = project_summary.set_index("Cost_Tracking_ID")[["Cumulative_Hours", "Budget_Hours"]]
        st.bar_chart(chart_df)

    st.subheader("Staff Weekly Summary")
    dataframe(staff_summary, height=300)

    st.subheader("Missing Weekly Summary")
    dataframe(missing, height=260)


def page_missing_summary():
    section_title("缺漏週報", "有 Daily Worklog 但尚未提交 Weekly Summary 的項目。")

    db.rebuild_all_weekly_report_log()
    missing = db.get_missing_weekly_summary()

    if missing.empty:
        st.success("目前沒有缺漏週報。")
    else:
        dataframe(missing, height=520)


def page_export_excel():
    section_title("匯出 Excel", "匯出完整 workbook，包含所有主檔、日報、週報、缺漏與 Dashboard 來源資料。")

    db.rebuild_all_weekly_report_log()

    st.write("匯出 Sheet：")
    st.write([
        "Project_Budget_Master",
        "Daily_Worklog",
        "Weekly_Summary_Input",
        "Weekly_Report_Log",
        "Project_Hour_Summary",
        "Staff_Weekly_Summary",
        "Missing_Weekly_Summary",
        "Dashboard_Source",
        "Master_Lists",
    ])

    filename, data = export_full_workbook()
    st.download_button(
        "下載完整 Excel Workbook",
        data=data,
        file_name=filename,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )


def page_master_data():
    section_title("Master Data", "第一版提供 seed data 初始化、查看，以及簡易新增。")

    tabs = st.tabs(["Staff_Master", "Master_Lists"])

    with tabs[0]:
        st.subheader("Staff_Master")
        dataframe(db.get_table("staff_master"))

        with st.form("staff_add_form", clear_on_submit=True):
            st.write("新增 / 更新人員")
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                staff_name = st.text_input("Staff_Name")
            with col2:
                department = st.selectbox("Department", db.get_master_values("Department"))
            with col3:
                role = st.text_input("Role", value="Engineer")
            with col4:
                active_flag = st.selectbox("Active_Flag", [1, 0])
            submitted = st.form_submit_button("儲存人員")
            if submitted:
                try:
                    db.upsert_staff(staff_name, department, role, active_flag)
                    st.success("人員資料已儲存。請重新整理畫面查看最新結果。")
                except Exception as e:
                    st.error(str(e))

    with tabs[1]:
        st.subheader("Master_Lists")
        dataframe(db.get_table("master_lists"))

        with st.form("master_list_add_form", clear_on_submit=True):
            st.write("新增 Master List Value")
            col1, col2 = st.columns(2)
            with col1:
                list_type = st.selectbox("List_Type", ["Department", "Product_Line", "Platform_Line", "Work_Category", "Health", "Status"])
            with col2:
                list_value = st.text_input("List_Value")
            submitted = st.form_submit_button("新增清單值")
            if submitted:
                try:
                    db.add_master_list_value(list_type, list_value)
                    st.success("Master List 已新增。請重新整理畫面查看最新結果。")
                except Exception as e:
                    st.error(str(e))


MENU = {
    "預算設定": page_budget_setting,
    "日報輸入": page_daily_worklog,
    "週報輸入": page_weekly_summary,
    "自由彙整": page_free_query,
    "自動彙整 Dashboard": page_dashboard,
    "缺漏週報": page_missing_summary,
    "匯出 Excel": page_export_excel,
    "Master Data": page_master_data,
}


st.sidebar.title("GLOBAL Weekly Report Demo")
choice = st.sidebar.radio("選單", list(MENU.keys()))
st.sidebar.caption("Local Demo / SQLite / Streamlit")

MENU[choice]()
