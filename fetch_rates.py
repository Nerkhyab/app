import requests
import re
import json
import os
from datetime import datetime

# منابع دیتا
CHANNEL_HERAT = "https://t.me/s/NerkhYab_Khorasan"
CHANNEL_TEHRAN = "https://t.me/s/dollarsbze"

def clean_html(raw):
    return re.sub(r'<.*?>', '', raw)

def get_messages(url):
    try:
        res = requests.get(url, timeout=20)
        messages = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', res.text, re.S)
        return [clean_html(m) for m in messages[-30:]]
    except:
        return []

def load_old():
    if os.path.exists("last_rates.json"):
        with open("last_rates.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {"rates": {}}

def get_rates():
    messages_herat = get_messages(CHANNEL_HERAT)
    messages_tehran = get_messages(CHANNEL_TEHRAN)
    
    found_prices = {
        "دالر هرات": "63.20",
        "یورو هرات": "73.20",
        "تومان چک": "0.47",
        "تومان بانکی": "0.38",
        "کلدار": "214.00"
    }

    # ۱. استخراج دیتای هرات (طبق روال قبل)
    for msg in reversed(messages_herat):
        for key in found_prices.keys():
            search_key = key.split()[0] 
            if search_key in msg:
                pattern = rf"{search_key}.*?(\d+[.,]\d+)"
                match = re.search(pattern, msg)
                if match:
                    found_prices[key] = match.group(1).replace(',', '.')

    # ۲. استخراج هوشمند دلار تهران (اصلاح شده)
    # این الگو هم عدد را می‌گیرد و هم کلمات بعد از آن را مدیریت می‌کند
    tehran_pattern = r"دلار تهران ⛳️\s*:\s*([\d,]+)"
    
    for msg in reversed(messages_tehran):
        match = re.search(tehran_pattern, msg)
        if match:
            raw_val = match.group(1).replace(',', '')
            if raw_val.isdigit():
                found_prices["دلار تهران"] = raw_val
                break

    old_data = load_old()
    new_rates = {}

    for key, current_price in found_prices.items():
        # دریافت مقدار قبلی
        old_item = old_data.get("rates", {}).get(key, {})
        old_val_str = str(old_item.get("current", "0")).replace(',', '')
        
        try:
            nv = float(current_price)
            ov = float(old_val_str) if old_val_str != "---" else nv
        except:
            continue
        
        # تعیین وضعیت صعودی/نزولی
        status = "up" if nv > ov else ("down" if nv < ov else "same")
        
        # محاسبه درصد تغییرات
        percent = "0.00%"
        if ov != 0:
            diff = ((nv - ov) / ov) * 100
            percent = f"{diff:+.2f}%"

        # مدیریت تاریخچه برای نمودار
        history = [{"price": h, "ts": ""} if isinstance(h, (int, float)) else h for h in history]
        if not history or history[-1]["price"] != nv:
            history.append({"price": nv, "ts": datetime.now().isoformat()})
            if len(history) > 20: history.pop(0)

        # فرمت نمایش (تهران با جداکننده هزارگان، بقیه معمولی)
        display_price = f"{int(nv):,}" if key == "دلار تهران" else current_price

        new_rates[key] = {
            "current": display_price,
            "status": status,
            "percent": percent,
            "history": history
        }

    return {"rates": new_rates}

if __name__ == "__main__":
    data = get_rates()
    with open("last_rates.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("بروزرسانی دیتابیس با موفقیت انجام شد.")
