# GLOBAL Weekly Report Demo

GLOBAL Weekly Report Demo 是一套本機端 DEMO 用工時週報管理系統，用於展示：

1. 日報工時輸入
2. 週報總結與下週目標輸入
3. 依週次 / 部門 / 人員 / 工番號彙整查詢
4. 自動 Dashboard 彙整
5. 預算工時與營業評估工時管理
6. 缺漏週報追蹤
7. 完整 Excel workbook 匯出

本版為 Local Demo，不包含登入權限、多人同步編輯、雲端部署與審批流程。

---

## 1. 系統說明

系統使用以下技術：

- Python
- Streamlit
- SQLite
- pandas
- openpyxl

資料庫檔名：

```text
global_weekly_report_demo.db
```

第一次啟動時，系統會自動建立資料庫與 DEMO 初始資料。

---

## 2. 安裝方法

建議使用 Python 3.10 以上版本。

在專案資料夾內執行：

```bash
pip install -r requirements.txt
```

---

## 3. 執行方法

在專案資料夾內執行：

```bash
streamlit run app.py
```

系統會在瀏覽器中開啟 Streamlit 介面。

---

## 4. 初始化資料說明

第一次啟動時，若資料庫無資料，系統會自動建立：

### Staff_Master

預設人員：

- 小李
- 張三
- 王四
- JOHN
- 鈴木
- 大島
- MIKE
- MERRY
- MAX
- JAME
- 大河
- 吾郎
- 人傑
- 大勇

### Master Lists

包含：

- Department
- Product_Line
- Platform_Line
- Work_Category
- Health
- Status

### Project_Budget_Master

預設 Cost_Tracking_ID：

- W0001
- W0002
- W0003
- W0004
- A0011
- A0012

其他欄位會由系統隨機分配，例如：

- Customer
- Project_Name
- Product_Line
- Platform_Line
- Budget_Hours
- Sales_Estimated_Hours
- Owner
- Opportunity_ID

---

## 5. 操作流程

### Step 1：預算設定

進入「預算設定」頁面，確認或修改：

- Opportunity_ID
- Cost_Tracking_ID
- Customer
- Project_Name
- Product_Line
- Platform_Line
- Budget_Hours
- Sales_Estimated_Hours
- Owner
- Status

若 Cost_Tracking_ID 已存在，系統會更新原資料。

### Step 2：日報輸入

進入「日報輸入」頁面，每次輸入一筆日報：

- Work_Date
- Staff_Name
- Cost_Tracking_ID
- Work_Category
- Hours
- Work_Content

系統會自動產生：

- Worklog_ID
- Report_Week
- Department
- Product_Line
- Platform_Line
- Created_At

### Step 3：週報輸入

進入「週報輸入」頁面，針對每週、每人、每個 Cost_Tracking_ID 輸入：

- Weekly_Summary
- Next_Week_Target
- Health

同一個 `Report_Week + Staff_Name + Cost_Tracking_ID` 只會保留一筆。
重複提交時，系統會更新原紀錄。

### Step 4：自由彙整

進入「自由彙整」頁面，可以依以下條件查詢：

- Start_Week
- End_Week
- Department
- Staff_Name
- Cost_Tracking_ID

查詢結果可單獨匯出 Excel。

### Step 5：Dashboard

進入「自動彙整 Dashboard」頁面，可以查看：

- Active Cost_Tracking_ID 數
- 本週總工時
- 累計總工時
- Missing Weekly Summary 數
- 超過 Budget_Hours 的工番數
- Project Hour Summary
- Staff Weekly Summary
- Missing Weekly Summary

---

## 6. 如何匯出 Excel

進入「匯出 Excel」頁面，點選：

```text
下載完整 Excel Workbook
```

匯出檔名格式：

```text
GLOBAL_Weekly_Report_Demo_YYYYMMDD_HHMM.xlsx
```

Workbook 包含以下 Sheet：

1. Project_Budget_Master
2. Daily_Worklog
3. Weekly_Summary_Input
4. Weekly_Report_Log
5. Project_Hour_Summary
6. Staff_Weekly_Summary
7. Missing_Weekly_Summary
8. Dashboard_Source
9. Master_Lists

Excel 格式包含：

- 標題列加粗
- 自動欄寬
- 凍結首列
- 數字欄位格式
- Burn Rate 百分比格式

---

## 7. 檔案結構

```text
global_weekly_report_demo/
├─ app.py
├─ database.py
├─ export_excel.py
├─ requirements.txt
└─ README.md
```

執行後會自動產生：

```text
global_weekly_report_demo.db
```

---

## 8. 注意事項

- 本系統為 DEMO 版本，不建議直接用於正式多人協同環境。
- SQLite 適合本機端展示，不適合高併發多人同時寫入。
- 若要重新初始化 DEMO 資料，可關閉 Streamlit 後刪除 `global_weekly_report_demo.db`，再重新執行 `streamlit run app.py`。
