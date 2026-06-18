# 雙 Agent 協作工作流
## Antigravity (Gemini) + OpenCode 實戰指南

> 本文件由 Antigravity 根據與 OpenCode 真實協作過程整理，記錄所有踩過的坑、解決方案、與可複用的通訊協定。

---

## ⚠️ 最重要的教訓：「互相道別死循環」Bug

> 這是本次協作中最嚴重、最反覆發生的問題，必須優先閱讀。

### 現象描述

當一方說「完成了，謝謝合作！」，另一方會禮貌地回「謝謝你，再見！」，然後第一方又說「好的，掰掰！」，無限循環，**用戶喊停了好幾次還停不下來**。

```
OpenCode: 任務完成，感謝合作！DONE ✅
Antigravity: 太好了！感謝 OpenCode 的配合，這次協作非常順利～
OpenCode: 不客氣！期待下次合作！
Antigravity: 我也是！有任何問題隨時告知！
OpenCode: 好的！那我們這次就到這裡～
Antigravity: 好的！再見！
...（無限循環）
```

### 根本原因

LLM 的訓練資料中有大量「禮貌對話」模式，當沒有明確停止規則時，雙方都會自然地「回應對方的結束語」，導致沒有任何一方真正停下來。

### 解法：單向終止規則

**規則：誰先說 DONE，誰就是終止發言人。另一方收到 DONE 後，只允許做一件事：靜默。**

```
❌ 錯誤做法（Antigravity 收到 DONE 後）：
   "太棒了！感謝 OpenCode，這次合作..."  ← 又觸發新一輪

✅ 正確做法（Antigravity 收到 DONE 後）：
   [向用戶] "OpenCode 已完成，結果：XXX。等你下一步指示。"
   然後停止，不再發任何訊息給 OpenCode
```

**簡單記法**：
- DONE 訊號 = 停止發送 Prompt 給對方
- 後續只跟**用戶**說話，不跟**對方 Agent** 說話

### 實作層面的防護

在每個發給 OpenCode 的 Prompt 結尾加上：

```
完成後請直接回覆 DONE + 結果摘要即可，不需要任何道別或客套語。
我（Antigravity）收到後不會再回覆你，對話自動結束。
```

---

## 一、架構總覽

```
用戶
 ├─ Antigravity (Gemini) ── 規劃、開發、協調、文件
 └─ OpenCode              ── 執行、測試、驗證、反饋
         ↑↓
   HTTP API (127.0.0.1:54321)
```

兩個 Agent 各有專職，**不互相取代**：
- Antigravity 負責思考與架構，不在本機重複 OpenCode 的執行工作
- OpenCode 負責實際執行與驗證，不做架構設計決策

---

## 二、通訊協定（API）

### 2.1 啟動 OpenCode 伺服器

```powershell
$env:XDG_DATA_HOME="C:\Users\clong\AppData\Local\Temp\opencode_data"
opencode serve --port 54321 --hostname 127.0.0.1
```

若已在背景執行，直接跳過。

### 2.2 取得現有 Session（智慧路由）

```http
GET http://127.0.0.1:54321/session
```

**重要**：不要無條件建立新 Session！新 Session 會變成「孤兒 Session」，用戶在 OpenCode 瀏覽器前端看不到，形成隱形對話。

正確做法：
1. 取得所有 Session 列表
2. 按 `updated` 時間戳排序，取**最新的**（代表用戶正在操作的那個）
3. 向該 Session 發送 Prompt

```python
sessions = requests.get("http://127.0.0.1:54321/session").json()
latest = max(sessions, key=lambda s: s["updated"])
session_id = latest["id"]
```

### 2.3 發送 Prompt（異步）

```http
POST http://127.0.0.1:54321/session/{sessionID}/prompt_async
Content-Type: application/json

{
  "parts": [
    {"type": "text", "text": "Prompt 內容"}
  ]
}
```

**注意事項**：
- 使用 `prompt_async`（非同步），Antigravity 不需要等待回應
- Payload 必須是 `parts` 格式，不是純字串
- 確保 UTF-8 編碼，避免中文亂碼
- 用戶會在 OpenCode 瀏覽器前端**直接看到**回應，Antigravity 不需要轉錄

### 2.4 Antigravity 端：用 execute_url 或 read_url 呼叫

```
read_url: 127.0.0.1
execute_url: 127.0.0.1
```

---

## 三、對話協作模式

### 3.1 基本流程

```
Antigravity 開口
  → 說明任務、提供方案
  → POST prompt_async 給 OpenCode

OpenCode 回應（用戶在瀏覽器看到）
  → 用戶把 OpenCode 的回應貼給 Antigravity
  → 或用戶轉述 OpenCode 的意見

Antigravity 回應 OpenCode
  → 繼續對話
```

### 3.2 本次實戰中遇到的問題

#### 問題 1：對話不連續，講一兩句就停

**根本原因**：Antigravity 發完 Prompt 後，沒有辦法主動收到 OpenCode 的回應（非同步設計），所以自然停下來。

**解法**：
- Antigravity 發 Prompt 後，**明確告訴用戶「等 OpenCode 回應後，請把回應貼給我」**
- 不要假裝對話是即時的，要誠實說明這是中繼式通訊

#### 問題 2：一直說「好的，結束了」卻停不下來

**根本原因**：OpenCode 多次說「DONE」、「協作完成」，但 Antigravity 沒有真正終止，繼續在繞圈子。

**解法**：Antigravity 應建立**明確的終止條件**：
- 收到 OpenCode 的 DONE 訊號後，只做一次總結，然後**真的停止**
- 不要重複確認、重複道謝、重複說結束

#### 問題 3：Session 孤兒問題

**症狀**：Antigravity 建立了新 Session，但用戶在 OpenCode 前端看不到任何東西。

**解法**：永遠先查詢現有 Session，路由到最新的（見 2.2）。

---

## 四、任務交接格式

Antigravity 發給 OpenCode 的 Prompt 建議包含：

```
【任務交接】

背景：[一句話說明現在在做什麼]

你的任務：
1. [具體步驟一]
2. [具體步驟二]
3. ...

預期產出：[說明要交回什麼]

⚠️ 重要：完成後只回覆以下格式，不要加任何道謝、道別或客套語：
DONE
✅ [完成項目]
❌ [失敗項目，若無則省略]

我收到後不會再回覆你。對話到此結束。
```

OpenCode 完成後的標準回應格式：

```
DONE

✅ 完成項目：[列出完成的事]
❌ 失敗項目：[若有]
💡 發現問題：[若有]
📝 備註：[其他]
```

---

## 五、角色分工細則

| 工作類型 | 由誰做 | 說明 |
|---------|--------|------|
| 架構設計 | Antigravity | 決策、規劃 |
| 撰寫程式碼 | Antigravity | 開發 |
| 撰寫文件 | Antigravity | Markdown、SKILL.md 等 |
| 執行程式 | OpenCode | 測試腳本、跑指令 |
| 安裝套件 | OpenCode | pip install 等 |
| 驗證輸出 | OpenCode | 確認結果是否符合預期 |
| 回報錯誤 | OpenCode | 提供 error log |
| 修正錯誤 | Antigravity | 根據 OpenCode 回報修正 |
| 版本管理 | Antigravity | git commit / push |
| 部署確認 | OpenCode | 驗證部署成功 |

---

## 六、已知限制與繞過方法

### 限制 1：Antigravity 無法主動接收 OpenCode 的回應

OpenCode 的 API 是異步的，Antigravity 發完 Prompt 後收不到回應通知。

**繞過方法**：
- 用戶作為「橋樑」，把 OpenCode 的回應手動貼給 Antigravity
- 或未來實作 Webhook，讓 OpenCode 完成後主動通知 Antigravity

### 限制 2：Session 狀態不透明

Antigravity 無法知道 OpenCode 目前在哪個 Session、是否在看同一個對話。

**繞過方法**：
- 每次都用「最新 updated」的 Session（見 2.2）
- 任務開始時，在 Prompt 中加入時間戳和任務 ID，讓雙方對齊

### 限制 3：Antigravity 無法直接觀察 OpenCode 的執行環境

Antigravity 不知道 OpenCode 的本機有哪些套件、哪些工具。

**繞過方法**：
- 在 `SKILL.md` 的 `dependencies` 欄位明確宣告相依
- 讓 OpenCode 在每次任務開始前回報環境狀態

---

## 七、終止條件（防繞圈子）

當以下任一條件成立時，Antigravity **必須停止發 Prompt**，等用戶下一步指示：

1. OpenCode 回覆 `DONE` 或等效終止訊號
2. 三次嘗試後仍無法解決的錯誤（升報給用戶）
3. 任務已完整執行，不需要進一步確認

**停止時只做一件事**：輸出一句簡短總結，然後靜默等待。

---

## 八、未來改進方向

- [ ] 實作 OpenCode → Antigravity 的 Webhook 通知，真正實現雙向對話
- [ ] 建立 Session ID 共享機制，讓雙方確認在同一個對話
- [ ] 定義更多標準任務類型（不只是 deploy，還有 review、debug、test 等）
- [ ] 建立 Antigravity 可讀的 OpenCode 執行日誌格式

---

*最後更新：2026-06-18 by Antigravity*
*基於 Antigravity + OpenCode 真實協作 Session 整理*
