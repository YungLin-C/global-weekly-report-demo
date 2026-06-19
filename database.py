import sqlite3
from pathlib import Path
from datetime import datetime, date
import random
import pandas as pd

DB_NAME = "global_weekly_report_demo.db"
DB_PATH = Path(__file__).parent / DB_NAME


STAFF_SEED = [
    ("小李", "機械設計", "Engineer", 1),
    ("張三", "電氣", "Engineer", 1),
    ("王四", "組立", "Engineer", 1),
    ("JOHN", "CS", "Engineer", 1),
    ("鈴木", "營業", "Sales", 1),
    ("大島", "機械設計", "Engineer", 1),
    ("MIKE", "電氣", "Engineer", 1),
    ("MERRY", "組立", "Engineer", 1),
    ("MAX", "CS", "Engineer", 1),
    ("JAME", "營業", "Sales", 1),
    ("大河", "機械設計", "Engineer", 1),
    ("吾郎", "電氣", "Engineer", 1),
    ("人傑", "組立", "Engineer", 1),
    ("大勇", "CS", "Engineer", 1),
]

MASTER_LIST_SEED = {
    "Department": ["機械設計", "電氣", "組立", "CS", "營業"],
    "Product_Line": ["OWLS-1800", "OWLS-2200", "OCSS-600", "OTFC-1800", "T"],
    "Platform_Line": ["機械設計", "電氣", "組立", "CS", "營業"],
    "Work_Category": ["定例會議", "資料彙整", "設計", "組立", "調適", "現場異常", "異常分析"],
    "Health": ["Green", "Yellow", "Red"],
    "Status": ["Active", "Hold", "Closed"],
}

DEFAULT_COST_IDS = ["W0001", "W0002", "W0003", "W0004", "A0011", "A0012"]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def execute(sql, params=None):
    with get_connection() as conn:
        conn.execute(sql, params or [])
        conn.commit()


def query_df(sql, params=None):
    with get_connection() as conn:
        return pd.read_sql_query(sql, conn, params=params or [])


def init_db():
    with get_connection() as conn:
        c = conn.cursor()

        c.execute("""
        CREATE TABLE IF NOT EXISTS staff_master (
            Staff_Name TEXT PRIMARY KEY,
            Department TEXT NOT NULL,
            Role TEXT,
            Active_Flag INTEGER DEFAULT 1
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS master_lists (
            List_Type TEXT NOT NULL,
            List_Value TEXT NOT NULL,
            Active_Flag INTEGER DEFAULT 1,
            PRIMARY KEY (List_Type, List_Value)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS project_budget_master (
            Opportunity_ID TEXT,
            Cost_Tracking_ID TEXT PRIMARY KEY,
            Customer TEXT NOT NULL,
            Project_Name TEXT NOT NULL,
            Product_Line TEXT NOT NULL,
            Platform_Line TEXT NOT NULL,
            Budget_Hours REAL NOT NULL,
            Sales_Estimated_Hours REAL NOT NULL,
            Owner TEXT,
            Status TEXT NOT NULL DEFAULT 'Active',
            Created_At TEXT,
            Updated_At TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS daily_worklog (
            Worklog_ID TEXT PRIMARY KEY,
            Work_Date TEXT NOT NULL,
            Report_Week TEXT NOT NULL,
            Staff_Name TEXT NOT NULL,
            Department TEXT NOT NULL,
            Cost_Tracking_ID TEXT NOT NULL,
            Work_Category TEXT NOT NULL,
            Hours REAL NOT NULL,
            Work_Content TEXT NOT NULL,
            Product_Line TEXT,
            Platform_Line TEXT,
            Created_At TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_summary_input (
            Weekly_Input_ID TEXT PRIMARY KEY,
            Report_Week TEXT NOT NULL,
            Staff_Name TEXT NOT NULL,
            Cost_Tracking_ID TEXT NOT NULL,
            Weekly_Summary TEXT NOT NULL,
            Next_Week_Target TEXT NOT NULL,
            Health TEXT NOT NULL,
            Created_At TEXT,
            Updated_At TEXT,
            UNIQUE (Report_Week, Staff_Name, Cost_Tracking_ID)
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS weekly_report_log (
            Report_Week TEXT NOT NULL,
            Staff_Name TEXT NOT NULL,
            Department TEXT NOT NULL,
            Cost_Tracking_ID TEXT NOT NULL,
            Customer TEXT,
            Project_Name TEXT,
            Product_Line TEXT,
            Platform_Line TEXT,
            Weekly_Total_Hours REAL,
            Daily_Work_Detail TEXT,
            Work_Category_Summary TEXT,
            Weekly_Summary TEXT,
            Next_Week_Target TEXT,
            Health TEXT,
            Submit_Status TEXT,
            Updated_At TEXT,
            PRIMARY KEY (Report_Week, Staff_Name, Cost_Tracking_ID)
        )
        """)

        conn.commit()

    seed_master_data()
    seed_project_budget_master()


def seed_master_data():
    with get_connection() as conn:
        c = conn.cursor()

        staff_count = c.execute("SELECT COUNT(*) FROM staff_master").fetchone()[0]
        if staff_count == 0:
            c.executemany("""
                INSERT INTO staff_master (Staff_Name, Department, Role, Active_Flag)
                VALUES (?, ?, ?, ?)
            """, STAFF_SEED)

        list_count = c.execute("SELECT COUNT(*) FROM master_lists").fetchone()[0]
        if list_count == 0:
            rows = []
            for list_type, values in MASTER_LIST_SEED.items():
                for value in values:
                    rows.append((list_type, value, 1))
            c.executemany("""
                INSERT INTO master_lists (List_Type, List_Value, Active_Flag)
                VALUES (?, ?, ?)
            """, rows)

        conn.commit()


def seed_project_budget_master():
    with get_connection() as conn:
        c = conn.cursor()
        count = c.execute("SELECT COUNT(*) FROM project_budget_master").fetchone()[0]
        if count > 0:
            return

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        customers = [f"DEMO Customer {x}" for x in ["A", "B", "C", "D", "E", "F"]]
        product_lines = [r[0] for r in c.execute(
            "SELECT List_Value FROM master_lists WHERE List_Type='Product_Line' AND Active_Flag=1"
        ).fetchall()]
        platform_lines = [r[0] for r in c.execute(
            "SELECT List_Value FROM master_lists WHERE List_Type='Platform_Line' AND Active_Flag=1"
        ).fetchall()]
        staff_names = [r[0] for r in c.execute(
            "SELECT Staff_Name FROM staff_master WHERE Active_Flag=1"
        ).fetchall()]
        budget_options = [50, 100, 150, 200, 300]

        rows = []
        for idx, cost_id in enumerate(DEFAULT_COST_IDS, start=1):
            budget = random.choice(budget_options)
            sales_est = round(budget * random.uniform(0.8, 1.2), 1)
            rows.append((
                f"OPP-2026-{idx:03d}",
                cost_id,
                random.choice(customers),
                f"DEMO Project {cost_id}",
                random.choice(product_lines),
                random.choice(platform_lines),
                budget,
                sales_est,
                random.choice(staff_names),
                "Active",
                now,
                now,
            ))

        c.executemany("""
            INSERT INTO project_budget_master (
                Opportunity_ID, Cost_Tracking_ID, Customer, Project_Name,
                Product_Line, Platform_Line, Budget_Hours, Sales_Estimated_Hours,
                Owner, Status, Created_At, Updated_At
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
        conn.commit()


def get_master_values(list_type):
    return query_df(
        "SELECT List_Value FROM master_lists WHERE List_Type=? AND Active_Flag=1 ORDER BY List_Value",
        [list_type],
    )["List_Value"].tolist()


def get_staff(active_only=True):
    sql = "SELECT * FROM staff_master"
    if active_only:
        sql += " WHERE Active_Flag=1"
    sql += " ORDER BY Staff_Name"
    return query_df(sql)


def get_active_cost_ids():
    return query_df("""
        SELECT Cost_Tracking_ID
        FROM project_budget_master
        WHERE Status='Active'
        ORDER BY Cost_Tracking_ID
    """)["Cost_Tracking_ID"].tolist()


def get_current_week(input_date=None):
    if input_date is None:
        input_date = date.today()
    if isinstance(input_date, str):
        input_date = datetime.strptime(input_date, "%Y-%m-%d").date()
    iso = input_date.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_id(prefix, table_name, id_col):
    year = datetime.now().year
    pattern = f"{prefix}-{year}-%"
    with get_connection() as conn:
        row = conn.execute(
            f"SELECT {id_col} FROM {table_name} WHERE {id_col} LIKE ? ORDER BY {id_col} DESC LIMIT 1",
            [pattern],
        ).fetchone()

    if row is None:
        next_num = 1
    else:
        try:
            next_num = int(row[0].split("-")[-1]) + 1
        except Exception:
            next_num = 1

    return f"{prefix}-{year}-{next_num:06d}"


def validate_budget_record(record, is_update=False):
    errors = []
    if not record.get("Cost_Tracking_ID"):
        errors.append("Cost_Tracking_ID 不可為空。")
    if not record.get("Customer"):
        errors.append("Customer 不可為空。")
    if not record.get("Project_Name"):
        errors.append("Project_Name 不可為空。")
    if float(record.get("Budget_Hours") or 0) <= 0:
        errors.append("Budget_Hours 必須大於 0。")
    return errors


def upsert_project_budget(record):
    errors = validate_budget_record(record)
    if errors:
        raise ValueError("\n".join(errors))

    sales_hours = record.get("Sales_Estimated_Hours")
    if sales_hours is None or sales_hours == "":
        sales_hours = record["Budget_Hours"]

    now = get_now()
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT Cost_Tracking_ID FROM project_budget_master WHERE Cost_Tracking_ID=?",
            [record["Cost_Tracking_ID"]],
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE project_budget_master
                SET Opportunity_ID=?, Customer=?, Project_Name=?, Product_Line=?, Platform_Line=?,
                    Budget_Hours=?, Sales_Estimated_Hours=?, Owner=?, Status=?, Updated_At=?
                WHERE Cost_Tracking_ID=?
            """, [
                record.get("Opportunity_ID"),
                record["Customer"],
                record["Project_Name"],
                record["Product_Line"],
                record["Platform_Line"],
                float(record["Budget_Hours"]),
                float(sales_hours),
                record.get("Owner"),
                record["Status"],
                now,
                record["Cost_Tracking_ID"],
            ])
        else:
            conn.execute("""
                INSERT INTO project_budget_master (
                    Opportunity_ID, Cost_Tracking_ID, Customer, Project_Name, Product_Line,
                    Platform_Line, Budget_Hours, Sales_Estimated_Hours, Owner, Status,
                    Created_At, Updated_At
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                record.get("Opportunity_ID"),
                record["Cost_Tracking_ID"],
                record["Customer"],
                record["Project_Name"],
                record["Product_Line"],
                record["Platform_Line"],
                float(record["Budget_Hours"]),
                float(sales_hours),
                record.get("Owner"),
                record["Status"],
                now,
                now,
            ])
        conn.commit()


def add_daily_worklog(work_date, staff_name, cost_tracking_id, work_category, hours, work_content):
    if not staff_name:
        raise ValueError("人員不可為空。")
    if not cost_tracking_id:
        raise ValueError("工番號 / 依賴號不可為空。")
    if float(hours) <= 0:
        raise ValueError("工時不可為 0。")
    if float(hours) < 0.5 or float(hours) > 24:
        raise ValueError("工時必須介於 0.5 到 24 小時。")
    if not work_content or not work_content.strip():
        raise ValueError("簡短內容不可為空。")
    if len(work_content) > 100:
        raise ValueError("簡短內容建議限制 100 字以內，請縮短後再儲存。")

    staff = query_df("SELECT * FROM staff_master WHERE Staff_Name=?", [staff_name])
    if staff.empty:
        raise ValueError("人員不存在。")

    project = query_df("SELECT * FROM project_budget_master WHERE Cost_Tracking_ID=?", [cost_tracking_id])
    if project.empty:
        raise ValueError("工番號不存在。")

    if hasattr(work_date, "strftime"):
        work_date_str = work_date.strftime("%Y-%m-%d")
    else:
        work_date_str = str(work_date)

    report_week = get_current_week(work_date_str)
    worklog_id = generate_id("WL", "daily_worklog", "Worklog_ID")
    now = get_now()

    execute("""
        INSERT INTO daily_worklog (
            Worklog_ID, Work_Date, Report_Week, Staff_Name, Department,
            Cost_Tracking_ID, Work_Category, Hours, Work_Content,
            Product_Line, Platform_Line, Created_At
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, [
        worklog_id,
        work_date_str,
        report_week,
        staff_name,
        staff.iloc[0]["Department"],
        cost_tracking_id,
        work_category,
        float(hours),
        work_content.strip(),
        project.iloc[0]["Product_Line"],
        project.iloc[0]["Platform_Line"],
        now,
    ])

    regenerate_weekly_report_log(report_week=report_week, staff_name=staff_name, cost_tracking_id=cost_tracking_id)
    return worklog_id


def upsert_weekly_summary(report_week, staff_name, cost_tracking_id, weekly_summary, next_week_target, health):
    if not report_week:
        raise ValueError("週次不可為空。")
    if not staff_name:
        raise ValueError("人員不可為空。")
    if not cost_tracking_id:
        raise ValueError("工番號 / 依賴號不可為空。")
    if not weekly_summary or not weekly_summary.strip():
        raise ValueError("本週總結不可為空。")
    if not next_week_target or not next_week_target.strip():
        raise ValueError("下週目標不可為空。")
    if len(weekly_summary) > 500:
        raise ValueError("週報總結超過 500 字。")
    if len(next_week_target) > 500:
        raise ValueError("下週目標超過 500 字。")

    now = get_now()
    with get_connection() as conn:
        existing = conn.execute("""
            SELECT Weekly_Input_ID FROM weekly_summary_input
            WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=?
        """, [report_week, staff_name, cost_tracking_id]).fetchone()

        if existing:
            weekly_input_id = existing[0]
            conn.execute("""
                UPDATE weekly_summary_input
                SET Weekly_Summary=?, Next_Week_Target=?, Health=?, Updated_At=?
                WHERE Weekly_Input_ID=?
            """, [weekly_summary.strip(), next_week_target.strip(), health, now, weekly_input_id])
        else:
            weekly_input_id = generate_id("WSI", "weekly_summary_input", "Weekly_Input_ID")
            conn.execute("""
                INSERT INTO weekly_summary_input (
                    Weekly_Input_ID, Report_Week, Staff_Name, Cost_Tracking_ID,
                    Weekly_Summary, Next_Week_Target, Health, Created_At, Updated_At
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                weekly_input_id,
                report_week,
                staff_name,
                cost_tracking_id,
                weekly_summary.strip(),
                next_week_target.strip(),
                health,
                now,
                now,
            ])
        conn.commit()

    regenerate_weekly_report_log(report_week=report_week, staff_name=staff_name, cost_tracking_id=cost_tracking_id)
    return weekly_input_id


def regenerate_weekly_report_log(report_week=None, staff_name=None, cost_tracking_id=None):
    where = []
    params = []
    if report_week:
        where.append("dw.Report_Week=?")
        params.append(report_week)
    if staff_name:
        where.append("dw.Staff_Name=?")
        params.append(staff_name)
    if cost_tracking_id:
        where.append("dw.Cost_Tracking_ID=?")
        params.append(cost_tracking_id)

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    base = query_df(f"""
        SELECT
            dw.Report_Week,
            dw.Staff_Name,
            dw.Department,
            dw.Cost_Tracking_ID,
            pb.Customer,
            pb.Project_Name,
            pb.Product_Line,
            pb.Platform_Line,
            SUM(dw.Hours) AS Weekly_Total_Hours
        FROM daily_worklog dw
        LEFT JOIN project_budget_master pb
            ON dw.Cost_Tracking_ID = pb.Cost_Tracking_ID
        {where_sql}
        GROUP BY dw.Report_Week, dw.Staff_Name, dw.Department, dw.Cost_Tracking_ID,
                 pb.Customer, pb.Project_Name, pb.Product_Line, pb.Platform_Line
    """, params)

    now = get_now()

    with get_connection() as conn:
        for _, row in base.iterrows():
            rw = row["Report_Week"]
            sn = row["Staff_Name"]
            cid = row["Cost_Tracking_ID"]

            details_df = query_df("""
                SELECT Work_Date, Work_Category, Hours, Work_Content
                FROM daily_worklog
                WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=?
                ORDER BY Work_Date, Created_At
            """, [rw, sn, cid])

            detail_lines = []
            for _, d in details_df.iterrows():
                detail_lines.append(f'{d["Work_Date"]} | {d["Work_Category"]} | {d["Hours"]}h | {d["Work_Content"]}')
            daily_work_detail = "\n".join(detail_lines)

            cat_df = query_df("""
                SELECT Work_Category, SUM(Hours) AS Hours
                FROM daily_worklog
                WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=?
                GROUP BY Work_Category
                ORDER BY Work_Category
            """, [rw, sn, cid])
            cat_summary = " / ".join([f'{r["Work_Category"]}: {r["Hours"]}h' for _, r in cat_df.iterrows()])

            summary = query_df("""
                SELECT Weekly_Summary, Next_Week_Target, Health
                FROM weekly_summary_input
                WHERE Report_Week=? AND Staff_Name=? AND Cost_Tracking_ID=?
            """, [rw, sn, cid])

            if summary.empty:
                weekly_summary = ""
                next_week_target = ""
                health = ""
                submit_status = "Missing Summary"
            else:
                weekly_summary = summary.iloc[0]["Weekly_Summary"]
                next_week_target = summary.iloc[0]["Next_Week_Target"]
                health = summary.iloc[0]["Health"]
                submit_status = "Submitted"

            conn.execute("""
                INSERT INTO weekly_report_log (
                    Report_Week, Staff_Name, Department, Cost_Tracking_ID,
                    Customer, Project_Name, Product_Line, Platform_Line,
                    Weekly_Total_Hours, Daily_Work_Detail, Work_Category_Summary,
                    Weekly_Summary, Next_Week_Target, Health, Submit_Status, Updated_At
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(Report_Week, Staff_Name, Cost_Tracking_ID)
                DO UPDATE SET
                    Department=excluded.Department,
                    Customer=excluded.Customer,
                    Project_Name=excluded.Project_Name,
                    Product_Line=excluded.Product_Line,
                    Platform_Line=excluded.Platform_Line,
                    Weekly_Total_Hours=excluded.Weekly_Total_Hours,
                    Daily_Work_Detail=excluded.Daily_Work_Detail,
                    Work_Category_Summary=excluded.Work_Category_Summary,
                    Weekly_Summary=excluded.Weekly_Summary,
                    Next_Week_Target=excluded.Next_Week_Target,
                    Health=excluded.Health,
                    Submit_Status=excluded.Submit_Status,
                    Updated_At=excluded.Updated_At
            """, [
                rw, sn, row["Department"], cid,
                row["Customer"], row["Project_Name"], row["Product_Line"], row["Platform_Line"],
                float(row["Weekly_Total_Hours"] or 0), daily_work_detail, cat_summary,
                weekly_summary, next_week_target, health, submit_status, now
            ])

        conn.commit()


def rebuild_all_weekly_report_log():
    execute("DELETE FROM weekly_report_log")
    regenerate_weekly_report_log()


def get_week_options():
    weeks = query_df("""
        SELECT Report_Week FROM daily_worklog
        UNION
        SELECT Report_Week FROM weekly_summary_input
        ORDER BY Report_Week DESC
    """)
    options = weeks["Report_Week"].tolist() if not weeks.empty else []
    current = get_current_week()
    if current not in options:
        options.insert(0, current)
    return options


def get_cost_ids_for_staff_week(staff_name, report_week):
    df = query_df("""
        SELECT DISTINCT Cost_Tracking_ID
        FROM daily_worklog
        WHERE Staff_Name=? AND Report_Week=?
        ORDER BY Cost_Tracking_ID
    """, [staff_name, report_week])
    ids = df["Cost_Tracking_ID"].tolist() if not df.empty else []
    if ids:
        return ids
    return get_active_cost_ids()


def get_project_hour_summary(report_week=None):
    current_week = report_week or get_current_week()

    df = query_df("""
        SELECT
            pb.Cost_Tracking_ID,
            pb.Customer,
            pb.Project_Name,
            pb.Product_Line,
            pb.Platform_Line,
            pb.Budget_Hours,
            pb.Sales_Estimated_Hours,
            COALESCE(SUM(CASE WHEN dw.Report_Week=? THEN dw.Hours ELSE 0 END), 0) AS Weekly_Hours,
            COALESCE(SUM(dw.Hours), 0) AS Cumulative_Hours,
            pb.Owner,
            pb.Status
        FROM project_budget_master pb
        LEFT JOIN daily_worklog dw
            ON pb.Cost_Tracking_ID = dw.Cost_Tracking_ID
        GROUP BY
            pb.Cost_Tracking_ID, pb.Customer, pb.Project_Name, pb.Product_Line,
            pb.Platform_Line, pb.Budget_Hours, pb.Sales_Estimated_Hours,
            pb.Owner, pb.Status
        ORDER BY pb.Cost_Tracking_ID
    """, [current_week])

    if df.empty:
        return df

    df["Remaining_Hours"] = df["Budget_Hours"] - df["Cumulative_Hours"]
    df["Budget_Burn_Rate"] = df.apply(
        lambda r: r["Cumulative_Hours"] / r["Budget_Hours"] if r["Budget_Hours"] else 0, axis=1
    )
    df["Sales_Estimate_Burn_Rate"] = df.apply(
        lambda r: r["Cumulative_Hours"] / r["Sales_Estimated_Hours"] if r["Sales_Estimated_Hours"] else 0, axis=1
    )
    df["Budget_Health"] = df["Budget_Burn_Rate"].apply(get_budget_health)
    return df


def get_budget_health(rate):
    if rate < 0.5:
        return "Green"
    if rate <= 1.0:
        return "Yellow"
    if rate <= 1.5:
        return "Red"
    if rate <= 2.0:
        return "Critical"
    return "Overrun"


def get_staff_weekly_summary():
    weekly = query_df("""
        SELECT
            Report_Week,
            Staff_Name,
            Department,
            SUM(Weekly_Total_Hours) AS Total_Weekly_Hours,
            COUNT(DISTINCT Cost_Tracking_ID) AS Number_of_Cost_IDs,
            SUM(CASE WHEN Submit_Status='Missing Summary' THEN 1 ELSE 0 END) AS Missing_Summary_Count
        FROM weekly_report_log
        GROUP BY Report_Week, Staff_Name, Department
        ORDER BY Report_Week DESC, Staff_Name
    """)
    return weekly


def get_missing_weekly_summary():
    return query_df("""
        SELECT
            Report_Week,
            Staff_Name,
            Department,
            Cost_Tracking_ID,
            Customer,
            Project_Name,
            Weekly_Total_Hours,
            'Weekly Summary' AS Missing_Item,
            'Not Sent' AS Reminder_Status
        FROM weekly_report_log
        WHERE Submit_Status='Missing Summary'
        ORDER BY Report_Week DESC, Staff_Name, Cost_Tracking_ID
    """)


def get_dashboard_source():
    project = get_project_hour_summary()
    if project.empty:
        return project
    return project.copy()


def get_weekly_report_filtered(start_week=None, end_week=None, department=None, staff_name=None, cost_tracking_id=None):
    where = []
    params = []

    if start_week:
        where.append("Report_Week >= ?")
        params.append(start_week)
    if end_week:
        where.append("Report_Week <= ?")
        params.append(end_week)
    if department and department != "ALL":
        where.append("Department = ?")
        params.append(department)
    if staff_name and staff_name != "ALL":
        where.append("Staff_Name = ?")
        params.append(staff_name)
    if cost_tracking_id and cost_tracking_id != "ALL":
        where.append("Cost_Tracking_ID = ?")
        params.append(cost_tracking_id)

    where_sql = "WHERE " + " AND ".join(where) if where else ""

    return query_df(f"""
        SELECT
            Report_Week,
            Staff_Name,
            Department,
            Cost_Tracking_ID,
            Customer,
            Project_Name,
            Product_Line,
            Platform_Line,
            Weekly_Total_Hours,
            Weekly_Summary,
            Next_Week_Target,
            Health,
            Submit_Status
        FROM weekly_report_log
        {where_sql}
        ORDER BY Report_Week DESC, Staff_Name, Cost_Tracking_ID
    """, params)


def get_table(table_name):
    allowed = {
        "project_budget_master",
        "staff_master",
        "daily_worklog",
        "weekly_summary_input",
        "weekly_report_log",
        "master_lists",
    }
    if table_name not in allowed:
        raise ValueError("Unsupported table")
    return query_df(f"SELECT * FROM {table_name}")


def add_master_list_value(list_type, list_value):
    if not list_type or not list_value:
        raise ValueError("List_Type 與 List_Value 不可為空。")
    execute("""
        INSERT OR IGNORE INTO master_lists (List_Type, List_Value, Active_Flag)
        VALUES (?, ?, 1)
    """, [list_type, list_value.strip()])


def upsert_staff(staff_name, department, role="Engineer", active_flag=1):
    if not staff_name:
        raise ValueError("Staff_Name 不可為空。")
    if not department:
        raise ValueError("Department 不可為空。")
    execute("""
        INSERT INTO staff_master (Staff_Name, Department, Role, Active_Flag)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(Staff_Name)
        DO UPDATE SET Department=excluded.Department, Role=excluded.Role, Active_Flag=excluded.Active_Flag
    """, [staff_name.strip(), department, role, int(active_flag)])
