import requests
import re
import json
import os
from datetime import datetime, timedelta

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
        "دالر هرات": None,
        "یورو هرات": None,
        "تومان چک": None,
        "تومان بانکی": None,
        "کلدار هرات": None,
        "دلار تهران": None
    }

    # ====== استخراج از کانال هرات (فقط اعداد قبل از کلمات کلیدی) ======
    for msg in reversed(messages_herat):
        # ۱. دالر هرات
        if found_prices["دالر هرات"] is None and "دالر" in msg:
            m = re.search(r'(\d+[.,]\d+)\s*(?:خـرید|فروش|💵)', msg)
            if m:
                found_prices["دالر هرات"] = m.group(1).replace(',', '.')
        # ۲. یورو هرات
        if found_prices["یورو هرات"] is None and "یورو" in msg:
            m = re.search(r'(\d+[.,]\d+)\s*(?:خـرید|فروش|💶)', msg)
            if m:
                found_prices["یورو هرات"] = m.group(1).replace(',', '.')
        # ۳. تومان چک
        if found_prices["تومان چک"] is None and "تومان چک" in msg:
            m = re.search(r'(\d+[.,]\d+)\s*(?:خـرید|فروش|💎)', msg)
            if m:
                found_prices["تومان چک"] = m.group(1).replace(',', '.')
        # ۴. تومان بانکی
        if found_prices["تومان بانکی"] is None and "تومان بانکی" in msg:
            m = re.search(r'(\d+[.,]\d+)\s*(?:خـرید|فروش|💳)', msg)
            if m:
                found_prices["تومان بانکی"] = m.group(1).replace(',', '.')
        # ۵. کلدار هرات
        if found_prices["کلدار هرات"] is None and "کلدار" in msg:
            m = re.search(r'(\d+[.,]\d+)\s*(?:خـرید|فروش|🇵🇰)', msg)
            if m:
                found_prices["کلدار هرات"] = m.group(1).replace(',', '.')

    # ====== استخراج دلار تهران (کانال جداگانه) ======
    tehran_pattern = r'دلار تهران\s*[:]*\s*([\d,]+)'
    for msg in reversed(messages_tehran):
        m = re.search(tehran_pattern, msg)
        if m:
            raw_val = m.group(1).replace(',', '')
            if raw_val.isdigit():
                found_prices["دلار تهران"] = raw_val
                break

    old_data = load_old()
    old_rates = old_data.get("rates", {})

    defaults = {
        "دالر هرات": "63.20",
        "یورو هرات": "73.20",
        "تومان چک": "0.47",
        "تومان بانکی": "0.38",
        "کلدار هرات": "214.00",
        "دلار تهران": "174000"
    }

    # ====== اگر قیمت جدید پیدا نشد، مقدار قبلی را حفظ کن ======
    for key in found_prices:
        if found_prices[key] is None:
            old_val = old_rates.get(key, {}).get("current", "0")
            if old_val != "---" and old_val != "0":
                found_prices[key] = str(old_val).replace(',', '')
            else:
                found_prices[key] = defaults.get(key, "0")

    new_rates = {}
    for key, current_price in found_prices.items():
        try:
            nv = float(current_price)
        except:
            nv = 0.0

        old_item = old_rates.get(key, {})
        old_val_str = str(old_item.get("current", "0")).replace(',', '')
        try:
            ov = float(old_val_str) if old_val_str != "---" else nv
        except:
            ov = nv

        # وضعیت و درصد
        if nv > ov:
            status = "up"
        elif nv < ov:
            status = "down"
        else:
            status = "same"

        if nv == ov:
            percent = "0.00%"
        elif ov != 0:
            diff = ((nv - ov) / ov) * 100
            percent = f"{diff:+.2f}%"
        else:
            percent = "0.00%"

        # ====== مدیریت تاریخچه با زمان ======
        history = old_item.get("history", [])

        if history and isinstance(history[0], (int, float)):
            new_history = []
            now = datetime.now()
            for i, p in enumerate(history):
                days_ago = len(history) - i
                dt = now - timedelta(days=days_ago)
                new_history.append({"price": p, "time": dt.isoformat()})
            history = new_history

        if history and isinstance(history[0], dict) and "ts" in history[0]:
            for h in history:
                h["time"] = h.pop("ts")

        # اضافه کردن نقطه جدید (هر بار که اسکریپت اجرا شود)
        history.append({
            "price": nv,
            "time": datetime.now().isoformat()
        })

        if len(history) > 30:
            history = history[-30:]

        if key == "دلار تهران":
            display_price = f"{int(nv):,}"
        else:
            if nv < 1:
                display_price = f"{nv:.2f}"
            else:
                display_price = f"{nv:.2f}" if nv == int(nv) else str(nv)

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
