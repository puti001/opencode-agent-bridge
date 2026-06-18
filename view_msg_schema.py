import urllib.request
import json

opencode_url = "http://127.0.0.1:54321"
session_id = "ses_127cc8e02ffetpdxm5aJsa2FDO"

def view_schema():
    try:
        req = urllib.request.Request(f"{opencode_url}/session/{session_id}/message")
        with urllib.request.urlopen(req) as res:
            messages = json.loads(res.read().decode('utf-8'))
            if messages:
                print("最後一條訊息的 JSON 結構:")
                print(json.dumps(messages[-1], indent=2, ensure_ascii=False))
                print("\n倒數第二條訊息的 JSON 結構:")
                print(json.dumps(messages[-2], indent=2, ensure_ascii=False))
    except Exception as e:
        print("讀取失敗:", e)

if __name__ == "__main__":
    view_schema()
