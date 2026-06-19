
import streamlit as st
from datetime import date
import database as db
from export_excel import export_full_workbook, export_query_result

st.set_page_config(page_title="GLOBAL Weekly Report Demo v2", page_icon="🗓️", layout="wide")
db.init_db()

def get_user():
    users = db.get_users(True)
    if users.empty:
        st.error("沒有可用 Demo User。"); st.stop()
    emails=users["User_Email"].tolist()
    if "demo_user_email" not in st.session_state or st.session_state.demo_user_email not in emails:
        st.session_state.demo_user_email=emails[0]
    email=st.sidebar.selectbox("Demo Login / 模擬登入者", emails, index=emails.index(st.session_state.demo_user_email))
    st.session_state.demo_user_email=email
    u=db.user_by_email(email)
    if not u: st.error("Demo User 無效或已停用。"); st.stop()
    return u

U=get_user()

def title(t,c=None):
    st.title(t)
    if c: st.caption(c)

def dfview(df,h=360):
    st.dataframe(df,use_container_width=True,hide_index=True,height=h)

def perm(page):
    return db.permission(U["Role"],page)

def can_edit(page):
    if not perm(page)["Can_Edit"]:
        st.warning("目前角色沒有此頁面的編輯權限。")
        return False
    return True

def can_export(page):
    return bool(perm(page)["Can_Export"])

def ok(msg):
    st.success(msg); db.rebuild_weekly()

def staff_options():
    s=db.staff()
    if U["Role"]=="Admin": return s["Staff_Name"].tolist()
    if U["Role"]=="Manager": return s[s["Department"]==U["Department"]]["Staff_Name"].tolist()
    if U["Role"] in ["Staff","PD/PM"]: return [U["Staff_Name"]]
    return []

def allopt(vals):
    return ["ALL"]+list(vals)

def page_budget():
    title("預算設定","PD/PM 可維護自己 Owner 的案件；Admin 可維護全部。")
    editable=can_edit("預算設定")
    if editable:
        with st.form("budget"):
            c1,c2,c3=st.columns(3)
            with c1:
                opp=st.text_input("Opportunity_ID","OPP-2026-NEW")
                cid=st.text_input("Cost_Tracking_ID / 工番號・依賴號")
                customer=st.text_input("Customer")
            with c2:
                pname=st.text_input("Project_Name")
                product=st.selectbox("Product_Line",db.master_values("Product_Line"))
                platform=st.selectbox("Platform_Line",db.master_values("Platform_Line"))
            with c3:
                budget=st.number_input("Budget_Hours",min_value=0.0,value=100.0,step=10.0)
                estimate=st.number_input("PD/PM_Estimated_Hours",min_value=0.0,value=100.0,step=10.0)
                if U["Role"]=="PD/PM":
                    owner=st.text_input("Owner",value=U["Staff_Name"],disabled=True)
                else:
                    owner=st.selectbox("Owner",db.staff()["Staff_Name"].tolist())
                status=st.selectbox("Status",db.master_values("Status"),index=0)
            if st.form_submit_button("儲存預算資料",type="primary"):
                try:
                    db.upsert_budget({"Opportunity_ID":opp.strip(),"Cost_Tracking_ID":cid.strip(),"Customer":customer.strip(),"Project_Name":pname.strip(),"Product_Line":product,"Platform_Line":platform,"Budget_Hours":budget,"Sales_Estimated_Hours":estimate,"Owner":owner,"Status":status},U)
                    ok("預算資料已儲存。")
                except Exception as e: st.error(str(e))
    st.subheader("目前可見 Project_Budget_Master")
    dfview(db.project_budget_display(U),420)

def page_daily():
    title("日報輸入","單筆輸入每日工時。一筆日報只對應一個 Cost_Tracking_ID。")
    if not can_edit("日報輸入"): return
    staffs=staff_options(); ids=db.active_cost_ids(U); cats=db.master_values("Work_Category")
    if not staffs: st.error("目前角色沒有可輸入的人員範圍。"); return
    if not ids: st.error("目前角色沒有可輸入的 Active Cost_Tracking_ID。"); return
    with st.form("daily",clear_on_submit=True):
        c1,c2,c3=st.columns(3)
        with c1:
            wd=st.date_input("Work_Date / 作業日期",value=date.today())
            sn=st.selectbox("Staff_Name / 人員",staffs)
        with c2:
            cid=st.selectbox("Cost_Tracking_ID / 工番號・依賴號",ids)
            cat=st.selectbox("Work_Category / 工作分類",cats)
        with c3:
            hours=st.number_input("Hours / 工時",min_value=0.5,max_value=24.0,value=1.0,step=0.5)
            content=st.text_input("Work_Content / 簡短內容",max_chars=100)
        if st.form_submit_button("儲存日報",type="primary"):
            try:
                wid=db.add_daily(wd,sn,cid,cat,hours,content,U)
                ok(f"日報已儲存：{wid}")
            except Exception as e: st.error(str(e))
    st.subheader("最近 20 筆可見日報紀錄")
    recent=db.qdf("""SELECT Worklog_ID,Work_Date,Report_Week,Staff_Name,Department,Cost_Tracking_ID,Work_Category,Hours,Work_Content,Created_By,Created_At FROM daily_worklog ORDER BY Created_At DESC LIMIT 200""")
    dfview(db.scope_weekly(recent,U).head(20),360)

def page_weekly():
    title("週報輸入","每週每人針對有投入工時的 Cost_Tracking_ID 填寫本週總結與下週目標。")
    if not can_edit("週報輸入"): return
    weeks=db.week_options(); staffs=staff_options(); health=db.master_values("Health")
    c1,c2=st.columns(2)
    with c1: rw=st.selectbox("Report_Week / 週次",weeks)
    with c2: sn=st.selectbox("Staff_Name / 人員",staffs)
    ids=db.cost_ids_for_staff_week(sn,rw,U)
    if not ids: st.error("目前沒有可填寫週報的 Cost_Tracking_ID。"); return
    with st.form("weekly"):
        cid=st.selectbox("Cost_Tracking_ID / 工番號・依賴號",ids)
        summary=st.text_area("Weekly_Summary / 本週總結（500 字以內）",height=130,max_chars=500)
        target=st.text_area("Next_Week_Target / 下週目標（500 字以內）",height=130,max_chars=500)
        h=st.selectbox("Health / 狀態",health)
        if st.form_submit_button("儲存週報",type="primary"):
            try:
                wsi=db.upsert_weekly(rw,sn,cid,summary,target,h,U)
                ok(f"週報已儲存 / 更新：{wsi}")
            except Exception as e: st.error(str(e))
    st.subheader("目前選定條件的週報 Log")
    dfview(db.weekly_filtered(rw,rw,staff_name=sn,u=U),360)

def page_query():
    title("自由彙整","依目前登入角色的資料範圍查詢週報資料。")
    db.rebuild_weekly()
    weeks=sorted(db.week_options()) or [db.get_current_week()]
    c1,c2,c3,c4,c5=st.columns(5)
    with c1: start=st.selectbox("Start_Week",weeks,index=0)
    with c2: end=st.selectbox("End_Week",weeks,index=len(weeks)-1)
    with c3: dept=st.selectbox("Department",allopt(db.master_values("Department")))
    with c4: sn=st.selectbox("Staff_Name",allopt(db.staff()["Staff_Name"].tolist()))
    with c5: cid=st.selectbox("Cost_Tracking_ID",allopt(db.qdf("SELECT Cost_Tracking_ID FROM project_budget_master ORDER BY Cost_Tracking_ID")["Cost_Tracking_ID"].tolist()))
    res=db.weekly_filtered(start,end,dept,sn,cid,U)
    st.subheader("查詢結果"); dfview(res,460)
    if can_export("自由彙整"):
        fn,data=export_query_result(res)
        st.download_button("匯出目前查詢結果 Excel",data=data,file_name=fn,mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else: st.info("目前角色沒有匯出權限。")

def page_dashboard():
    title("自動彙整 Dashboard","依目前登入角色的資料範圍即時彙整。")
    db.rebuild_weekly(); ps=db.project_summary(u=U); ss=db.staff_weekly_summary(U); miss=db.missing_summary(U)
    active=int(len(ps[ps["Status"]=="Active"])) if not ps.empty else 0
    wh=float(ps["Weekly_Hours"].sum()) if not ps.empty else 0
    ch=float(ps["Cumulative_Hours"].sum()) if not ps.empty else 0
    over=int((ps["Cumulative_Hours"]>ps["Budget_Hours"]).sum()) if not ps.empty else 0
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("可見 Active Cost_Tracking_ID 數",active)
    c2.metric("本週總工時",f"{wh:.1f}")
    c3.metric("累計總工時",f"{ch:.1f}")
    c4.metric("Missing Weekly Summary 數",len(miss))
    c5.metric("超過 Budget_Hours 工番數",over)
    st.subheader("Project Hour Summary"); dfview(ps,360)
    if not ps.empty: st.bar_chart(ps.set_index("Cost_Tracking_ID")[["Cumulative_Hours","Budget_Hours"]])
    st.subheader("Staff Weekly Summary"); dfview(ss,300)
    st.subheader("Missing Weekly Summary"); dfview(miss,260)

def page_missing():
    title("缺漏週報","有 Daily Worklog 但尚未提交 Weekly Summary 的項目。")
    db.rebuild_weekly(); miss=db.missing_summary(U)
    if miss.empty: st.success("目前權限範圍內沒有缺漏週報。")
    else: dfview(miss,520)

def page_export():
    title("匯出 Excel","依目前角色權限匯出 workbook。Admin 匯出全量，其餘角色只匯出可見範圍。")
    if not can_export("匯出 Excel"):
        st.warning("目前角色沒有 Excel 匯出權限。"); return
    fn,data=export_full_workbook(U)
    st.download_button("下載權限範圍 Excel Workbook",data=data,file_name=fn,mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",type="primary")

def page_master():
    title("Master Data","僅 Admin 可編輯 Master Data。")
    editable=can_edit("Master Data")
    tabs=st.tabs(["Staff_Master","Master_Lists","Role_Permission","Audit_Log"])
    with tabs[0]:
        dfview(db.table("staff_master"))
        if editable:
            with st.form("staff"):
                c1,c2,c3,c4=st.columns(4)
                with c1: sn=st.text_input("Staff_Name")
                with c2: dept=st.selectbox("Department",db.master_values("Department"))
                with c3: role=st.text_input("Role","Engineer")
                with c4: active=st.selectbox("Active_Flag",[1,0])
                if st.form_submit_button("儲存人員"):
                    try: db.upsert_staff(sn,dept,role,active,U); st.success("人員資料已儲存。")
                    except Exception as e: st.error(str(e))
    with tabs[1]:
        dfview(db.table("master_lists"))
        if editable:
            with st.form("ml"):
                c1,c2=st.columns(2)
                with c1: lt=st.selectbox("List_Type",["Department","Product_Line","Platform_Line","Work_Category","Health","Status","Role"])
                with c2: lv=st.text_input("List_Value")
                if st.form_submit_button("新增清單值"):
                    try: db.add_master_value(lt,lv,U); st.success("Master List 已新增。")
                    except Exception as e: st.error(str(e))
    with tabs[2]: dfview(db.table("role_permission"),520)
    with tabs[3]: dfview(db.table("audit_log"),520)

def page_users():
    title("User Management","Demo Login 用帳號與角色管理。僅 Admin 可見。")
    editable=can_edit("User Management")
    dfview(db.table("user_master"))
    if editable:
        with st.form("user"):
            staff_df=db.staff(); staffs=staff_df["Staff_Name"].tolist()
            c1,c2,c3,c4,c5=st.columns(5)
            with c1: email=st.text_input("User_Email")
            with c2: sn=st.selectbox("Staff_Name",staffs)
            with c3: dept=st.selectbox("Department",db.master_values("Department"))
            with c4: role=st.selectbox("Role",["Admin","Manager","Staff","PD/PM","Viewer"])
            with c5: active=st.selectbox("Active_Flag",[1,0])
            if st.form_submit_button("儲存 User",type="primary"):
                try: db.upsert_user(email,sn,dept,role,active,U); st.success("User 已儲存。")
                except Exception as e: st.error(str(e))

MENU={"預算設定":page_budget,"日報輸入":page_daily,"週報輸入":page_weekly,"自由彙整":page_query,"自動彙整 Dashboard":page_dashboard,"缺漏週報":page_missing,"匯出 Excel":page_export,"Master Data":page_master,"User Management":page_users}

st.sidebar.title("GLOBAL Weekly Report Demo v2")
pages=db.allowed_pages(U["Role"])
if not pages:
    st.error("目前角色沒有任何頁面權限。"); st.stop()
choice=st.sidebar.radio("選單",pages)
st.sidebar.caption("Local Demo / SQLite / Streamlit / RBAC")
st.sidebar.markdown("---")
st.sidebar.caption("Current User")
st.sidebar.write(f"**{U['Staff_Name']}**")
st.sidebar.write(f"Role: **{U['Role']}**")
st.sidebar.write(f"Dept: **{U['Department']}**")
st.sidebar.write(U["User_Email"])
MENU[choice]()
