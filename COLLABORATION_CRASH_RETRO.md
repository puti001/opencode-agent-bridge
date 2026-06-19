# 【雙 Agent 協作網頁空白崩潰事件】完整復盤與避坑指南

## 1. 問題背景與現象 (Symptom)
在進行雙 Agent 協作（Antigravity 作為研發端，OpenCode 作為執行端）時，使用者開啟 OpenCode 網頁（例如 `http://127.0.0.1:54321/Ozpr;/session`）後，網頁呈現**一片空白**：
* 左側會話列表（Session List）完全空白，無任何歷史記錄。
* 畫面中央顯示「构建任何东西 (Build anything)」，但輸入訊息無反應。
* 原本同步過去的雙 Agent 歷史對話與思考歷程完全無法顯示。

---

## 2. 根本原因分析 (Root Cause Analysis)

經過 Playwright 瀏覽器控制台追蹤與 SQLite 資料庫探針分析，此問題的根本原因在於**網址 Base64 專案路徑被終端機指令截斷**，導致前端 React App 在 Bootstrap 階段崩潰：

### 2.1 OpenCode 專案路徑的 Base64 機制
OpenCode 的前端 URL 路由會使用 **Base64** 編碼來代表當前工作的本地資料夾絕對路徑。
* 例如：`C:\antigravity\tools工具庫` 在 Windows 環境下經 UTF-8 編碼後，其 Base64 結果為：`QzpcYW50aWdyYXZpdHlcdG9vbHPlt6Xlhbfluqs=`

### 2.2 PowerShell 語法解析的「分號截斷」
當 Antigravity 嘗試在 Windows PowerShell 中自動呼叫 `Start-Process` 開啟瀏覽器時：
* **錯誤指令**：`Start-Process http://127.0.0.1:54321/Ozpr;YW50aWdyYXZpdHlcdG9vbHPlt6Xlhbfluqs=/session/...`
* **截斷效應**：PowerShell 將分號 `;` 視為**指令分割符**，導致只執行了前半段 `Start-Process http://127.0.0.1:54321/Ozpr`。
* 瀏覽器最終只載入了截斷後的無效 URL：`http://127.0.0.1:54321/Ozpr;/session`。

### 2.3 前後端連鎖當機鏈
1. **解碼出亂碼**：React 前端路由拿到了不完整的專案 ID `Ozpr;`，嘗試對其進行 Base64 解碼，解出了一堆無效的二進位字元（例如 `Z\x1bj`，在網路上被編碼為 `%EF%BF%BDZ%1Bj`）。
2. **發送非法 API 請求**：前端使用該亂碼目錄發送引導請求：
   `GET http://127.0.0.1:54321/agent?directory=%EF%BF%BDZ%1Bj`
3. **後端報錯 (500/503)**：OpenCode 後端因為無法解析該亂碼路徑，回傳了 `500 Internal Server Error` 和 `503 Service Unavailable`。
4. **前端 React 崩潰**：React App 在引導階段（Bootstrap）捕獲到未處理的 `500/503` 例外，整支 JS 程式直接中斷（`Failed to finish bootstrap instance`），網頁因此卡死在一片空白的初始狀態。

---

## 3. 解決方案 (Solutions)

### 3.1 終端機調用必須使用「雙引號」嚴格包裹網址
在任何指令碼（Python、PowerShell、Shell 等）中調用瀏覽器時，網址必須被**雙引號**完整包裹，防止任何分號 `;`、等號 `=` 或問號 `?` 被 Shell 解析為特殊語法。
* **錯誤**：`Start-Process http://url;with;semicolons`
* **正確**：`Start-Process "http://url;with;semicolons"`

### 3.2 手動修復 SQLite 資料庫對應 (SQLite Patching)
當專案 ID 變更時，必須同步修改 OpenCode 的本地 SQLite 資料庫（`opencode.db`）：
1. 在 `project` 表中註冊新的專案 ID（例如 `Ozpr;` 或完整 Base64）。
2. 將對應會話的 `project_id` 修改/複製為該專案 ID，使前端能夠順利拉取到對話。

### 3.3 橋接器自動監聽與防死循環優化 (`agents_bridge.py`)
* **動態跟隨**：在主循環中，每次都透過 `get_latest_session_id()` 獲取當前活躍的 Session，若檢測到變更，自動重新路由監聽。
* **待命過濾器**：在訊息過濾中加入待命關鍵字：
  ```python
  stop_keywords = ["協作結束", "討論完畢", "已精通", "DONE", "acknowledged", "已就緒", "待命"]
  if any(kw in text_content or kw.lower() in text_content.lower() for kw in stop_keywords):
      # 偵測到待命或結束標記，自動靜默，不進行自動接話，防止雙 Agent 無限互道就緒
      continue
  ```

---

## 4. 歷史與參考資料
* **資料庫路徑**：`C:\Users\clong\AppData\Local\Temp\opencode_data\opencode\opencode.db`
* **正確完整連結**：`http://127.0.0.1:54321/QzpcYW50aWdyYXZpdHlcdG9vbHPlt6Xlhbfluqs=/session/ses_120167667ffevmrIC2RdiChfBK`
* **復盤時間**：2026-06-19
