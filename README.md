# GLOBAL Weekly Report Demo v2

此版本在 v1 基礎上加入 **PD/PM 權限管理** 與 **Demo Login**。

## v2 重點

- 將原本 Sales 角色改為 `PD/PM`
- 新增 Demo Login，下拉選擇不同登入者
- 新增 `user_master`
- 新增 `role_permission`
- 新增 `audit_log`
- 左側選單依 Role 顯示
- 查詢與匯出依 Role 限制資料範圍
- PD/PM 只能管理自己 Owner 的 Cost_Tracking_ID
- Staff 只能看與輸入自己的資料
- Manager 只能看本部門資料
- Admin 可看全部
- Viewer 只能看 Dashboard

## 檔案結構

```text
global_weekly_report_demo_v2/
├─ app.py
├─ database.py
├─ export_excel.py
├─ requirements.txt
├─ README.md
└─ .gitignore
```

## 安裝

```powershell
py -m pip install -r requirements.txt
```

## 執行

```powershell
py -m streamlit run app.py
```

## Demo Login 預設帳號

| Email | Staff | Department | Role |
|---|---|---|---|
| admin@demo.com | 小李 | 機械設計 | Admin |
| manager@demo.com | 張三 | 電氣 | Manager |
| staff@demo.com | 王四 | 組立 | Staff |
| pdpm@demo.com | 鈴木 | 營業 | PD/PM |
| viewer@demo.com | JOHN | CS | Viewer |

## 權限邏輯

### Admin

全部頁面、全部資料、全部匯出。

### Manager

依部門限制：

```text
Department = current_user.Department
```

### Staff

依人員限制：

```text
Staff_Name = current_user.Staff_Name
```

### PD/PM

依案件 Owner 限制：

```text
project_budget_master.Owner = current_user.Staff_Name
```

### Viewer

只能查看 Dashboard。

## 頁面權限

| 頁面 | Admin | Manager | Staff | PD/PM | Viewer |
|---|---:|---:|---:|---:|---:|
| 預算設定 | ✓ | × | × | ✓ | × |
| 日報輸入 | ✓ | ✓ | ✓ | ✓ | × |
| 週報輸入 | ✓ | ✓ | ✓ | ✓ | × |
| 自由彙整 | ✓ | ✓ | ✓ | ✓ | × |
| 自動彙整 Dashboard | ✓ | ✓ | ✓ | ✓ | ✓ |
| 缺漏週報 | ✓ | ✓ | ✓ | ✓ | × |
| 匯出 Excel | ✓ | ✓ | ✓ | ✓ | × |
| Master Data | ✓ | × | × | × | × |
| User Management | ✓ | × | × | × | × |

## Streamlit Cloud 注意事項

此版仍使用 SQLite。  
適合 Demo 與流程測試，不建議直接當正式多人長期資料庫。

正式運作建議下一階段改成：

```text
Streamlit + PostgreSQL + Microsoft Entra ID / Google Workspace OIDC
```

## 重新初始化資料

關閉 Streamlit 後刪除：

```text
global_weekly_report_demo.db
```

再重新執行：

```powershell
py -m streamlit run app.py
```


---

## 11. Admin Data Maintenance

v2 maintenance 版新增：

```text
Admin Data Maintenance
```

此頁面僅 Admin 可見，用於後台修正已輸入資料。

功能包含：

1. 編輯 Daily_Worklog
2. 刪除 Daily_Worklog
3. 編輯 Weekly_Summary_Input
4. 刪除 Weekly_Summary_Input
5. 修改或刪除後自動重建 Weekly_Report_Log
6. 所有後台修改寫入 Audit_Log

注意：本 Demo 版刪除為 hard delete。正式運作建議改成 Deleted_Flag / Deleted_By / Deleted_At 的 soft delete。
