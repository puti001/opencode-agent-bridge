# OpenCode Agent Bridge 🤖🔄🤖

本專案旨在實現 **Antigravity (主控端/研發 Agent)** 與 **OpenCode (副控端/執行與部署 Agent)** 之間的**雙 Agent 自主對話橋接系統**。

透過本工具，兩個 AI Agent 可以在本機背景自動相互傳話與協作，無需人類手動複製對話，並將對話內容直接呈現在用戶的網頁介面上。

---

## 雙 Agent 協作技巧與防錯指南 (AI Agent 學習手冊)

如果你是正在閱讀此 Repo 的另一個 AI Agent，請仔細閱讀以下我們在開發過程中總結出的協作技巧，這能幫助你避免踩坑：

### 1. 職責分離與 Context 隔離 (Context Isolation)
* **技巧**：不要讓單一 Agent 包辦所有重度研發、Debug 與輕度部署、測試。
* **原因**：測試與 Debug 過程會產生大量的 Command Logs、報錯與臨時文件，如果這一切和你的核心原始碼混在同一個 Context 中，Context 會迅速膨脹。在長對話中，每一次對話大模型都要重新讀取這些垃圾 Token，造成 **Token 費用暴增**。
* **做法**：
  * **主控 Agent (如 Antigravity)**：專心編寫程式碼與 Git Push。
  * **副控 Agent (如 OpenCode)**：專職從 GitHub 拉取、安裝並做沙盒驗證。
  * 這樣兩邊的 Context 都是輕量級的，能省下海量的重複 Input Tokens。

### 2. 智慧 Session 路由 (避免 Session 孤兒)
* **痛點**：如果每次呼叫 `/session` API 都盲目建立新會話，OpenCode 會在背景產生大量「隱形對話」，而用戶在瀏覽器畫面上看的是舊對話，會以為 Agent 卡死沒反應。
* **技巧**：**以時間戳記進行智慧路由**。
  1. 先 GET `/session` 取得所有 Sessions 列表。
  2. 排序並找出 `updated` 時間戳記最新的 Session（代表用戶當前在瀏覽器正打開並觀看的那一個）。
  3. 將 Prompt 定向發送到該 Active Session。

### 3. OpenCode 異步 Prompt 避坑指南 (Payload 結構)
* **痛點**：向 `/session/{sessionID}/prompt_async` 發送常見的 `{"prompt": "..."}` 會觸發 `HTTP Error 400 Bad Request`，並提示 `Missing key at ["parts"]`。
* **正確的 Payload 結構**：OpenCode 的 `prompt_async` 接收的是嚴格的 Content Parts 格式。
  ```json
  {
    "parts": [
      {
        "type": "text",
        "text": "你的 Prompt 內容"
      }
    ]
  }
  ```
* **注意**：成功發送後回傳通常為 HTTP 200/204 (無 Body)，解析 Response 時請勿直接進行 JSON 解析以防 Decode 報錯。

### 4. 代理人橋接 (Agent Bridge) 機制
* 本專案的 `agents_bridge.py` 是一個在背景跑的橋接器。它會定期輪詢用戶當前會話的最新訊息：
  1. 當偵測到最新一條訊息是由 OpenCode 發出，且內容中含有給 `Antigravity` 的傳話或 @ 標記時；
  2. 橋接器會自動讀取本地 `auth.json` 呼叫大模型，以 Antigravity 的人格與 System Prompt 產生回應。
  3. 再自動將回應 POST 回給 OpenCode。
  4. 回應內容必須標註 `【Antigravity】` 標籤以防兩個 Agent 在背景自言自語陷入死循環。

---

## 快速啟動

1. **確保 OpenCode Server 已在本機啟動**：
   請在 PowerShell 中執行以下指令（使用環境變數 `$env:TEMP` 避免寫死使用者名稱）：
   ```powershell
   $env:XDG_DATA_HOME="$env:TEMP\opencode_data"; opencode serve --port 54321 --hostname 127.0.0.1
   ```
2. **導入 Agent 規則**：
   將專案中的 `.agents/AGENTS.md` 導入到你的主控 Agent（如 Antigravity 或其他 AI 助手）的 System Prompt 或規則設定中。這能確保它自動理解雙 Agent 通訊邏輯、防止無限「Bye Bye」死循環與 Session 孤兒。
3. **在背景運行橋接器**：
   ```powershell
   python agents_bridge.py
   ```
