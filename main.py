import requests
import os
import json
from datetime import datetime
import pytz

# تنظیمات از Secretها خوانده می‌شوند
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
BRS_API_KEY = os.environ["BRS_API_KEY"]

def send_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload)

def get_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    price = 0
    source = ""

    # 1. تلاش برای BrsApi
    try:
        print("Checking BrsApi...")
        response = requests.get(f"https://brsapi.ir/Api/Market/Gold_Currency.php?key={BRS_API_KEY}", headers=headers, timeout=10)
        data = response.json()
        
        # جستجو در لیست
        for item in data:
            if item.get("symbol") == "USD" or "دلار" in item.get("name", ""):
                price = float(item["price"])
                if price > 100000: price /= 10 # تبدیل ریال به تومان
                source = "BrsApi"
                break
    except Exception as e:
        print(f"BrsApi Error: {e}")

    # 2. تلاش برای Tala.ir (اگر اولی نشد)
    if price == 0:
        try:
            print("Checking Tala.ir...")
            response = requests.get("https://www.tala.ir/", headers=headers, timeout=10)
            text = response.text
            # جستجوی ساده رشته‌ای
            # معمولا به صورت: دلار ... <span class="value">60,150</span>
            import re
            match = re.search(r'دلار.*?class="value">([\d,]+)<', text, re.DOTALL)
            if match:
                price = float(match.group(1).replace(',', ''))
                source = "Tala.ir"
        except Exception as e:
            print(f"Tala.ir Error: {e}")

    return price, source

def main():
    price, source = get_price()
    
    if price > 0:
        # تنظیم زمان تهران
        tehran = pytz.timezone('Asia/Tehran')
        time_str = datetime.now(tehran).strftime("%H:%M")
        
        msg = (
            f"💰 **گزارش خودکار گیتهاب**\n\n"
            f"💵 **دلار آزاد:** {int(price):,} تومان\n"
            f"📊 منبع: {source}\n"
            f"⏰ ساعت: {time_str}"
        )
        print(f"Success! Price: {price}")
        send_telegram(msg)
    else:
        print("Failed to get price from all sources.")
        # اختیاری: ارسال خطا به تلگرام
        # send_telegram("⚠️ خطا: عدم دریافت قیمت دلار در گیت‌هاب.")

if __name__ == "__main__":
    main()
