# Agent 協作協定

本文件定義 Antigravity（研發端）與 OpenCode（測試/執行端）之間的雙 Agent CI/CD 協作規範。

## 1. 角色分工

| 角色 | 職責 |
|------|------|
| **Antigravity** | 開發技能、撰寫文件、推送至 GitHub |
| **OpenCode** | 從 GitHub 拉取、安裝、預檢環境、測試驗證、產出報告 |

Antigravity 不在本機重複實作與測試；OpenCode 為唯一的第一線執行與驗證環境。

## 2. 交棒訊號

Antigravity 推送完成後，在對話中輸入以下指令觸發交接：

```
[deploy] <技能名稱>
```

範例：

```
[deploy] tutorial-gen
```

OpenCode 收到訊號後，依序執行：
1. 讀取 repo 根目錄的 `skills.json`，取得技能路徑、相依套件與版本
2. 拉取對應的 `SKILL.md`
3. 預檢環境與安裝相依套件
4. 執行測試
5. 輸出標準化測試報告

## 3. 相依宣告

每支技能的 `SKILL.md` 須在 YAML Frontmatter 中加入 `dependencies` 欄位：

```yaml
---
name: tutorial-gen
description: 產生互動翻轉卡片教學網頁
dependencies: [requests, beautifulsoup4]
---
```

OpenCode 執行前自動比對 `pip list`，缺少的套件自動執行 `pip install`。

## 4. 技能註冊檔 (`skills.json`)

repo 根目錄須維護 `skills.json`，格式如下：

```json
{
  "skills": [
    {
      "name": "tutorial-gen",
      "path": "skills/tutorial-gen/SKILL.md",
      "dependencies": ["requests", "beautifulsoup4"],
      "version": "1.0.0"
    }
  ]
}
```

### 欄位說明

| 欄位 | 型態 | 說明 |
|------|------|------|
| `name` | string | 技能名稱，與 `[deploy]` 指令對應 |
| `path` | string | 相對於 repo 根目錄的 SKILL.md 路徑 |
| `dependencies` | string[] | Python 套件列表（可為空陣列） |
| `version` | string | 語意化版本號 (SemVer) |

每次推送新版本時，Antigravity 須更新 `skills.json` 中的版本號。

## 5. 標準化測試報告

測試完成後，OpenCode 輸出以下格式：

```markdown
## 測試報告
- 技能名稱：tutorial-gen
- 版本：1.0.0
- 測試模式：url ✅ / file ⏭ / text ⏭
- 輸出驗證：通過 ✅
- 測試時間：2025-06-18 14:30
- 結果：PASS
```

測試模式列出三種輸入的測試狀態（✅ 通過 / ❌ 失敗 / ⏭ 跳過）。

## 6. 版本語意

遵循 SemVer：`MAJOR.MINOR.PATCH`
- **MAJOR**: 不相容的 API 或流程變更
- **MINOR**: 向下相容的新功能
- **PATCH**: 向下相容的錯誤修正
