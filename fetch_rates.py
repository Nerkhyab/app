import requests
import re
import json
import os
from datetime import datetime, timedelta

# منابع دیتا
CHANNEL_HERAT = "https://t.me/s/NerkhYab_Khorasan"
CHANNEL_TEHRAN = "https://t.me/s/dollar3sbze"

def clean_html(raw):
    return re.sub(r'<.*?>', '', raw)

def get_messages(url, limit=50):
    try:
        res = requests.get(url, timeout=20)
        messages = re.findall(r'<div class="tgme_widget_message_text.*?>(.*?)</div>', res.text, re.S)
        return [clean_html(m) for m in messages[-limit:]]
    except:
        return []

def load_old():
    if os.path.exists("last_rates.json"):
        with open("last_rates.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return {"rates": {}}

def get_rates():
    messages_herat = get_messages(CHANNEL_HERAT, 50)
    messages_tehran = get_messages(CHANNEL_TEHRAN, 50)
    
    found_prices = {
        "دالر هرات": None,
        "یورو هرات": None,
        "تومان چک": None,
        "تومان بانکی": None,
        "کلدار هرات": None,
        "دلار تهران": None
    }

    # ===== تشخیص پیام کلی =====
    summary_message = None
    for msg in messages_herat:
        if "پایان معاملات" in msg:
            summary_message = msg
            break

    # ===== استخراج قیمت‌ها =====
    if summary_message:
        # ===== پیام کلی (اصلاح شده) =====
        pattern = r'(دالر|یورو|کلدار|تومان چک)[^\d]*([\d,]+\.?\d*)'
        matches = re.findall(pattern, summary_message)
        for name, price in matches:
            key = name + " هرات" if name != "تومان چک" else name
            if key in found_prices:
                price = price.replace(',', '.')
                # فقط عدد اول (قیمت خرید) رو بگیر
                if ' ' in price:
                    price = price.split()[0]
                found_prices[key] = price
    else:
        # ===== پیام‌های تکی (با پشتیبانی از فرمت جدید و قدیم) =====
        for msg in reversed(messages_herat):
            # جلوگیری از بررسی پیام‌های تکراری
            if all(v is not None for v in found_prices.values() if v != "دلار تهران"):
                break
                
            # روش جدید: استخراج اعداد به صورت ترتیبی
            numbers = re.findall(r'(\d+[.,]\d+)', msg)
            if len(numbers) >= 4 and not any(keyword in msg for keyword in ["دالر", "یورو", "کلدار", "تومان"]):
                # اگر نام ارزها نبود، به ترتیب نسبت بده
                if found_prices["دالر هرات"] is None:
                    found_prices["دالر هرات"] = numbers[0].replace(',', '.')
                if found_prices["یورو هرات"] is None:
                    found_prices["یورو هرات"] = numbers[1].replace(',', '.')
                if found_prices["کلدار هرات"] is None:
                    found_prices["کلدار هرات"] = numbers[2].replace(',', '.')
                if found_prices["تومان چک"] is None:
                    found_prices["تومان چک"] = numbers[3].replace(',', '.')
            
            # روش قدیم: جستجوی نام ارز (برای پیام‌های دارای نام)
            if "دالر هرات" in msg and found_prices["دالر هرات"] is None:
                m = re.search(r'دالر هرات\s*([\d,.]+)', msg)
                if m:
                    found_prices["دالر هرات"] = m.group(1).replace(',', '.')
            if "یورو هرات" in msg and found_prices["یورو هرات"] is None:
                m = re.search(r'یورو هرات\s*([\d,.]+)', msg)
                if m:
                    found_prices["یورو هرات"] = m.group(1).replace(',', '.')
            if "تومان چک" in msg and found_prices["تومان چک"] is None:
                m = re.search(r'تومان چک\s*([\d,.]+)', msg)
                if m:
                    found_prices["تومان چک"] = m.group(1).replace(',', '.')
            if "تومان بانکی" in msg and found_prices["تومان بانکی"] is None:
                m = re.search(r'تومان بانکی\s*([\d,.]+)', msg)
                if m:
                    found_prices["تومان بانکی"] = m.group(1).replace(',', '.')
            if "کلدار هرات" in msg and found_prices["کلدار هرات"] is None:
                m = re.search(r'کلدار هرات\s*([\d,.]+)', msg)
                if m:
                    found_prices["کلدار هرات"] = m.group(1).replace(',', '.')

    # ===== دلار تهران =====
    for msg in reversed(messages_tehran):
        m = re.search(r'دلار تهران.*?([\d,]+)', msg)
        if m:
            raw_val = m.group(1).replace(',', '')
            if raw_val.isdigit():
                found_prices["دلار تهران"] = raw_val
                break

    # ===== مقدار پیش‌فرض =====
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
    for key in found_prices:
        if found_prices[key] is None:
            old_val = old_rates.get(key, {}).get("current", "0")
            if old_val not in ["---", "0"]:
                found_prices[key] = str(old_val).replace(',', '')
            else:
                found_prices[key] = defaults.get(key, "0")

    # ===== ساخت خروجی =====
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
