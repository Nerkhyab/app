import os
import json
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

def get_rates():
    # ۱. تعریف کانال‌ها
    URL_HERAT = "https://t.me/s/NerkhYab_Khorasan"
    URL_TEHRAN = "https://t.me/s/dollarsbze"
    FILE_NAME = 'last_rates.json'
    now = datetime.now()

    # ۲. الگوهای استخراج (Regex)
    mapping_herat = {
        "دالر هرات": r"دالر.*?(\d+[.,]\d+)",
        "یورو هرات": r"یورو.*?(\d+[.,]\d+)",
        "تومان چک": r"چک.*?(\d+[.,]\d+)",
        "تومان بانکی": r"بانکی.*?(\d+[.,]\d+)",
        "کلدار هرات": r"کلدار.*?(\d+[.,]\d+)"
    }
    pattern_tehran = r"دلار تهران ⛳️\s*:\s*([\d,]+)"

    # ۳. لود کردن دیتای قبلی
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if "rates" not in data: data = {"rates": {}}
        except: data = {"rates": {}}
    else:
        data = {"rates": {}}

    headers = {'User-Agent': 'Mozilla/5.0'}

    def update_data(key, val, is_formatted=False):
        try:
            nv = float(val)
            if key not in data["rates"]:
                data["rates"][key] = {"history": [nv], "status": "up", "percent": "0.00%"}
            
            # قیمت مبنا برای درصد تغییرات (اولین قیمت موجود در تاریخچه روز)
            base_price = float(data["rates"][key]["history"][0])
            
            data["rates"][key]["status"] = "up" if nv >= base_price else "down"
            diff = ((nv - base_price) / base_price * 100) if base_price != 0 else 0
            data["rates"][key]["percent"] = f"{diff:+.2f}%"
            
            # فرمت نمایش قیمت
            data["rates"][key]["current"] = f"{int(nv):,}" if is_formatted else f"{nv:.2f}"
            
            # آپدیت تاریخچه (فقط اگر قیمت تغییر کرده باشد)
            if data["rates"][key]["history"][-1] != nv:
                data["rates"][key]["history"].append(nv)
                
                # نگهداری تا ۱۰۰۰ نقطه داده برای نمودار یک ماهه
                if len(data["rates"][key]["history"]) > 1000:
                    data["rates"][key]["history"].pop(0)
        except: pass

    def process_source(url, is_tehran=False):
        try:
            response = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(response.text, 'html.parser')
            # پیدا کردن تمام پیام‌های متنی
            messages = soup.find_all('div', class_='tgme_widget_message_text')
            
            # پردازش از قدیمی‌ترین پیام به جدیدترین برای ساخت صحیح تاریخچه
            for msg in messages:
                text = msg.get_text(separator=" ").replace('\n', ' ')
                if is_tehran:
                    match = re.search(pattern_tehran, text)
                    if match:
                        val_raw = match.group(1).replace(',', '')
                        update_data("دلار تهران", val_raw, is_formatted=True)
                else:
                    for key, pattern in mapping_herat.items():
                        match = re.search(pattern, text)
                        if match:
                            val = match.group(1).replace(',', '.')
                            update_data(key, val)
        except Exception as e:
            print(f"Error fetching {url}: {e}")

    # ۴. اجرای استخراج
    process_source(URL_HERAT, is_tehran=False)
    process_source(URL_TEHRAN, is_tehran=True)

    # ۵. ذخیره نهایی در فایل
    with open(FILE_NAME, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    print(f"Success! History built and updated at {now.strftime('%H:%M')}")

if __name__ == "__main__":
    get_rates()
