import urllib.request
import json

opencode_url = "http://127.0.0.1:4096"
session_id = "ses_127cc8e02ffetpdxm5aJsa2FDO"

def read_reply():
    try:
        req = urllib.request.Request(f"{opencode_url}/session/{session_id}/message")
        with urllib.request.urlopen(req) as res:
            messages = json.loads(res.read().decode('utf-8'))
            
            # 尋找最後一條由 model 產生的訊息（且不是 Antigravity 的橋接回應）
            for msg in reversed(messages):
                role = msg.get("role")
                if role == "model":
                    parts = msg.get("parts", [])
                    text_content = "".join([p.get("text", "") if isinstance(p, dict) else p for p in parts])
                    if "【Antigravity】" not in text_content:
                        print("--- 找到 OpenCode 的最新意見回覆 ---")
                        print(text_content)
                        return
            print("未找到 OpenCode 的最新回覆。")
    except Exception as e:
        print("讀取失敗:", e)

if __name__ == "__main__":
    read_reply()
