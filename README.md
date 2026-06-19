# GLOBAL Weekly Report Demo v3 - Excel Admin Config

GLOBAL Weekly Report Demo v3 是一套本機端 / Streamlit Cloud DEMO 用工時週報管理系統。

v3 在 v2 的基礎上追加：

```text
Admin Config Import / Export
```

Admin 可以用一個 Excel workbook 維護：

1. Staff_Master
2. User_Master
3. Role_Permission
4. Master_Lists

---

## 1. v3 新增功能

### Admin Config Excel

新增頁面：

```text
Admin Config Import / Export
```

使用者必須用 Admin 登入，例如：

```text
admin@demo.com
```

此頁面提供：

1. Export Current Admin Config
2. Upload Admin Config Excel
3. Validation Check
4. Apply Config to Database
5. Audit_Log 記錄匯入操作

---

## 2. Excel Workbook 結構

系統匯出的設定檔名稱類似：

```text
GLOBAL_Weekly_Report_Admin_Config_YYYYMMDD_HHMM.xlsx
```

包含以下 Sheet：

```text
Staff_Master
User_Master
Role_Permission
Master_Lists
Validation_Guide
```

---

## 3. Sheet 定義

### Staff_Master

| Staff_Name | Department | Role | Active_Flag |
|---|---|---|---|

說明：

```text
Staff_Name   人員名稱，主鍵
Department   部門，需存在於 Master_Lists 的 Department
Role         人員職務，例如 Engineer / PD/PM
Active_Flag  1=啟用，0=停用
```

### User_Master

| User_Email | Staff_Name | Department | Role | Active_Flag |
|---|---|---|---|---|

說明：

```text
User_Email   Demo Login 帳號，主鍵
Staff_Name   對應 Staff_Master
Department   權限範圍用部門
Role         系統角色：Admin / Manager / Staff / PD/PM / Viewer
Active_Flag  1=啟用，0=停用
```

### Role_Permission

| Role | Page_Name | Can_View | Can_Edit | Can_Export |
|---|---|---:|---:|---:|

說明：

```text
Role         系統角色
Page_Name    左側頁面名稱
Can_View     1=可見，0=不可見
Can_Edit     1=可編輯，0=不可編輯
Can_Export   1=可匯出，0=不可匯出
```

### Master_Lists

| List_Type | List_Value | Active_Flag |
|---|---|---:|

說明：

```text
List_Type     Department / Product_Line / Platform_Line / Work_Category / Health / Status / Role
List_Value    下拉選單值
Active_Flag   1=啟用，0=停用
```

---

## 4. 匯入規則

匯入前系統會檢查：

1. 必要 Sheet 是否存在
2. 必要欄位是否存在
3. 主鍵是否重複
4. Active_Flag / Can_View / Can_Edit / Can_Export 是否為 0 或 1
5. User_Master.Staff_Name 是否存在於 Staff_Master
6. User_Master.Department 是否存在於 Master_Lists Department
7. Role 是否為 Admin / Manager / Staff / PD/PM / Viewer
8. Page_Name 是否為系統允許頁面

---

## 5. 寫入資料庫規則

Excel 套用後：

```text
Staff_Master      依 Staff_Name upsert
User_Master       依 User_Email upsert
Master_Lists      依 List_Type + List_Value upsert
Role_Permission   先清空後全量重建
```

注意：

```text
Excel 沒列出的 Staff / User / Master List 不會自動刪除。
要停用請將 Active_Flag 改成 0。
```

這樣可避免誤刪歷史資料。

---

## 6. Demo Login 預設帳號

| Email | Staff | Department | Role |
|---|---|---|---|
| admin@demo.com | 小李 | 機械設計 | Admin |
| manager@demo.com | 張三 | 電氣 | Manager |
| staff@demo.com | 王四 | 組立 | Staff |
| pdpm@demo.com | 鈴木 | 營業 | PD/PM |
| viewer@demo.com | JOHN | CS | Viewer |

---

## 7. 安裝方法

```bash
pip install -r requirements.txt
```

Windows 建議：

```powershell
py -m pip install -r requirements.txt
```

---

## 8. 執行方法

```bash
streamlit run app.py
```

Windows 建議：

```powershell
py -m streamlit run app.py
```

---

## 9. 檔案結構

```text
global_weekly_report_demo_v3_excel_admin_config/
├─ app.py
├─ database.py
├─ export_excel.py
├─ requirements.txt
├─ README.md
└─ .gitignore
```

執行後會自動產生：

```text
global_weekly_report_demo.db
```

---

## 10. 部署到 GitHub / Streamlit Cloud

覆蓋你的 repo 後執行：

```powershell
git add .
git commit -m "Upgrade to v3 Excel Admin Config"
git push
```

Streamlit Cloud 會重新部署。

---

## 11. 注意事項

本系統仍是 DEMO 版。

正式多人使用建議下一階段改為：

```text
Streamlit + PostgreSQL + Microsoft Entra ID / Google Workspace OIDC
```

SQLite 適合本機 Demo 或小規模流程測試，不適合作為正式多人長期寫入資料庫。
