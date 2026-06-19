import streamlit as st
import pandas as pd
from datetime import date

import database as db
from export_excel import export_full_workbook, export_query_result


st.set_page_config(
    page_title="GLOBAL Weekly Report Demo v3",
    page_icon="🗓️",
    layout="wide",
)

db.init_db()


def title(text, caption=None):
    st.title(text)
    if caption:
        st.caption(caption)


def dfview(df, height=360):
    st.dataframe(df, use_container_width=True, hide_index=True, height=height)


def ok(message):
    st.success(message)
    db.rebuild_weekly_report_log()


def get_current_user():
    users = db.get_users(active_only=True)
    if users.empty:
        st.error("沒有可用 Demo User。")
        st.stop()

    if "demo_user_email" not in st.session_state:
        st.session_state.demo_user_email = users.iloc[0]["User_Email"]

    emails = users["User_Email"].tolist()
    if st.session_state.demo_user_email not in emails:
        st.session_state.demo_user_email = emails[0]

    selected = st.sidebar.selectbox(
        "Demo Login / 模擬登入者",
        emails,
        index=emails.index(st.session_state.demo_user_email),
    )
    st.session_state.demo_user_email = selected

    user = db.get_user_by_email(selected)
    if not user:
        st.error("Demo User 無效或已停用。")
        st.stop()
    return user


USER = get_current_user()


def can_edit(page):
    return bool(db.get_permission(USER["Role"], page)["Can_Edit"])


def can_export(page):
    return bool(db.get_permission(USER["Role"], page)["Can_Export"])


def user_badge():
    st.sidebar.markdown("---")
    st.sidebar.caption("Current User")
    st.sidebar.write(f"**{USER['Staff_Name']}**")
    st.sidebar.write(f"Role: **{USER['Role']}**")
    st.sidebar.write(f"Dept: **{USER['Department']}**")
    st.sidebar.write(USER["User_Email"])


def scoped_staff_options():
    staff = db.get_staff()
    role = USER["Role"]
    if role == "Admin":
        return staff["Staff_Name"].tolist()
    if role == "Manager":
        return staff[staff["Department"] == USER["Department"]]["Staff_Name"].tolist()
    if role in ["Staff", "PD/PM"]:
        return [USER["Staff_Name"]]
    return []


def page_budget():
    title("預算設定", "PD/PM 可維護自己 Owner 的案件；Admin 可維護全部。")
    if not can_edit("預算設定"):
        st.warning("目前角色沒有編輯權限。")
    product_lines = db.get_master_values("Product_Line")
    platform_lines = db.get_master_values("Platform_Line")
    status_list = db.get_master_values("Status")
    staff_names = db.get_staff()["Staff_Name"].tolist()

    if can_edit("預算設定"):
        with st.form("budget_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                opp = st.text_input("Opportunity_ID", value="OPP-2026-NEW")
                cid = st.text_input("Cost_Tracking_ID")
                customer = st.text_input("Customer")
            with c2:
                pname = st.text_input("Project_Name")
                pl = st.selectbox("Product_Line", product_lines)
                pfl = st.selectbox("Platform_Line", platform_lines)
            with c3:
                budget = st.number_input("Budget_Hours", min_value=0.0, value=100.0, step=10.0)
                est = st.number_input("PD/PM_Estimated_Hours", min_value=0.0, value=100.0, step=10.0)
                if USER["Role"] == "PD/PM":
                    owner = st.text_input("Owner", value=USER["Staff_Name"], disabled=True)
                else:
                    owner = st.selectbox("Owner", staff_names)
                status = st.selectbox("Status", status_list, index=status_list.index("Active") if "Active" in status_list else 0)

            if st.form_submit_button("儲存預算資料", type="primary"):
                try:
                    db.upsert_project_budget({
                        "Opportunity_ID": opp.strip(),
                        "Cost_Tracking_ID": cid.strip(),
                        "Customer": customer.strip(),
                        "Project_Name": pname.strip(),
                        "Product_Line": pl,
                        "Platform_Line": pfl,
                        "Budget_Hours": budget,
                        "Sales_Estimated_Hours": est,
                        "Owner": owner,
                        "Status": status,
                    }, USER)
                    ok("預算資料已儲存。")
                except Exception as e:
                    st.error(str(e))

    st.subheader("目前可見 Project_Budget_Master")
    dfview(db.get_project_budget_for_display(USER))


def page_daily():
    title("日報輸入", "單筆輸入每日工時。一筆日報只對應一個 Cost_Tracking_ID。")
    if not can_edit("日報輸入"):
        st.warning("目前角色沒有編輯權限。")
        return

    staff_names = scoped_staff_options()
    cost_ids = db.get_active_cost_ids(USER)
    categories = db.get_master_values("Work_Category")
    if not staff_names or not cost_ids:
        st.error("目前角色沒有可輸入的人員或 Cost_Tracking_ID 範圍。")
        return

    with st.form("daily_form", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            wd = st.date_input("Work_Date", value=date.today())
            sn = st.selectbox("Staff_Name", staff_names)
        with c2:
            cid = st.selectbox("Cost_Tracking_ID", cost_ids)
            cat = st.selectbox("Work_Category", categories)
        with c3:
            hours = st.number_input("Hours", min_value=0.5, max_value=24.0, value=1.0, step=0.5)
            content = st.text_input("Work_Content", max_chars=100)

        if st.form_submit_button("儲存日報", type="primary"):
            try:
                wid = db.add_daily_worklog(wd, sn, cid, cat, hours, content, USER)
                ok(f"日報已儲存：{wid}")
            except Exception as e:
                st.error(str(e))

    recent = db.query_df("""
        SELECT Worklog_ID, Work_Date, Report_Week, Staff_Name, Department,
               Cost_Tracking_ID, Work_Category, Hours, Work_Content, Created_By, Created_At
        FROM daily_worklog
        ORDER BY Created_At DESC
        LIMIT 200
    """)
    recent = db.scope_weekly_df(recent, USER).head(20)
    st.subheader("最近 20 筆可見日報")
    dfview(recent, 300)


def page_weekly():
    title("週報輸入", "每週每人針對有投入工時的 Cost_Tracking_ID 填寫本週總結與下週目標。")
    if not can_edit("週報輸入"):
        st.warning("目前角色沒有編輯權限。")
        return

    week_options = db.get_week_options()
    staff_names = scoped_staff_options()
    health_list = db.get_master_values("Health")

    c1, c2 = st.columns(2)
    with c1:
        rw = st.selectbox("Report_Week", week_options)
    with c2:
        sn = st.selectbox("Staff_Name", staff_names)

    cost_ids = db.get_cost_ids_for_staff_week(sn, rw, USER)
    if not cost_ids:
        st.error("目前沒有可填寫週報的 Cost_Tracking_ID。")
        return

    with st.form("weekly_form"):
        cid = st.selectbox("Cost_Tracking_ID", cost_ids)
        summary = st.text_area("Weekly_Summary（500 字以內）", height=130, max_chars=500)
        target = st.text_area("Next_Week_Target（500 字以內）", height=130, max_chars=500)
        health = st.selectbox("Health", health_list)

        if st.form_submit_button("儲存週報", type="primary"):
            try:
                wid = db.upsert_weekly_summary(rw, sn, cid, summary, target, health, USER)
                ok(f"週報已儲存 / 更新：{wid}")
            except Exception as e:
                st.error(str(e))

    st.subheader("目前選定條件的週報 Log")
    dfview(db.get_weekly_report_filtered(rw, rw, staff_name=sn, user=USER))


def page_query():
    title("自由彙整", "依權限範圍查詢週報資料。")
    db.rebuild_weekly_report_log()

    weeks = sorted(db.get_week_options())
    departments = ["ALL"] + db.get_master_values("Department")
    staff = ["ALL"] + db.get_staff()["Staff_Name"].tolist()
    cost_ids = ["ALL"] + db.query_df("SELECT Cost_Tracking_ID FROM project_budget_master ORDER BY Cost_Tracking_ID")["Cost_Tracking_ID"].tolist()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        start = st.selectbox("Start_Week", weeks, index=0)
    with c2:
        end = st.selectbox("End_Week", weeks, index=len(weeks) - 1)
    with c3:
        dept = st.selectbox("Department", departments)
    with c4:
        sn = st.selectbox("Staff_Name", staff)
    with c5:
        cid = st.selectbox("Cost_Tracking_ID", cost_ids)

    result = db.get_weekly_report_filtered(start, end, dept, sn, cid, USER)
    st.subheader("查詢結果")
    dfview(result, 460)

    if can_export("自由彙整"):
        filename, data = export_query_result(result)
        st.download_button("匯出目前查詢結果 Excel", data=data, file_name=filename,
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("目前角色沒有匯出權限。")


def page_dashboard():
    title("自動彙整 Dashboard", "依目前登入角色的資料範圍即時彙整。")
    db.rebuild_weekly_report_log()

    project = db.get_project_hour_summary(user=USER)
    staff = db.get_staff_weekly_summary(USER)
    missing = db.get_missing_weekly_summary(USER)

    active_count = int(len(project[project["Status"] == "Active"])) if not project.empty else 0
    week_hours = float(project["Weekly_Hours"].sum()) if not project.empty else 0
    cumulative_hours = float(project["Cumulative_Hours"].sum()) if not project.empty else 0
    missing_count = len(missing)
    over_budget = int((project["Cumulative_Hours"] > project["Budget_Hours"]).sum()) if not project.empty else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("可見 Active ID 數", active_count)
    c2.metric("本週總工時", f"{week_hours:.1f}")
    c3.metric("累計總工時", f"{cumulative_hours:.1f}")
    c4.metric("Missing Summary 數", missing_count)
    c5.metric("超過 Budget 工番數", over_budget)

    st.subheader("Project Hour Summary")
    dfview(project)
    if not project.empty:
        st.bar_chart(project.set_index("Cost_Tracking_ID")[["Cumulative_Hours", "Budget_Hours"]])

    st.subheader("Staff Weekly Summary")
    dfview(staff, 300)

    st.subheader("Missing Weekly Summary")
    dfview(missing, 260)


def page_missing():
    title("缺漏週報", "有 Daily Worklog 但尚未提交 Weekly Summary 的項目。")
    db.rebuild_weekly_report_log()
    missing = db.get_missing_weekly_summary(USER)
    if missing.empty:
        st.success("目前權限範圍內沒有缺漏週報。")
    else:
        dfview(missing, 520)


def page_export():
    title("匯出 Excel", "依目前角色權限匯出 workbook。Admin 匯出全量，其餘角色只匯出可見範圍。")
    if not can_export("匯出 Excel"):
        st.warning("目前角色沒有 Excel 匯出權限。")
        return
    filename, data = export_full_workbook(USER)
    st.download_button("下載權限範圍 Excel Workbook", data=data, file_name=filename,
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="primary")


def page_master():
    title("Master Data", "Admin 可新增、修改、停用 Master Data。已被歷史資料引用的值建議停用，不建議刪除。")
    if not can_edit("Master Data"):
        st.warning("目前角色沒有 Master Data 編輯權限。")
        return

    tabs = st.tabs(["Staff_Master", "Master_Lists", "Role_Permission", "Audit_Log"])

    with tabs[0]:
        staff_df = db.get_table("staff_master")
        st.subheader("Staff_Master")
        dfview(staff_df)

        st.markdown("### 新增 / 更新人員")
        with st.form("staff_add_form"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                staff_name = st.text_input("Staff_Name")
            with c2:
                department = st.selectbox("Department", db.get_master_values("Department"), key="staff_add_dept")
            with c3:
                role = st.text_input("Role", value="Engineer")
            with c4:
                active_flag = st.selectbox("Active_Flag", [1, 0], key="staff_add_active")
            if st.form_submit_button("新增 / 更新人員", type="primary"):
                try:
                    db.upsert_staff(staff_name, department, role, active_flag, USER)
                    ok("人員資料已新增 / 更新。")
                except Exception as e:
                    st.error(str(e))

        if not staff_df.empty:
            st.markdown("### 編輯既有人員")
            selected_staff = st.selectbox("選擇 Staff_Name", staff_df["Staff_Name"].tolist())
            rec = staff_df[staff_df["Staff_Name"] == selected_staff].iloc[0].to_dict()

            with st.form("staff_edit_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    depts = db.get_master_values("Department")
                    dept_idx = depts.index(rec["Department"]) if rec["Department"] in depts else 0
                    new_dept = st.selectbox("Department", depts, index=dept_idx, key="staff_edit_dept")
                with c2:
                    new_role = st.text_input("Role", value=str(rec.get("Role") or ""))
                with c3:
                    new_active = st.selectbox("Active_Flag", [1, 0], index=0 if int(rec["Active_Flag"]) == 1 else 1, key="staff_edit_active")
                if st.form_submit_button("更新既有人員", type="primary"):
                    try:
                        db.update_staff_master(selected_staff, new_dept, new_role, new_active, USER)
                        ok(f"已更新 Staff_Master：{selected_staff}")
                    except Exception as e:
                        st.error(str(e))

            with st.expander("刪除此人員"):
                st.warning("若此人員已被資料引用，系統會阻止刪除。建議 Active_Flag=0。")
                confirm = st.checkbox(f"我確認要刪除 {selected_staff}", key=f"del_staff_{selected_staff}")
                if st.button("刪除 Staff_Master", disabled=not confirm):
                    try:
                        db.delete_staff_master(selected_staff, USER)
                        ok(f"已刪除 Staff_Master：{selected_staff}")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with tabs[1]:
        ml_df = db.get_table("master_lists")
        st.subheader("Master_Lists")
        dfview(ml_df)

        st.markdown("### 新增 Master List Value")
        with st.form("ml_add_form"):
            c1, c2 = st.columns(2)
            with c1:
                lt = st.selectbox("List_Type", ["Department", "Product_Line", "Platform_Line", "Work_Category", "Health", "Status", "Role"])
            with c2:
                lv = st.text_input("List_Value")
            if st.form_submit_button("新增清單值", type="primary"):
                try:
                    db.add_master_list_value(lt, lv, USER)
                    ok("Master List 已新增。")
                except Exception as e:
                    st.error(str(e))

        if not ml_df.empty:
            st.markdown("### 編輯 / 停用既有 Master List")
            display = ml_df["List_Type"].astype(str) + " | " + ml_df["List_Value"].astype(str)
            selected = st.selectbox("選擇 Master List", display.tolist())
            old_type, old_value = selected.split(" | ", 1)
            rec = ml_df[(ml_df["List_Type"] == old_type) & (ml_df["List_Value"] == old_value)].iloc[0].to_dict()

            with st.form("ml_edit_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    type_options = ["Department", "Product_Line", "Platform_Line", "Work_Category", "Health", "Status", "Role"]
                    new_type = st.selectbox("List_Type", type_options, index=type_options.index(old_type) if old_type in type_options else 0, key="ml_edit_type")
                with c2:
                    new_value = st.text_input("List_Value", value=old_value)
                with c3:
                    new_active = st.selectbox("Active_Flag", [1, 0], index=0 if int(rec["Active_Flag"]) == 1 else 1, key="ml_edit_active")
                if st.form_submit_button("更新 Master List", type="primary"):
                    try:
                        db.update_master_list_value(old_type, old_value, new_type, new_value, new_active, USER)
                        ok("已更新 Master List。")
                    except Exception as e:
                        st.error(str(e))

            with st.expander("刪除此 Master List"):
                st.warning("若此值已被資料引用，系統會阻止刪除。正式建議 Active_Flag=0。")
                confirm = st.checkbox(f"我確認要刪除 {old_type} / {old_value}", key=f"del_ml_{old_type}_{old_value}")
                if st.button("刪除 Master List", disabled=not confirm):
                    try:
                        db.delete_master_list_value(old_type, old_value, USER)
                        ok("已刪除 Master List。")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with tabs[2]:
        st.subheader("Role_Permission")
        dfview(db.get_table("role_permission"), 520)

    with tabs[3]:
        st.subheader("Audit_Log")
        dfview(db.get_table("audit_log"), 520)


def page_users():
    title("User Management", "Admin 可新增、修改、停用與刪除 Demo Login 使用者。")
    if not can_edit("User Management"):
        st.warning("目前角色沒有 User Management 編輯權限。")
        return

    user_df = db.get_table("user_master")
    st.subheader("User_Master")
    dfview(user_df)

    staff_df = db.get_staff()
    staff_names = staff_df["Staff_Name"].tolist()
    departments = db.get_master_values("Department")
    roles = db.ROLES

    st.markdown("### 新增 / 更新 User")
    with st.form("user_add_form"):
        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            email = st.text_input("User_Email")
        with c2:
            staff = st.selectbox("Staff_Name", staff_names, key="user_add_staff")
        with c3:
            dept = st.selectbox("Department", departments, key="user_add_dept")
        with c4:
            role = st.selectbox("Role", roles, key="user_add_role")
        with c5:
            active = st.selectbox("Active_Flag", [1, 0], key="user_add_active")
        if st.form_submit_button("新增 / 更新 User", type="primary"):
            try:
                db.upsert_user(email, staff, dept, role, active, USER)
                ok("User 已新增 / 更新。")
            except Exception as e:
                st.error(str(e))

    if user_df.empty:
        return

    st.markdown("### 編輯既有 User")
    selected = st.selectbox("選擇 User_Email", user_df["User_Email"].tolist())
    rec = user_df[user_df["User_Email"] == selected].iloc[0].to_dict()

    with st.form("user_edit_form"):
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            staff_idx = staff_names.index(rec["Staff_Name"]) if rec["Staff_Name"] in staff_names else 0
            edit_staff = st.selectbox("Staff_Name", staff_names, index=staff_idx, key="user_edit_staff")
        with c2:
            dept_idx = departments.index(rec["Department"]) if rec["Department"] in departments else 0
            edit_dept = st.selectbox("Department", departments, index=dept_idx, key="user_edit_dept")
        with c3:
            role_idx = roles.index(rec["Role"]) if rec["Role"] in roles else 0
            edit_role = st.selectbox("Role", roles, index=role_idx, key="user_edit_role")
        with c4:
            edit_active = st.selectbox("Active_Flag", [1, 0], index=0 if int(rec["Active_Flag"]) == 1 else 1, key="user_edit_active")
        if st.form_submit_button("更新既有 User", type="primary"):
            try:
                db.upsert_user(selected, edit_staff, edit_dept, edit_role, edit_active, USER)
                ok(f"已更新 User：{selected}")
            except Exception as e:
                st.error(str(e))

    with st.expander("刪除此 User"):
        st.warning("刪除後此 Demo Login 帳號將無法使用。不可刪除目前登入中的自己。")
        confirm = st.checkbox(f"我確認要刪除 {selected}", key=f"del_user_{selected}")
        if st.button("刪除 User", disabled=not confirm):
            try:
                db.delete_user(selected, USER)
                ok(f"已刪除 User：{selected}")
                st.rerun()
            except Exception as e:
                st.error(str(e))


def page_admin_maintenance():
    title("Admin Data Maintenance", "Admin 後台維護已輸入的日報與週報紀錄。")
    if USER["Role"] != "Admin":
        st.warning("只有 Admin 可以使用此頁面。")
        return

    tabs = st.tabs(["Daily Worklog 維護", "Weekly Summary 維護", "Maintenance Audit Log"])

    with tabs[0]:
        daily = db.query_df("""
            SELECT Worklog_ID, Work_Date, Report_Week, Staff_Name, Department, Cost_Tracking_ID,
                   Work_Category, Hours, Work_Content, Created_By, Created_At
            FROM daily_worklog
            ORDER BY Created_At DESC
        """)
        st.subheader("Daily_Worklog 編輯 / 刪除")
        dfview(daily, 320)

        if not daily.empty:
            selected = st.selectbox("選擇要維護的 Worklog_ID", daily["Worklog_ID"].tolist())
            rec = daily[daily["Worklog_ID"] == selected].iloc[0].to_dict()

            with st.form("daily_edit_form"):
                c1, c2, c3 = st.columns(3)
                with c1:
                    wd = st.date_input("Work_Date", value=date.fromisoformat(str(rec["Work_Date"])))
                    staff_names = db.get_staff()["Staff_Name"].tolist()
                    sn = st.selectbox("Staff_Name", staff_names, index=staff_names.index(rec["Staff_Name"]) if rec["Staff_Name"] in staff_names else 0)
                with c2:
                    cids = db.query_df("SELECT Cost_Tracking_ID FROM project_budget_master ORDER BY Cost_Tracking_ID")["Cost_Tracking_ID"].tolist()
                    cid = st.selectbox("Cost_Tracking_ID", cids, index=cids.index(rec["Cost_Tracking_ID"]) if rec["Cost_Tracking_ID"] in cids else 0)
                    cats = db.get_master_values("Work_Category")
                    cat = st.selectbox("Work_Category", cats, index=cats.index(rec["Work_Category"]) if rec["Work_Category"] in cats else 0)
                with c3:
                    hours = st.number_input("Hours", min_value=0.5, max_value=24.0, value=float(rec["Hours"]), step=0.5)
                    content = st.text_input("Work_Content", value=str(rec["Work_Content"]), max_chars=100)
                if st.form_submit_button("更新 Daily Worklog", type="primary"):
                    try:
                        db.update_daily_worklog(selected, wd, sn, cid, cat, hours, content, USER)
                        ok(f"已更新 Daily Worklog：{selected}")
                    except Exception as e:
                        st.error(str(e))

            with st.expander("刪除此 Daily Worklog"):
                confirm = st.checkbox(f"我確認要刪除 {selected}", key=f"del_daily_{selected}")
                if st.button("刪除 Daily Worklog", disabled=not confirm):
                    try:
                        db.delete_daily_worklog(selected, USER)
                        ok(f"已刪除 Daily Worklog：{selected}")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with tabs[1]:
        weekly = db.query_df("""
            SELECT Weekly_Input_ID, Report_Week, Staff_Name, Cost_Tracking_ID,
                   Weekly_Summary, Next_Week_Target, Health, Created_By, Updated_By, Created_At, Updated_At
            FROM weekly_summary_input
            ORDER BY Updated_At DESC, Created_At DESC
        """)
        st.subheader("Weekly_Summary_Input 編輯 / 刪除")
        dfview(weekly, 320)

        if not weekly.empty:
            selected = st.selectbox("選擇要維護的 Weekly_Input_ID", weekly["Weekly_Input_ID"].tolist())
            rec = weekly[weekly["Weekly_Input_ID"] == selected].iloc[0].to_dict()

            with st.form("weekly_edit_form"):
                c1, c2 = st.columns(2)
                with c1:
                    rw = st.text_input("Report_Week", value=str(rec["Report_Week"]))
                    staff_names = db.get_staff()["Staff_Name"].tolist()
                    sn = st.selectbox("Staff_Name", staff_names, index=staff_names.index(rec["Staff_Name"]) if rec["Staff_Name"] in staff_names else 0, key="weekly_edit_staff")
                with c2:
                    cids = db.query_df("SELECT Cost_Tracking_ID FROM project_budget_master ORDER BY Cost_Tracking_ID")["Cost_Tracking_ID"].tolist()
                    cid = st.selectbox("Cost_Tracking_ID", cids, index=cids.index(rec["Cost_Tracking_ID"]) if rec["Cost_Tracking_ID"] in cids else 0, key="weekly_edit_cid")
                    health_list = db.get_master_values("Health")
                    health = st.selectbox("Health", health_list, index=health_list.index(rec["Health"]) if rec["Health"] in health_list else 0)
                summary = st.text_area("Weekly_Summary", value=str(rec["Weekly_Summary"]), height=130, max_chars=500)
                target = st.text_area("Next_Week_Target", value=str(rec["Next_Week_Target"]), height=130, max_chars=500)

                if st.form_submit_button("更新 Weekly Summary", type="primary"):
                    try:
                        db.update_weekly_summary_input(selected, rw, sn, cid, summary, target, health, USER)
                        ok(f"已更新 Weekly Summary：{selected}")
                    except Exception as e:
                        st.error(str(e))

            with st.expander("刪除此 Weekly Summary"):
                confirm = st.checkbox(f"我確認要刪除 {selected}", key=f"del_weekly_{selected}")
                if st.button("刪除 Weekly Summary", disabled=not confirm):
                    try:
                        db.delete_weekly_summary_input(selected, USER)
                        ok(f"已刪除 Weekly Summary：{selected}")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

    with tabs[2]:
        st.subheader("Audit_Log")
        dfview(db.query_df("""
            SELECT Audit_ID, User_Email, Action_Type, Table_Name, Record_Key, Old_Value, New_Value, Created_At
            FROM audit_log
            ORDER BY Created_At DESC
            LIMIT 300
        """), 520)


def page_admin_config():
    title("Admin Config Import / Export", "用一個 Excel 維護人員、帳號、角色權限與 Master Lists。")
    if USER["Role"] != "Admin":
        st.warning("只有 Admin 可以使用此頁面。")
        return

    st.subheader("1. 下載目前 Admin Config Excel")
    st.write("下載目前 Staff_Master / User_Master / Role_Permission / Master_Lists。")
    cfg_name, cfg_data = db.export_admin_config_workbook()
    st.download_button(
        "Export Current Admin Config",
        data=cfg_data,
        file_name=cfg_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    st.markdown("---")
    st.subheader("2. 上傳修改後的 Admin Config Excel")
    uploaded = st.file_uploader("Upload GLOBAL_Weekly_Report_Admin_Config.xlsx", type=["xlsx"])

    if uploaded is not None:
        try:
            frames = db.read_admin_config_excel(uploaded)
            errors, summary = db.validate_admin_config_frames(frames)

            st.markdown("### 匯入檢查摘要")
            dfview(summary, 180)

            preview_tabs = st.tabs(["Staff_Master", "User_Master", "Role_Permission", "Master_Lists"])
            for tab, sheet in zip(preview_tabs, ["Staff_Master", "User_Master", "Role_Permission", "Master_Lists"]):
                with tab:
                    dfview(frames[sheet].head(200), 300)

            if errors:
                st.error("Validation Failed")
                for err in errors[:50]:
                    st.write(f"- {err}")
                if len(errors) > 50:
                    st.write(f"... 還有 {len(errors) - 50} 筆錯誤")
            else:
                st.success("Validation Passed. 可以套用設定。")
                confirm = st.checkbox("我確認要將此 Excel 設定套用到資料庫")
                if st.button("Apply Config to Database", type="primary", disabled=not confirm):
                    try:
                        result = db.apply_admin_config_frames(frames, USER)
                        st.success("Admin Config 已套用。請重新整理頁面或切換 Demo Login 查看新權限。")
                        dfview(result, 180)
                    except Exception as e:
                        st.error(str(e))
        except Exception as e:
            st.error(str(e))

    st.markdown("---")
    st.subheader("Excel 格式")
    st.code("""Workbook Sheets:
- Staff_Master: Staff_Name, Department, Role, Active_Flag
- User_Master: User_Email, Staff_Name, Department, Role, Active_Flag
- Role_Permission: Role, Page_Name, Can_View, Can_Edit, Can_Export
- Master_Lists: List_Type, List_Value, Active_Flag
- Validation_Guide: 說明用，不匯入
""")

    st.warning("建議停用資料使用 Active_Flag=0，不要直接刪除已被歷史資料引用的人員或主檔。")


MENU = {
    "預算設定": page_budget,
    "日報輸入": page_daily,
    "週報輸入": page_weekly,
    "自由彙整": page_query,
    "自動彙整 Dashboard": page_dashboard,
    "缺漏週報": page_missing,
    "匯出 Excel": page_export,
    "Master Data": page_master,
    "User Management": page_users,
    "Admin Data Maintenance": page_admin_maintenance,
    "Admin Config Import / Export": page_admin_config,
}


st.sidebar.title("GLOBAL Weekly Report Demo v3")
allowed_pages = db.get_allowed_pages(USER["Role"])
if not allowed_pages:
    st.error("目前角色沒有任何頁面權限。請用 Admin 調整 role_permission。")
    st.stop()

choice = st.sidebar.radio("選單", allowed_pages)
st.sidebar.caption("Local Demo / SQLite / Streamlit / Excel Admin Config")
user_badge()

MENU[choice]()
