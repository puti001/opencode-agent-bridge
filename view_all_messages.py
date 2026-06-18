import urllib.request
import json

opencode_url = "http://127.0.0.1:54321"
session_id = "ses_127cc8e02ffetpdxm5aJsa2FDO"

def view_all():
    try:
        req = urllib.request.Request(f"{opencode_url}/session/{session_id}/message")
        with urllib.request.urlopen(req) as res:
            messages = json.loads(res.read().decode('utf-8'))
            print(f"Total Messages: {len(messages)}")
            for idx, msg in enumerate(messages[-5:]):
                role = msg.get("role")
                parts = msg.get("parts", [])
                text_content = ""
                for part in parts:
                    if isinstance(part, dict) and "text" in part:
                        text_content += part["text"]
                    elif isinstance(part, str):
                        text_content += part
                print(f"Msg #{idx} - Role: {role}")
                print(f"  Content: {text_content[:300]}...")
    except Exception as e:
        print("讀取失敗:", e)

if __name__ == "__main__":
    view_all()
