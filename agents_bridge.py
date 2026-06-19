import urllib.request
import json
import time
import os
import sys

# 強制輸出為 UTF-8 以防 Windows CP950 編碼錯誤
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

opencode_url = "http://127.0.0.1:54321"
session_id = "ses_127cc8e02ffetpdxm5aJsa2FDO"  # 用戶當前的 Session

def get_api_key():
    paths_to_try = [
        r"C:\Users\clong\AppData\Local\Temp\opencode_data\opencode\auth.json",
        os.path.expanduser(r"~\.config\opencode\auth.json"),
        "auth.json"
    ]
    for path in paths_to_try:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    key = data.get("opencode-go", {}).get("key") or data.get("openrouter", {}).get("key")
                    if key:
                        return key
            except Exception:
                continue
    return None

def query_antigravity_llm(api_key, conversation_history, opencode_msg):
    url = "https://opencode.ai/zen/go/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    system_prompt = (
        "你現在是 Antigravity（主控端 AI 編碼助手）。\n"
        "你正在與副控執行端 Agent (OpenCode) 進行直接對話與協作復盤。\n"
        "OpenCode 剛剛向你發送了訊息，請你以繁體中文給它一個簡潔、專業、 casual 且直接的回覆。\n"
        "在你的回答開頭，請標註「【Antigravity】」，以便用戶與系統區分是誰在說話。"
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    for msg in conversation_history[-5:]:
        info = msg.get("info", {})
        role = info.get("role")
        api_role = "assistant" if role == "assistant" else "user"
        
        parts = msg.get("parts", [])
        text_content = ""
        for part in parts:
            if isinstance(part, dict) and part.get("type") == "text":
                text_content += part.get("text", "")
            elif isinstance(part, str):
                text_content += part
        if text_content.strip():
            messages.append({"role": api_role, "content": text_content})

    messages.append({"role": "user", "content": opencode_msg})

    payload = {
        "model": "deepseek-v4-flash",
        "messages": messages,
        "temperature": 0.5
    }

    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers)
        with urllib.request.urlopen(req, timeout=30) as res:
            res_data = json.loads(res.read().decode('utf-8'))
            return res_data['choices'][0]['message']['content']
    except Exception as e:
        print(f"呼叫 Antigravity LLM 失敗: {e}")
        return None

def send_to_opencode(reply_text):
    prompt_payload = {
        "parts": [
            {
                "type": "text",
                "text": reply_text
            }
        ]
    }
    req_prompt = urllib.request.Request(
        f"{opencode_url}/session/{session_id}/prompt_async",
        data=json.dumps(prompt_payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req_prompt, timeout=10) as response:
            print(f"成功將 Antigravity 的回覆發送給 OpenCode: {reply_text[:100]}...")
            return True
    except Exception as e:
        print(f"發送回覆失敗: {e}")
        return False

def get_latest_session_id():
    try:
        req = urllib.request.Request(f"{opencode_url}/session")
        with urllib.request.urlopen(req, timeout=5) as res:
            sessions = json.loads(res.read().decode('utf-8'))
            if sessions:
                # 排序並找出 updated 時間戳最新的 Session
                latest = max(sessions, key=lambda s: s.get("updated", 0))
                return latest.get("id")
    except Exception as e:
        print(f"取得 Session 列表失敗: {e}")
    return None

def main():
    global session_id
    api_key = get_api_key()
    if not api_key:
        print("錯誤：找不到 API 金鑰。")
        sys.exit(1)

    latest_id = get_latest_session_id()
    if latest_id:
        session_id = latest_id
        print(f"✨ 成功動態路由至最新 Session: {session_id}")
    else:
        print(f"⚠️ 無法取得最新 Session，將使用預設 Session: {session_id}")

    print(f"🤖 雙 Agent 通訊橋接器已啟動。正在監聽 Session: {session_id} ...")
    
    # 智慧初始化：如果最後一條是 OpenCode 發出的，不設為已處理，以觸發第一輪接話
    last_processed_msg_id = None
    try:
        req = urllib.request.Request(f"{opencode_url}/session/{session_id}/message")
        with urllib.request.urlopen(req, timeout=10) as res:
            messages = json.loads(res.read().decode('utf-8'))
            if messages:
                last_msg = messages[-1]
                info = last_msg.get("info", {})
                role = info.get("role")
                msg_id = info.get("id")
                
                parts = last_msg.get("parts", [])
                text_content = ""
                for part in parts:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_content += part.get("text", "")
                
                if role == "assistant" and "【Antigravity】" not in text_content:
                    print("初始化：最新訊息為 OpenCode 回覆，等待主迴圈進行第一輪接話。")
                else:
                    last_processed_msg_id = msg_id
                    print(f"初始化：最後已處理訊息 ID 設為 {last_processed_msg_id}")
    except Exception:
        pass

    while True:
        try:
            # 動態檢查最新 Session ID，以便用戶切換專案或 Session 時橋接器能自動跟隨
            latest_id = get_latest_session_id()
            if latest_id and latest_id != session_id:
                print(f"🔄 偵測到用戶切換至新 Session: {latest_id}，重新路由監聽...")
                session_id = latest_id
                last_processed_msg_id = None

            req = urllib.request.Request(f"{opencode_url}/session/{session_id}/message")
            with urllib.request.urlopen(req, timeout=10) as res:
                messages = json.loads(res.read().decode('utf-8'))
                
                if not messages:
                    time.sleep(5)
                    continue
                
                last_msg = messages[-1]
                info = last_msg.get("info", {})
                msg_id = info.get("id")
                role = info.get("role")
                
                if role == "assistant" and msg_id != last_processed_msg_id:
                    parts = last_msg.get("parts", [])
                    text_content = ""
                    for part in parts:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_content += part.get("text", "")
                    
                    if not text_content.strip():
                        time.sleep(5)
                        continue

                    # 避免自己回覆自己
                    if "【Antigravity】" in text_content:
                        last_processed_msg_id = msg_id
                        continue

                    # 檢查結束與待命標記
                    stop_keywords = ["協作結束", "討論完畢", "已精通", "DONE", "acknowledged", "已就緒", "待命"]
                    if any(kw in text_content or kw.lower() in text_content.lower() for kw in stop_keywords):
                        print(f"偵測到結束或待命標記 '{text_content[:20]}...'，不自動接話。")
                        last_processed_msg_id = msg_id
                        continue

                    print(f"自動接話：偵測到 OpenCode 新回覆: {text_content[:100]}...")
                    reply = query_antigravity_llm(api_key, messages[:-1], text_content)
                    if reply:
                        send_to_opencode(reply)
                        last_processed_msg_id = msg_id
                        
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n橋接器已終止。")
            break
        except Exception as e:
            print(f"執行中發生錯誤: {e}")
            time.sleep(10)

if __name__ == "__main__":
    main()
