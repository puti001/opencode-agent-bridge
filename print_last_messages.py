import urllib.request
import json
import sys

# 強制輸出為 UTF-8 以防 Windows CP950 編碼錯誤
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

opencode_url = "http://127.0.0.1:54321"
session_id = "ses_127cc8e02ffetpdxm5aJsa2FDO"

def print_all():
    try:
        req = urllib.request.Request(f"{opencode_url}/session/{session_id}/message")
        with urllib.request.urlopen(req) as res:
            messages = json.loads(res.read().decode('utf-8'))
            print("--- 最後 5 條訊息的完整內容 ---")
            for idx, msg in enumerate(messages[-5:]):
                sender = msg.get("sender") or msg.get("author") or "未知"
                parts = msg.get("parts", [])
                text_content = ""
                for part in parts:
                    if isinstance(part, dict) and "text" in part:
                        text_content += part["text"]
                    elif isinstance(part, str):
                        text_content += part
                print(f"\n[訊息 #{idx}] Sender: {sender} (Role: {msg.get('role')})")
                print("-" * 50)
                print(text_content)
                print("-" * 50)
    except Exception as e:
        print("讀取失敗:", e)

if __name__ == "__main__":
    print_all()
