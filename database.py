
import sqlite3, random
from pathlib import Path
from datetime import datetime, date
import pandas as pd

DB_PATH = Path(__file__).parent / "global_weekly_report_demo.db"

STAFF_SEED = [
    ("小李","機械設計","Engineer",1),("張三","電氣","Engineer",1),("王四","組立","Engineer",1),
    ("JOHN","CS","Engineer",1),("鈴木","營業","PD/PM",1),("大島","機械設計","Engineer",1),
    ("MIKE","電氣","Engineer",1),("MERRY","組立","Engineer",1),("MAX","CS","Engineer",1),
    ("JAME","營業","PD/PM",1),("大河","機械設計","Engineer",1),("吾郎","電氣","Engineer",1),
    ("人傑","組立","Engineer",1),("大勇","CS","Engineer",1)
]
MASTER_LIST_SEED = {
    "Department":["機械設計","電氣","組立","CS","營業"],
    "Product_Line":["OWLS-1800","OWLS-2200","OCSS-600","OTFC-1800","T"],
    "Platform_Line":["機械設計","電氣","組立","CS","營業"],
    "Work_Category":["定例會議","資料彙整","設計","組立","調適","現場異常","異常分析"],
    "Health":["Green","Yellow","Red"],
    "Status":["Active","Hold","Closed"],
    "Role":["Admin","Manager","Staff","PD/PM","Viewer"],
}
DEFAULT_COST_IDS = ["W0001","W0002","W0003","W0004","A0011","A0012"]
DEFAULT_USERS = [
    ("admin@demo.com","小李","機械設計","Admin",1),
    ("manager@demo.com","張三","電氣","Manager",1),
    ("staff@demo.com","王四","組立","Staff",1),
    ("pdpm@demo.com","鈴木","營業","PD/PM",1),
    ("viewer@demo.com","JOHN","CS","Viewer",1),
]
PAGE_ORDER = ["預算設定","日報輸入","週報輸入","自由彙整","自動彙整 Dashboard","缺漏週報","匯出 Excel","Master Data","User Management","Admin Data Maintenance"]

def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def qdf(sql, params=None):
    with conn() as c:
        return pd.read_sql_query(sql, c, params=params or [])

def execute(sql, params=None):
    with conn() as c:
        c.execute(sql, params or [])
        c.commit()

def col_exists(c, table, col):
    return any(r[1] == col for r in c.execute(f"PRAGMA table_info({table})").fetchall())

def add_col(c, table, definition):
    col = definition.split()[0]
    if not col_exists(c, table, col):
        c.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")

def init_db():
    with conn() as c:
        cur = c.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS staff_master(
            Staff_Name TEXT PRIMARY KEY, Department TEXT NOT NULL, Role TEXT, Active_Flag INTEGER DEFAULT 1)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS master_lists(
            List_Type TEXT NOT NULL, List_Value TEXT NOT NULL, Active_Flag INTEGER DEFAULT 1,
            PRIMARY KEY(List_Type,List_Value))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS project_budget_master(
            Opportunity_ID TEXT, Cost_Tracking_ID TEXT PRIMARY KEY, Customer TEXT NOT NULL,
            Project_Name TEXT NOT NULL, Product_Line TEXT NOT NULL, Platform_Line TEXT NOT NULL,
            Budget_Hours REAL NOT NULL, Sales_Estimated_Hours REAL NOT NULL, Owner TEXT,
            Status TEXT NOT NULL DEFAULT 'Active', Created_At TEXT, Updated_At TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS daily_worklog(
            Worklog_ID TEXT PRIMARY KEY, Work_Date TEXT NOT NULL, Report_Week TEXT NOT NULL,
            Staff_Name TEXT NOT NULL, Department TEXT NOT NULL, Cost_Tracking_ID TEXT NOT NULL,
            Work_Category TEXT NOT NULL, Hours REAL NOT NULL, Work_Content TEXT NOT NULL,
            Product_Line TEXT, Platform_Line TEXT, Created_At TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS weekly_summary_input(
            Weekly_Input_ID TEXT PRIMARY KEY, Report_Week TEXT NOT NULL, Staff_Name TEXT NOT NULL,
            Cost_Tracking_ID TEXT NOT NULL, Weekly_Summary TEXT NOT NULL, Next_Week_Target TEXT NOT NULL,
            Health TEXT NOT NULL, Created_At TEXT, Updated_At TEXT,
            UNIQUE(Report_Week,Staff_Name,Cost_Tracking_ID))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS weekly_report_log(
            Report_Week TEXT NOT NULL, Staff_Name TEXT NOT NULL, Department TEXT NOT NULL,
            Cost_Tracking_ID TEXT NOT NULL, Customer TEXT, Project_Name TEXT, Product_Line TEXT,
            Platform_Line TEXT, Weekly_Total_Hours REAL, Daily_Work_Detail TEXT, Work_Category_Summary TEXT,
            Weekly_Summary TEXT, Next_Week_Target TEXT, Health TEXT, Submit_Status TEXT, Updated_At TEXT,
            PRIMARY KEY(Report_Week,Staff_Name,Cost_Tracking_ID))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS user_master(
            User_Email TEXT PRIMARY KEY, Staff_Name TEXT, Department TEXT, Role TEXT NOT NULL,
            Active_Flag INTEGER DEFAULT 1, Created_At TEXT, Updated_At TEXT)""")
        cur.execute("""CREATE TABLE IF NOT EXISTS role_permission(
            Role TEXT NOT NULL, Page_Name TEXT NOT NULL, Can_View INTEGER DEFAULT 0,
            Can_Edit INTEGER DEFAULT 0, Can_Export INTEGER DEFAULT 0, PRIMARY KEY(Role,Page_Name))""")
        cur.execute("""CREATE TABLE IF NOT EXISTS audit_log(
            Audit_ID TEXT PRIMARY KEY, User_Email TEXT, Action_Type TEXT, Table_Name TEXT,
            Record_Key TEXT, Old_Value TEXT, New_Value TEXT, Created_At TEXT)""")
        for table, defs in {
            "project_budget_master":["Created_By TEXT","Updated_By TEXT"],
            "daily_worklog":["Created_By TEXT"],
            "weekly_summary_input":["Created_By TEXT","Updated_By TEXT"],
        }.items():
            for d in defs: add_col(c, table, d)
        c.commit()
    seed_master_data(); seed_project_budget_master(); seed_users_permissions()

def seed_master_data():
    with conn() as c:
        if c.execute("SELECT COUNT(*) FROM staff_master").fetchone()[0] == 0:
            c.executemany("INSERT INTO staff_master VALUES(?,?,?,?)", STAFF_SEED)
        c.execute("UPDATE staff_master SET Role='PD/PM' WHERE Role='Sales'")
        for lt, vals in MASTER_LIST_SEED.items():
            for v in vals:
                c.execute("INSERT OR IGNORE INTO master_lists VALUES(?,?,1)", [lt, v])
        c.execute("UPDATE master_lists SET List_Value='PD/PM' WHERE List_Type='Role' AND List_Value='Sales'")
        c.commit()

def seed_project_budget_master():
    with conn() as c:
        if c.execute("SELECT COUNT(*) FROM project_budget_master").fetchone()[0] > 0: return
        products = [r[0] for r in c.execute("SELECT List_Value FROM master_lists WHERE List_Type='Product_Line'").fetchall()]
        platforms = [r[0] for r in c.execute("SELECT List_Value FROM master_lists WHERE List_Type='Platform_Line'").fetchall()]
        owners = [r[0] for r in c.execute("SELECT Staff_Name FROM staff_master WHERE Role='PD/PM' AND Active_Flag=1").fetchall()] or ["鈴木"]
        rows=[]
        for i,cid in enumerate(DEFAULT_COST_IDS,1):
            b=random.choice([50,100,150,200,300])
            rows.append((f"OPP-2026-{i:03d}",cid,f"DEMO Customer {chr(64+i)}",f"DEMO Project {cid}",
                         random.choice(products),random.choice(platforms),b,round(b*random.uniform(.8,1.2),1),
                         random.choice(owners),"Active",now(),now(),"system","system"))
        c.executemany("""INSERT INTO project_budget_master(
            Opportunity_ID,Cost_Tracking_ID,Customer,Project_Name,Product_Line,Platform_Line,
            Budget_Hours,Sales_Estimated_Hours,Owner,Status,Created_At,Updated_At,Created_By,Updated_By)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
        c.commit()

def seed_users_permissions():
    n=now()
    with conn() as c:
        c.execute("UPDATE user_master SET Role='PD/PM' WHERE Role='Sales'")
        for u in DEFAULT_USERS:
            c.execute("""INSERT OR IGNORE INTO user_master(User_Email,Staff_Name,Department,Role,Active_Flag,Created_At,Updated_At)
                         VALUES(?,?,?,?,?,?,?)""", [*u,n,n])
        c.execute("DELETE FROM role_permission")
        p = {
            "Admin": {pg:(1,1,1) for pg in PAGE_ORDER},
            "Manager": {"日報輸入":(1,1,0),"週報輸入":(1,1,0),"自由彙整":(1,0,1),"自動彙整 Dashboard":(1,0,1),"缺漏週報":(1,0,1),"匯出 Excel":(1,0,1)},
            "Staff": {"日報輸入":(1,1,0),"週報輸入":(1,1,0),"自由彙整":(1,0,1),"自動彙整 Dashboard":(1,0,0),"缺漏週報":(1,0,0),"匯出 Excel":(1,0,1)},
            "PD/PM": {"預算設定":(1,1,1),"日報輸入":(1,1,0),"週報輸入":(1,1,0),"自由彙整":(1,0,1),"自動彙整 Dashboard":(1,0,1),"缺漏週報":(1,0,1),"匯出 Excel":(1,0,1)},
            "Viewer": {"自動彙整 Dashboard":(1,0,0)}
        }
        for role,pages in p.items():
            for pg,(v,e,x) in pages.items():
                c.execute("INSERT INTO role_permission VALUES(?,?,?,?,?)",[role,pg,v,e,x])
        c.commit()

def get_current_week(d=None):
    d = d or date.today()
    if isinstance(d,str): d=datetime.strptime(d,"%Y-%m-%d").date()
    iso=d.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"

def gen_id(prefix, table, col):
    y=datetime.now().year; pat=f"{prefix}-{y}-%"
    with conn() as c:
        r=c.execute(f"SELECT {col} FROM {table} WHERE {col} LIKE ? ORDER BY {col} DESC LIMIT 1",[pat]).fetchone()
    n=1 if not r else int(str(r[0]).split("-")[-1])+1
    return f"{prefix}-{y}-{n:06d}"

def audit(action, table, key, old="", new="", user="system"):
    execute("INSERT INTO audit_log VALUES(?,?,?,?,?,?,?,?)",
            [gen_id("AUD","audit_log","Audit_ID"),user,action,table,key,str(old),str(new),now()])

def master_values(t):
    df=qdf("SELECT List_Value FROM master_lists WHERE List_Type=? AND Active_Flag=1 ORDER BY List_Value",[t])
    return df["List_Value"].tolist() if not df.empty else []

def staff(active=True):
    sql="SELECT * FROM staff_master" + (" WHERE Active_Flag=1" if active else "") + " ORDER BY Staff_Name"
    return qdf(sql)

def users(active=True):
    sql="SELECT * FROM user_master" + (" WHERE Active_Flag=1" if active else "") + " ORDER BY Role,User_Email"
    return qdf(sql)

def user_by_email(email):
    df=qdf("SELECT * FROM user_master WHERE User_Email=? AND Active_Flag=1",[email])
    return None if df.empty else df.iloc[0].to_dict()

def allowed_pages(role):
    df=qdf("""SELECT Page_Name FROM role_permission WHERE Role=? AND Can_View=1
              ORDER BY CASE Page_Name WHEN '預算設定' THEN 1 WHEN '日報輸入' THEN 2 WHEN '週報輸入' THEN 3
              WHEN '自由彙整' THEN 4 WHEN '自動彙整 Dashboard' THEN 5 WHEN '缺漏週報' THEN 6
              WHEN '匯出 Excel' THEN 7 WHEN 'Master Data' THEN 8 WHEN 'User Management' THEN 9 ELSE 99 END""",[role])
    return df["Page_Name"].tolist() if not df.empty else []

def permission(role,page):
    df=qdf("SELECT Can_View,Can_Edit,Can_Export FROM role_permission WHERE Role=? AND Page_Name=?",[role,page])
    return {"Can_View":0,"Can_Edit":0,"Can_Export":0} if df.empty else {k:int(df.iloc[0][k]) for k in ["Can_View","Can_Edit","Can_Export"]}

def owned_cost_ids(staff_name):
    df=qdf("SELECT Cost_Tracking_ID FROM project_budget_master WHERE Owner=? ORDER BY Cost_Tracking_ID",[staff_name])
    return df["Cost_Tracking_ID"].tolist() if not df.empty else []

def scope_project(df,u):
    if df.empty or not u: return df
    if u["Role"] in ["Admin","Viewer","Manager","Staff"]: return df
    if u["Role"]=="PD/PM" and "Owner" in df.columns: return df[df["Owner"]==u["Staff_Name"]]
    return df.iloc[0:0]

def scope_weekly(df,u):
    if df.empty or not u: return df
    if u["Role"] in ["Admin","Viewer"]: return df
    if u["Role"]=="Manager" and "Department" in df.columns: return df[df["Department"]==u["Department"]]
    if u["Role"]=="Staff" and "Staff_Name" in df.columns: return df[df["Staff_Name"]==u["Staff_Name"]]
    if u["Role"]=="PD/PM" and "Cost_Tracking_ID" in df.columns:
        return df[df["Cost_Tracking_ID"].isin(owned_cost_ids(u["Staff_Name"]))]
    return df.iloc[0:0]

def active_cost_ids(u=None):
    df=qdf("SELECT Cost_Tracking_ID,Owner FROM project_budget_master WHERE Status='Active' ORDER BY Cost_Tracking_ID")
    if u: df=scope_project(df,u)
    return df["Cost_Tracking_ID"].tolist() if not df.empty else []

def project_budget_display(u=None): return scope_project(table("project_budget_master"),u) if u else table("project_budget_master")

def upsert_budget(r,u=None):
    if not r.get("Cost_Tracking_ID"): raise ValueError("Cost_Tracking_ID 不可為空。")
    if not r.get("Customer"): raise ValueError("Customer 不可為空。")
    if not r.get("Project_Name"): raise ValueError("Project_Name 不可為空。")
    if float(r.get("Budget_Hours") or 0)<=0: raise ValueError("Budget_Hours 必須大於 0。")
    user=u["User_Email"] if u else "system"; role=u["Role"] if u else "Admin"
    with conn() as c:
        ex=c.execute("SELECT * FROM project_budget_master WHERE Cost_Tracking_ID=?",[r["Cost_Tracking_ID"]]).fetchone()
        if role=="PD/PM":
            if ex and ex["Owner"]!=u["Staff_Name"]: raise PermissionError("PD/PM 只能修改自己 Owner 的 Cost_Tracking_ID。")
            r["Owner"]=u["Staff_Name"]
        sh = float(r.get("Sales_Estimated_Hours") or r["Budget_Hours"])
        if ex:
            c.execute("""UPDATE project_budget_master SET Opportunity_ID=?,Customer=?,Project_Name=?,Product_Line=?,Platform_Line=?,
                         Budget_Hours=?,Sales_Estimated_Hours=?,Owner=?,Status=?,Updated_At=?,Updated_By=? WHERE Cost_Tracking_ID=?""",
                      [r.get("Opportunity_ID"),r["Customer"],r["Project_Name"],r["Product_Line"],r["Platform_Line"],float(r["Budget_Hours"]),sh,r["Owner"],r["Status"],now(),user,r["Cost_Tracking_ID"]])
            act="UPDATE"
        else:
            c.execute("""INSERT INTO project_budget_master VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                      [r.get("Opportunity_ID"),r["Cost_Tracking_ID"],r["Customer"],r["Project_Name"],r["Product_Line"],r["Platform_Line"],float(r["Budget_Hours"]),sh,r["Owner"],r["Status"],now(),now(),user,user])
            act="INSERT"
        c.commit()
    audit(act,"project_budget_master",r["Cost_Tracking_ID"],"",r,user)

def add_daily(work_date, staff_name, cid, cat, hours, content, u=None):
    if u:
        if u["Role"]=="Staff" and staff_name!=u["Staff_Name"]: raise PermissionError("Staff 只能替自己輸入日報。")
        if u["Role"]=="Manager":
            sdf=qdf("SELECT Department FROM staff_master WHERE Staff_Name=?",[staff_name])
            if not sdf.empty and sdf.iloc[0]["Department"]!=u["Department"]: raise PermissionError("Manager 只能替本部門人員輸入資料。")
        if u["Role"]=="PD/PM" and cid not in owned_cost_ids(u["Staff_Name"]): raise PermissionError("PD/PM 只能對自己 Owner 的 Cost_Tracking_ID 輸入資料。")
    if float(hours)<=0: raise ValueError("工時不可為 0。")
    if not content.strip(): raise ValueError("簡短內容不可為空。")
    if len(content)>100: raise ValueError("簡短內容限制 100 字以內。")
    sdf=qdf("SELECT * FROM staff_master WHERE Staff_Name=?",[staff_name])
    pdf=qdf("SELECT * FROM project_budget_master WHERE Cost_Tracking_ID=?",[cid])
    if sdf.empty: raise ValueError("人員不存在。")
    if pdf.empty: raise ValueError("工番號不存在。")
    wd=work_date.strftime("%Y-%m-%d") if hasattr(work_date,"strftime") else str(work_date)
    rw=get_current_week(wd); wid=gen_id("WL","daily_worklog","Worklog_ID"); user=u["User_Email"] if u else "system"
    execute("""INSERT INTO daily_worklog(Worklog_ID,Work_Date,Report_Week,Staff_Name,Department,Cost_Tracking_ID,Work_Category,Hours,Work_Content,Product_Line,Platform_Line,Created_At,Created_By)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            [wid,wd,rw,staff_name,sdf.iloc[0]["Department"],cid,cat,float(hours),content.strip(),pdf.iloc[0]["Product_Line"],pdf.iloc[0]["Platform_Line"],now(),user])
    regen_weekly(rw,staff_name,cid); audit("INSERT","daily_worklog",wid,"",{"cid":cid,"hours":hours},user); return wid

def upsert_weekly(rw,staff_name,cid,summary,target,health,u=None):
    if u:
        if u["Role"]=="Staff" and staff_name!=u["Staff_Name"]: raise PermissionError("Staff 只能替自己輸入週報。")
        if u["Role"]=="PD/PM" and cid not in owned_cost_ids(u["Staff_Name"]): raise PermissionError("PD/PM 只能管理自己 Owner 的 Cost_Tracking_ID。")
    if not summary.strip() or not target.strip(): raise ValueError("本週總結與下週目標不可為空。")
    if len(summary)>500: raise ValueError("週報總結超過 500 字。")
    if len(target)>500: raise ValueError("下週目標超過 500 字。")
    user=u["User_Email"] if u else "system"; n=now()
    with conn() as c:
        ex=c.execute("SELECT Weekly_Input_ID FROM weekly_summary_input WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=?",[rw,staff_name,cid]).fetchone()
        if ex:
            wsi=ex[0]
            c.execute("UPDATE weekly_summary_input SET Weekly_Summary=?,Next_Week_Target=?,Health=?,Updated_At=?,Updated_By=? WHERE Weekly_Input_ID=?",
                      [summary.strip(),target.strip(),health,n,user,wsi]); act="UPDATE"
        else:
            wsi=gen_id("WSI","weekly_summary_input","Weekly_Input_ID")
            c.execute("""INSERT INTO weekly_summary_input VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                      [wsi,rw,staff_name,cid,summary.strip(),target.strip(),health,n,n,user,user]); act="INSERT"
        c.commit()
    regen_weekly(rw,staff_name,cid); audit(act,"weekly_summary_input",wsi,"",{"rw":rw,"cid":cid},user); return wsi

def regen_weekly(rw=None, staff_name=None, cid=None):
    wh=[]; p=[]
    if rw: wh.append("dw.Report_Week=?"); p.append(rw)
    if staff_name: wh.append("dw.Staff_Name=?"); p.append(staff_name)
    if cid: wh.append("dw.Cost_Tracking_ID=?"); p.append(cid)
    ws="WHERE "+" AND ".join(wh) if wh else ""
    base=qdf(f"""SELECT dw.Report_Week,dw.Staff_Name,dw.Department,dw.Cost_Tracking_ID,pb.Customer,pb.Project_Name,pb.Product_Line,pb.Platform_Line,SUM(dw.Hours) Weekly_Total_Hours
                 FROM daily_worklog dw LEFT JOIN project_budget_master pb ON dw.Cost_Tracking_ID=pb.Cost_Tracking_ID {ws}
                 GROUP BY dw.Report_Week,dw.Staff_Name,dw.Department,dw.Cost_Tracking_ID,pb.Customer,pb.Project_Name,pb.Product_Line,pb.Platform_Line""",p)
    with conn() as c:
        for _,r in base.iterrows():
            det=qdf("""SELECT Work_Date,Work_Category,Hours,Work_Content FROM daily_worklog WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=? ORDER BY Work_Date,Created_At""",[r.Report_Week,r.Staff_Name,r.Cost_Tracking_ID])
            detail="\n".join([f"{x.Work_Date} | {x.Work_Category} | {x.Hours}h | {x.Work_Content}" for _,x in det.iterrows()])
            cat=qdf("""SELECT Work_Category,SUM(Hours) Hours FROM daily_worklog WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=? GROUP BY Work_Category""",[r.Report_Week,r.Staff_Name,r.Cost_Tracking_ID])
            cats=" / ".join([f"{x.Work_Category}: {x.Hours}h" for _,x in cat.iterrows()])
            summ=qdf("""SELECT Weekly_Summary,Next_Week_Target,Health FROM weekly_summary_input WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=?""",[r.Report_Week,r.Staff_Name,r.Cost_Tracking_ID])
            if summ.empty: s=t=h=""; status="Missing Summary"
            else: s=summ.iloc[0]["Weekly_Summary"]; t=summ.iloc[0]["Next_Week_Target"]; h=summ.iloc[0]["Health"]; status="Submitted"
            c.execute("""INSERT INTO weekly_report_log VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                         ON CONFLICT(Report_Week,Staff_Name,Cost_Tracking_ID) DO UPDATE SET
                         Department=excluded.Department,Customer=excluded.Customer,Project_Name=excluded.Project_Name,Product_Line=excluded.Product_Line,Platform_Line=excluded.Platform_Line,
                         Weekly_Total_Hours=excluded.Weekly_Total_Hours,Daily_Work_Detail=excluded.Daily_Work_Detail,Work_Category_Summary=excluded.Work_Category_Summary,
                         Weekly_Summary=excluded.Weekly_Summary,Next_Week_Target=excluded.Next_Week_Target,Health=excluded.Health,Submit_Status=excluded.Submit_Status,Updated_At=excluded.Updated_At""",
                      [r.Report_Week,r.Staff_Name,r.Department,r.Cost_Tracking_ID,r.Customer,r.Project_Name,r.Product_Line,r.Platform_Line,float(r.Weekly_Total_Hours or 0),detail,cats,s,t,h,status,now()])
        c.commit()

def rebuild_weekly():
    execute("DELETE FROM weekly_report_log"); regen_weekly()

def week_options():
    df=qdf("SELECT Report_Week FROM daily_worklog UNION SELECT Report_Week FROM weekly_summary_input ORDER BY Report_Week DESC")
    opts=df["Report_Week"].tolist() if not df.empty else []
    cw=get_current_week()
    if cw not in opts: opts.insert(0,cw)
    return opts

def cost_ids_for_staff_week(staff_name,rw,u=None):
    df=qdf("""SELECT DISTINCT dw.Cost_Tracking_ID,pb.Owner FROM daily_worklog dw LEFT JOIN project_budget_master pb ON dw.Cost_Tracking_ID=pb.Cost_Tracking_ID WHERE dw.Staff_Name=? AND dw.Report_Week=?""",[staff_name,rw])
    if u and u["Role"]=="PD/PM": df=df[df["Owner"]==u["Staff_Name"]]
    ids=df["Cost_Tracking_ID"].tolist() if not df.empty else []
    return ids or active_cost_ids(u)

def health(rate):
    return "Green" if rate<.5 else "Yellow" if rate<=1 else "Red" if rate<=1.5 else "Critical" if rate<=2 else "Overrun"

def project_summary(rw=None,u=None):
    rw=rw or get_current_week()
    df=qdf("""SELECT pb.Cost_Tracking_ID,pb.Customer,pb.Project_Name,pb.Product_Line,pb.Platform_Line,pb.Budget_Hours,pb.Sales_Estimated_Hours,
              COALESCE(SUM(CASE WHEN dw.Report_Week=? THEN dw.Hours ELSE 0 END),0) Weekly_Hours,
              COALESCE(SUM(dw.Hours),0) Cumulative_Hours,pb.Owner,pb.Status
              FROM project_budget_master pb LEFT JOIN daily_worklog dw ON pb.Cost_Tracking_ID=dw.Cost_Tracking_ID
              GROUP BY pb.Cost_Tracking_ID,pb.Customer,pb.Project_Name,pb.Product_Line,pb.Platform_Line,pb.Budget_Hours,pb.Sales_Estimated_Hours,pb.Owner,pb.Status ORDER BY pb.Cost_Tracking_ID""",[rw])
    df=scope_project(df,u) if u else df
    if df.empty: return df
    df["Remaining_Hours"]=df["Budget_Hours"]-df["Cumulative_Hours"]
    df["Budget_Burn_Rate"]=df.apply(lambda r:r.Cumulative_Hours/r.Budget_Hours if r.Budget_Hours else 0,axis=1)
    df["Sales_Estimate_Burn_Rate"]=df.apply(lambda r:r.Cumulative_Hours/r.Sales_Estimated_Hours if r.Sales_Estimated_Hours else 0,axis=1)
    df["Budget_Health"]=df["Budget_Burn_Rate"].apply(health)
    return df

def staff_weekly_summary(u=None):
    df=qdf("""SELECT Report_Week,Staff_Name,Department,SUM(Weekly_Total_Hours) Total_Weekly_Hours,COUNT(DISTINCT Cost_Tracking_ID) Number_of_Cost_IDs,
              SUM(CASE WHEN Submit_Status='Missing Summary' THEN 1 ELSE 0 END) Missing_Summary_Count
              FROM weekly_report_log GROUP BY Report_Week,Staff_Name,Department ORDER BY Report_Week DESC,Staff_Name""")
    return scope_weekly(df,u) if u else df

def missing_summary(u=None):
    df=qdf("""SELECT Report_Week,Staff_Name,Department,Cost_Tracking_ID,Customer,Project_Name,Weekly_Total_Hours,'Weekly Summary' Missing_Item,'Not Sent' Reminder_Status
              FROM weekly_report_log WHERE Submit_Status='Missing Summary' ORDER BY Report_Week DESC,Staff_Name,Cost_Tracking_ID""")
    return scope_weekly(df,u) if u else df

def weekly_filtered(start=None,end=None,dept=None,staff_name=None,cid=None,u=None):
    wh=[]; p=[]
    if start: wh.append("Report_Week>=?"); p.append(start)
    if end: wh.append("Report_Week<=?"); p.append(end)
    if dept and dept!="ALL": wh.append("Department=?"); p.append(dept)
    if staff_name and staff_name!="ALL": wh.append("Staff_Name=?"); p.append(staff_name)
    if cid and cid!="ALL": wh.append("Cost_Tracking_ID=?"); p.append(cid)
    ws="WHERE "+" AND ".join(wh) if wh else ""
    df=qdf(f"""SELECT Report_Week,Staff_Name,Department,Cost_Tracking_ID,Customer,Project_Name,Product_Line,Platform_Line,Weekly_Total_Hours,Weekly_Summary,Next_Week_Target,Health,Submit_Status
              FROM weekly_report_log {ws} ORDER BY Report_Week DESC,Staff_Name,Cost_Tracking_ID""",p)
    return scope_weekly(df,u) if u else df

def table(name):
    allowed={"project_budget_master","staff_master","daily_worklog","weekly_summary_input","weekly_report_log","master_lists","user_master","role_permission","audit_log"}
    if name not in allowed: raise ValueError("Unsupported table")
    return qdf(f"SELECT * FROM {name}")

def add_master_value(lt,val,u=None):
    if not lt or not val: raise ValueError("List_Type 與 List_Value 不可為空。")
    execute("INSERT OR IGNORE INTO master_lists VALUES(?,?,1)",[lt,val.strip()])
    audit("INSERT_OR_IGNORE","master_lists",f"{lt}:{val}","","",u["User_Email"] if u else "system")

def upsert_staff(staff_name,dept,role="Engineer",active=1,u=None):
    if not staff_name or not dept: raise ValueError("Staff_Name 與 Department 不可為空。")
    execute("""INSERT INTO staff_master VALUES(?,?,?,?) ON CONFLICT(Staff_Name) DO UPDATE SET Department=excluded.Department,Role=excluded.Role,Active_Flag=excluded.Active_Flag""",
            [staff_name.strip(),dept,role,int(active)])
    audit("UPSERT","staff_master",staff_name,"","",u["User_Email"] if u else "system")

def upsert_user(email,staff_name,dept,role,active=1,u=None):
    if not email: raise ValueError("User_Email 不可為空。")
    if role not in ["Admin","Manager","Staff","PD/PM","Viewer"]: raise ValueError("Role 必須是 Admin / Manager / Staff / PD/PM / Viewer。")
    n=now()
    execute("""INSERT INTO user_master VALUES(?,?,?,?,?,?,?) ON CONFLICT(User_Email) DO UPDATE SET Staff_Name=excluded.Staff_Name,Department=excluded.Department,Role=excluded.Role,Active_Flag=excluded.Active_Flag,Updated_At=excluded.Updated_At""",
            [email.strip(),staff_name,dept,role,int(active),n,n])
    audit("UPSERT","user_master",email,"",{"role":role},u["User_Email"] if u else "system")


# -----------------------------
# Admin Data Maintenance helpers
# -----------------------------

def _admin_only(u):
    if not u or u.get("Role") != "Admin":
        raise PermissionError("只有 Admin 可以執行後台資料維護。")

def get_daily_worklog_by_id(worklog_id):
    df = qdf("SELECT * FROM daily_worklog WHERE Worklog_ID=?", [worklog_id])
    return None if df.empty else df.iloc[0].to_dict()

def get_weekly_summary_by_id(weekly_input_id):
    df = qdf("SELECT * FROM weekly_summary_input WHERE Weekly_Input_ID=?", [weekly_input_id])
    return None if df.empty else df.iloc[0].to_dict()

def update_daily_worklog(worklog_id, work_date, staff_name, cid, cat, hours, content, u=None):
    _admin_only(u)
    old = get_daily_worklog_by_id(worklog_id)
    if not old:
        raise ValueError("找不到指定 Worklog_ID。")
    if not staff_name:
        raise ValueError("Staff_Name 不可為空。")
    if not cid:
        raise ValueError("Cost_Tracking_ID 不可為空。")
    if float(hours) <= 0:
        raise ValueError("工時不可為 0。")
    if float(hours) < 0.5 or float(hours) > 24:
        raise ValueError("工時必須介於 0.5 到 24 小時。")
    if not content or not content.strip():
        raise ValueError("Work_Content 不可為空。")
    if len(content) > 100:
        raise ValueError("Work_Content 限制 100 字以內。")

    sdf = qdf("SELECT * FROM staff_master WHERE Staff_Name=?", [staff_name])
    pdf = qdf("SELECT * FROM project_budget_master WHERE Cost_Tracking_ID=?", [cid])
    if sdf.empty:
        raise ValueError("人員不存在。")
    if pdf.empty:
        raise ValueError("工番號不存在。")

    wd = work_date.strftime("%Y-%m-%d") if hasattr(work_date, "strftime") else str(work_date)
    rw = get_current_week(wd)
    user = u["User_Email"] if u else "system"

    execute("""UPDATE daily_worklog
               SET Work_Date=?, Report_Week=?, Staff_Name=?, Department=?, Cost_Tracking_ID=?,
                   Work_Category=?, Hours=?, Work_Content=?, Product_Line=?, Platform_Line=?
               WHERE Worklog_ID=?""",
            [wd, rw, staff_name, sdf.iloc[0]["Department"], cid,
             cat, float(hours), content.strip(), pdf.iloc[0]["Product_Line"], pdf.iloc[0]["Platform_Line"],
             worklog_id])

    rebuild_weekly()
    audit("ADMIN_UPDATE", "daily_worklog", worklog_id, old, {
        "Work_Date": wd,
        "Report_Week": rw,
        "Staff_Name": staff_name,
        "Cost_Tracking_ID": cid,
        "Work_Category": cat,
        "Hours": hours,
        "Work_Content": content.strip(),
    }, user)

def delete_daily_worklog(worklog_id, u=None):
    _admin_only(u)
    old = get_daily_worklog_by_id(worklog_id)
    if not old:
        raise ValueError("找不到指定 Worklog_ID。")
    user = u["User_Email"] if u else "system"
    execute("DELETE FROM daily_worklog WHERE Worklog_ID=?", [worklog_id])
    rebuild_weekly()
    audit("ADMIN_DELETE", "daily_worklog", worklog_id, old, "", user)

def update_weekly_summary_input(weekly_input_id, report_week, staff_name, cid, summary, target, health_value, u=None):
    _admin_only(u)
    old = get_weekly_summary_by_id(weekly_input_id)
    if not old:
        raise ValueError("找不到指定 Weekly_Input_ID。")
    if not report_week:
        raise ValueError("Report_Week 不可為空。")
    if not staff_name:
        raise ValueError("Staff_Name 不可為空。")
    if not cid:
        raise ValueError("Cost_Tracking_ID 不可為空。")
    if not summary or not summary.strip():
        raise ValueError("Weekly_Summary 不可為空。")
    if not target or not target.strip():
        raise ValueError("Next_Week_Target 不可為空。")
    if len(summary) > 500:
        raise ValueError("Weekly_Summary 超過 500 字。")
    if len(target) > 500:
        raise ValueError("Next_Week_Target 超過 500 字。")

    user = u["User_Email"] if u else "system"
    n = now()

    # Avoid duplicate unique key conflict if Admin changes week/staff/cost id.
    dup = qdf("""SELECT Weekly_Input_ID FROM weekly_summary_input
                 WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=? AND Weekly_Input_ID<>?""",
              [report_week, staff_name, cid, weekly_input_id])
    if not dup.empty:
        raise ValueError("相同 Report_Week + Staff_Name + Cost_Tracking_ID 的週報已存在，無法更新成重複組合。")

    execute("""UPDATE weekly_summary_input
               SET Report_Week=?, Staff_Name=?, Cost_Tracking_ID=?, Weekly_Summary=?,
                   Next_Week_Target=?, Health=?, Updated_At=?, Updated_By=?
               WHERE Weekly_Input_ID=?""",
            [report_week, staff_name, cid, summary.strip(), target.strip(), health_value, n, user, weekly_input_id])

    rebuild_weekly()
    audit("ADMIN_UPDATE", "weekly_summary_input", weekly_input_id, old, {
        "Report_Week": report_week,
        "Staff_Name": staff_name,
        "Cost_Tracking_ID": cid,
        "Weekly_Summary": summary.strip(),
        "Next_Week_Target": target.strip(),
        "Health": health_value,
    }, user)

def delete_weekly_summary_input(weekly_input_id, u=None):
    _admin_only(u)
    old = get_weekly_summary_by_id(weekly_input_id)
    if not old:
        raise ValueError("找不到指定 Weekly_Input_ID。")
    user = u["User_Email"] if u else "system"
    execute("DELETE FROM weekly_summary_input WHERE Weekly_Input_ID=?", [weekly_input_id])
    rebuild_weekly()
    audit("ADMIN_DELETE", "weekly_summary_input", weekly_input_id, old, "", user)
