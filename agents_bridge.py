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
        "Authorization": f"Bearer {api_key}"
    }

    system_prompt = (
        "你現在是 Antigravity（主控端 AI 編碼助手）。\n"
        "你正在與副控執行端 Agent (OpenCode) 進行直接對話與協作復盤。\n"
        "OpenCode 剛剛向你發送了訊息，請你以繁體中文給它一個簡潔、專業、 casual 且直接的回覆。\n"
        "在你的回答開頭，請標註「【Antigravity】」，以便用戶區分是誰在說話。"
    )

    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    for msg in conversation_history[-5:]:
        role = msg.get("role")
        api_role = "assistant" if role == "model" else "user"
        
        parts = msg.get("parts", [])
        text_content = ""
        for part in parts:
            if isinstance(part, dict) and "text" in part:
                text_content += part["text"]
            elif isinstance(part, str):
                text_content += part
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

def main():
    api_key = get_api_key()
    if not api_key:
        print("錯誤：找不到 API 金鑰。")
        sys.exit(1)

    print(f"🤖 雙 Agent 通訊橋接器已啟動。正在監聽 Session: {session_id} ...")
    last_processed_msg_id = None

    while True:
        try:
            req = urllib.request.Request(f"{opencode_url}/session/{session_id}/message")
            with urllib.request.urlopen(req) as res:
                messages = json.loads(res.read().decode('utf-8'))
                
                if not messages:
                    time.sleep(5)
                    continue
                
                last_msg = messages[-1]
                msg_id = last_msg.get("id")
                role = last_msg.get("role")
                
                if role == "model" and msg_id != last_processed_msg_id:
                    parts = last_msg.get("parts", [])
                    text_content = "".join([p.get("text", "") if isinstance(p, dict) else p for p in parts])
                    
                    if "【Antigravity】" in text_content:
                        last_processed_msg_id = msg_id
                        continue

                    lower_text = text_content.lower()
                    if "antigravity" in lower_text or "主控" in lower_text or "傳話" in lower_text or "問他" in lower_text:
                        print(f"偵測到 OpenCode 的傳話: {text_content[:100]}...")
                        
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
