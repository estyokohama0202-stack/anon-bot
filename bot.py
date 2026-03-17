import requests
import time
import os

BEARER_TOKEN = os.getenv("BEARER_TOKEN")
USER_ID = os.getenv("USER_ID")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

CHECK_INTERVAL = 21600  # 6時間

headers = {
"Authorization": f"Bearer {BEARER_TOKEN}"
}

def get_following():
url = f"https://api.x.com/2/users/{USER_ID}/following"
params = {
"user.fields": "description,profile_image_url,public_metrics",
"max_results": 1000
}

```
try:
    res = requests.get(url, headers=headers, params=params)
    if res.status_code != 200:
        print("API Error:", res.text)
        return {}

    data = res.json()

    users = {}
    if "data" in data:
        for user in data["data"]:
            users[user["id"]] = user

    return users

except Exception as e:
    print("Error:", e)
    return {}
```

def send_discord(user, action):
# タイトルカスタム
if action == "New Follow":
title = "🎉 DJSHIGEが新しくフォローしました"
elif action == "Unfollow":
title = "⚠️ DJSHIGEがフォロー解除しました"
else:
title = "📌 最近のフォロー"

```
profile_url = f"https://x.com/{user['username']}"

embed = {
    "title": title,
    "description": f"👤 @{user['username']}\n📝 {user.get('description', 'No bio')}\n🔗 {profile_url}",
    "color": 5814783,
    "thumbnail": {
        "url": user["profile_image_url"]
    },
    "fields": [
        {
            "name": "👥 フォロワー数",
            "value": str(user["public_metrics"]["followers_count"]),
            "inline": True
        }
    ],
    "footer": {
        "text": "X Follow Monitor"
    }
}

try:
    requests.post(DISCORD_WEBHOOK_URL, json={"embeds": [embed]})
except Exception as e:
    print("Discord Error:", e)
```

def send_initial(users):
print("Sending initial 10 follows...")

```
latest_users = list(users.values())[:10]

fo
```
