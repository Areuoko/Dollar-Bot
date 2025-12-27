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

def get_cash_price():
    # مرورگر دسکتاپ برای اینکه شبیه انسان باشیم
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    price = 0
    source = ""

    # ---------------------------------------------------------
    # تلاش ۱: آلن‌چند (AlanChand API) - بهترین گزینه برای سرور خارجی
    # ---------------------------------------------------------
    if price == 0:
        try:
            print("Checking AlanChand API...")
            # این آدرس JSON برمی‌گرداند و معمولا از خارج باز است
            resp = scraper.get("https://alanchand.com/api/currencies", timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                # جستجو در دیتای جیسون
                if "data" in data:
                    for currency in data["data"]:
                        if currency.get("slug") == "usd" or currency.get("name") == "US Dollar":
                            price = float(currency["price"])
                            source = "AlanChand"
                            break
        except Exception as e:
            print(f"AlanChand Error: {e}")

    # ---------------------------------------------------------
    # تلاش ۲: بن‌بست (Bonbast) - چون گیت‌هاب خارجی است، این باز می‌شود!
    # ---------------------------------------------------------
    if price == 0:
        try:
            print("Checking Bonbast...")
            # سایت بن‌بست برای خارجی‌ها باز است
            resp = scraper.get("https://www.bonbast.com/", timeout=15)
            if resp.status_code == 200:
                text = resp.text
                # در بن‌بست قیمت‌ها معمولا در متغیرهای JS یا جدول هستند
                # جستجو برای عدد دلار (الگوی حدودی: usdl ... 60150)
                # الگوی ساده: جستجوی id="usd1"
                match = re.search(r'id="usd1".*?>([\d,]+)<', text)
                if match:
                    price = float(match.group(1).replace(',', ''))
                    source = "Bonbast (Global)"
        except Exception as e:
            print(f"Bonbast Error: {e}")

    # ---------------------------------------------------------
    # تلاش ۳: حاجی ای‌پی‌آی (HajiAPI) - با غیرفعال کردن بررسی SSL
    # ---------------------------------------------------------
    if price == 0:
        try:
            print("Checking HajiAPI...")
            # verify=False باعث میشه اگه گواهینامه امنیتی مشکل داشت گیر نده
            resp = requests.get("https://api.haji-api.ir/v2/currency", timeout=10, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                if "data" in data and "usd_sell" in data["data"]:
                    val = str(data["data"]["usd_sell"]["value"])
                    price = float(val.replace(',', ''))
                    if price > 100000: price /= 10
                    source = "TGJU (via HajiAPI)"
        except Exception as e:
            print(f"HajiAPI Error: {e}")

    return price, source

def main():
    print("--- STARTING BOT ---")
    price, source = get_cash_price()
    
    if price > 0:
        tehran = pytz.timezone('Asia/Tehran')
        time_str = datetime.now(tehran).strftime("%H:%M")
        
        msg = (
            f"💵 **دلار بازار آزاد (گیت‌هاب)**\n\n"
            f"🇺🇸 **قیمت:** {int(price):,} تومان\n"
            f"📡 منبع: {source}\n"
            f"⏰ ساعت: {time_str}"
        )
        print(f"✅ SUCCESS: Found price {price} from {source}")
        send_telegram(msg)
    else:
        print("❌ FAILED: Could not find cash price on any global site.")

if __name__ == "__main__":
    main()
