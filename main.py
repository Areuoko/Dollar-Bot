import cloudscraper
import os
import re
import json
from datetime import datetime
import pytz
import requests

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

def send_telegram(text):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram Error: {e}")

def get_price():
    scraper = cloudscraper.create_scraper()
    price = 0
    source = ""

    # ------------------------------------------------------------------
    # تلاش ۱: Dokal.ir (معمولاً با سرور خارجی باز است)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking Dokal...")
            # دکال معمولا قیمت را در یک جیسون ساده برمی‌گرداند
            resp = scraper.get("https://api.dokal.ir/api/v1/prices", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                # جستجو برای دلار آزاد
                if "prices" in data:
                    for item in data["prices"]:
                        if item.get("slug") == "usd" or "دلار" in item.get("title", ""):
                            # قیمت ممکن است string باشد
                            p_str = str(item.get("price", "0")).replace(',', '')
                            price = float(p_str)
                            source = "Dokal"
                            break
            else:
                print(f"Dokal Status: {resp.status_code}")
        except Exception as e:
            print(f"Dokal Error: {e}")

    # ------------------------------------------------------------------
    # تلاش ۲: Bonbast (روش Regex متنی - ضد تغییر ساختار)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking Bonbast (Regex)...")
            resp = scraper.get("https://bonbast.com", timeout=15)
            if resp.status_code == 200:
                text = resp.text
                # الگوی جستجو: کلمه US Dollar ... فاصله ... عدد ۵ یا ۶ رقمی
                # این الگو کل کدهای HTML را نادیده می‌گیرد و فقط دنبال نزدیکترین عدد به کلمه دلار می‌گردد
                # مثال: US Dollar</td><td class="...">64500</td>
                match = re.search(r'US Dollar.*?(\d{2,3}[,]\d{3})', text, re.DOTALL)
                
                if match:
                    price_str = match.group(1).replace(',', '')
                    price = float(price_str)
                    source = "Bonbast"
                else:
                    # تلاش برای پیدا کردن از طریق id="usd1" (روش قدیمی)
                    match_id = re.search(r'id="usd1".*?>([\d,]+)<', text)
                    if match_id:
                        price = float(match_id.group(1).replace(',', ''))
                        source = "Bonbast (ID)"
                    else:
                        print("Bonbast: Price pattern not found in HTML.")
            else:
                print(f"Bonbast Status: {resp.status_code}")
        except Exception as e:
            print(f"Bonbast Error: {e}")

    # ------------------------------------------------------------------
    # تلاش ۳: AlanChand API (تلاش مجدد با چاپ خطا)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking AlanChand...")
            resp = scraper.get("https://alanchand.com/api/currencies", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data:
                    for currency in data["data"]:
                        if currency.get("slug") == "usd":
                            price = float(currency["price"])
                            source = "AlanChand"
                            break
            else:
                print(f"AlanChand Status: {resp.status_code}")
        except Exception as e:
            print(f"AlanChand Error: {e}")

    return price, source

def main():
    print("--- STARTING BOT (Regex Mode) ---")
    price, source = get_price()
    
    if price > 0:
        tehran = pytz.timezone('Asia/Tehran')
        time_str = datetime.now(tehran).strftime("%H:%M")
        
        msg = (
            f"💵 **دلار بازار آزاد (گیت‌هاب)**\n\n"
            f"🇺🇸 **قیمت:** {int(price):,} تومان\n"
            f"📡 منبع: {source}\n"
            f"⏰ ساعت: {time_str}"
        )
        print(f"✅ SUCCESS: {price} from {source}")
        send_telegram(msg)
    else:
        print("❌ FAILED: All sources failed to return a valid price.")

if __name__ == "__main__":
    main()
