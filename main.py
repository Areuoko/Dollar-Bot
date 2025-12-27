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
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    price = 0
    source = ""

    # ------------------------------------------------------------------
    # تلاش ۱: آلن‌چند (استخراج از دیتای مخفی Next.js)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking AlanChand (HTML)...")
            # به جای API، خود صفحه دلار را می‌گیریم
            resp = scraper.get("https://alanchand.com/currencies-price/usd", timeout=20)
            if resp.status_code == 200:
                text = resp.text
                
                # روش ۱: جستجوی مستقیم در متن HTML (ساده‌ترین راه)
                # در آلن چند قیمت معمولا در تایتل صفحه یا تگ‌های مشخص است
                # مثال: <td class="...">60,150</td>
                
                # ما دنبال الگوی جیسون مخفی می‌گردیم که دقیق‌تر است
                # "slug":"usd", ... "price":"60150"
                match = re.search(r'"slug":"usd".*?"price":"([\d\.]+)"', text)
                
                if match:
                    price = float(match.group(1))
                    source = "AlanChand"
                else:
                    # روش ۲: جستجوی بصری در جدول
                    # دلار آمریکا ... 60,500
                    # دنبال عددی ۵ رقمی بعد از کلمه دلار آمریکا می‌گردیم
                    match_table = re.search(r'دلار\s*آمریکا.*?([\d,]{5,7})', text, re.DOTALL)
                    if match_table:
                        price = float(match_table.group(1).replace(',', ''))
                        source = "AlanChand (Table)"
            else:
                print(f"AlanChand Status: {resp.status_code}")
        except Exception as e:
            print(f"AlanChand Error: {e}")

    # ------------------------------------------------------------------
    # تلاش ۲: نوسان (Navasan.net) - معمولا از خارج باز است
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking Navasan...")
            resp = scraper.get("https://www.navasan.net/", timeout=20)
            if resp.status_code == 200:
                text = resp.text
                # جستجو برای قیمت فروش دلار
                # id="usd_sell" > 60,150
                match = re.search(r'id="usd_sell".*?>([\d,]+)<', text)
                if match:
                    price = float(match.group(1).replace(',', ''))
                    source = "Navasan"
            else:
                print(f"Navasan Status: {resp.status_code}")
        except Exception as e:
            print(f"Navasan Error: {e}")

    # ------------------------------------------------------------------
    # تلاش ۳: TGJU (نسخه دسکتاپ - شاید باز شود)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking TGJU Desktop...")
            # نسخه موبایل مشکل DNS داشت، نسخه دسکتاپ را امتحان می‌کنیم
            resp = scraper.get("https://www.tgju.org/profile/price_dollar_rl", timeout=20)
            if resp.status_code == 200:
                text = resp.text
                # الگوی استاندارد TGJU
                match = re.search(r'data-value="([\d,]+)"', text) # گاهی در اتریبیوت است
                if not match:
                    match = re.search(r'class="value">.*?([\d,]{5,7})<', text, re.DOTALL)
                
                if match:
                    price = float(match.group(1).replace(',', ''))
                    # tgju ریال است
                    if price > 100000: price /= 10
                    source = "TGJU"
        except Exception as e:
            print(f"TGJU Error: {e}")

    return price, source

def main():
    print("--- STARTING BOT (HTML Extraction Mode) ---")
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
        print("❌ FAILED: All sources blocked or failed.")

if __name__ == "__main__":
    main()
