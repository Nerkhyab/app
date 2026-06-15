import json
from datetime import datetime, timedelta

with open("last_rates.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for key, item in data["rates"].items():
    old_history = item.get("history", [])
    new_history = []
    for i, price in enumerate(old_history):
        dt = datetime.now() - timedelta(days=len(old_history)-i)
        new_history.append({"price": price, "time": dt.isoformat()})
    item["history"] = new_history

with open("last_rates.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("تبدیل انجام شد.")
