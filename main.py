import cloudscraper
import os
import re
import json
from datetime import datetime
import pytz
import requests

# خواندن تنظیمات
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: BOT_TOKEN or CHAT_ID is missing in Secrets!")
        return

    print(f"🚀 Sending message to {CHAT_ID}...")
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=10)
        
        # چاپ نتیجه ارسال
        if resp.status_code == 200:
            print("✅ Telegram Message SENT Successfully!")
        else:
            print(f"❌ Telegram Failed: {resp.status_code}")
            print(f"Response: {resp.text}") # این خط دلیل ارور را می‌گوید
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def get_price():
    # ساخت مرورگر
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    price = 0
    source = ""

    # ------------------------------------------------------------------
    # تلاش ۱: آلن‌چند (AlanChand HTML)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking AlanChand (HTML)...")
            resp = scraper.get("https://alanchand.com/currencies-price/usd", timeout=20)
            if resp.status_code == 200:
                text = resp.text
                
                # جستجو برای جدول قیمت دلار
                # پترن: دلار آمریکا ... عدد ...
                match_table = re.search(r'دلار\s*آمریکا.*?([\d]{2},[\d]{3})', text, re.DOTALL)
                
                if match_table:
                    price_str = match_table.group(1).replace(',', '')
                    price = float(price_str)
                    source = "AlanChand"
                else:
                    # پترن دوم: جستجو در تایتل
                    match_title = re.search(r'قیمت\s*دلار.*?([\d]{2},[\d]{3})', text)
                    if match_title:
                        price = float(match_title.group(1).replace(',', ''))
                        source = "AlanChand (Title)"
            else:
                print(f"AlanChand Status: {resp.status_code}")
        except Exception as e:
            print(f"AlanChand Error: {e}")

    # ------------------------------------------------------------------
    # تلاش ۲: نوسان (Navasan)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking Navasan...")
            resp = scraper.get("https://www.navasan.net/", timeout=20)
            if resp.status_code == 200:
                text = resp.text
                match = re.search(r'id="usd_sell".*?>([\d,]+)<', text)
                if match:
                    price = float(match.group(1).replace(',', ''))
                    source = "Navasan"
        except Exception as e:
            print(f"Navasan Error: {e}")

    return price, source

def main():
    print("--- STARTING BOT ---")
    
    # تست اینکه آیا سکرت‌ها خوانده شده‌اند؟
    if not BOT_TOKEN:
        print("⚠️ Warning: BOT_TOKEN is empty!")
    if not CHAT_ID:
        print("⚠️ Warning: CHAT_ID is empty!")

    price, source = get_price()
    
    if price > 0:
        tehran = pytz.timezone('Asia/Tehran')
        time_str = datetime.now(tehran).strftime("%H:%M")
        
        msg = (
            f"💵 **دلار بازار آزاد**\n\n"
            f"🇺🇸 **قیمت:** {int(price):,} تومان\n"
            f"📡 منبع: {source}\n"
            f"⏰ ساعت: {time_str}"
        )
        print(f"✅ Found Price: {price}")
        send_telegram(msg)
    else:
        print("❌ FAILED: All sources blocked or failed.")

if __name__ == "__main__":
    main()
