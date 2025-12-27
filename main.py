import cloudscraper
from bs4 import BeautifulSoup
import os
import requests
from datetime import datetime
import pytz

# تنظیمات
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
    # تلاش ۱: Bonbast (بهترین گزینه برای سرورهای خارجی)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking Bonbast...")
            # درخواست به سایت بن‌بست
            resp = scraper.get("https://bonbast.com", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                
                # تکنیک هوشمند: به جای ID، دنبال متن "US Dollar" می‌گردیم
                # و قیمت را از ستون‌های جلویی آن برمی‌داریم
                usd_row = soup.find('td', string=lambda text: text and "US Dollar" in text)
                
                if usd_row:
                    # پیدا کردن تگ پدر (tr)
                    parent = usd_row.find_parent('tr')
                    # پیدا کردن تمام ستون‌ها (td)
                    cols = parent.find_all('td')
                    
                    # معمولا ستون سوم یا چهارم قیمت فروش است
                    if len(cols) >= 3:
                        # تلاش برای استخراج عدد از ستون‌های مختلف
                        for col in cols:
                            text = col.get_text(strip=True)
                            if text.isdigit() and len(text) >= 5: # عدد ۵ یا ۶ رقمی
                                price = float(text)
                                source = "Bonbast"
                                break
        except Exception as e:
            print(f"Bonbast Parsing Error: {e}")

    # ------------------------------------------------------------------
    # تلاش ۲: ArzLive (منبع کمکی)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking ArzLive...")
            resp = scraper.get("https://arzlive.com/dollar/", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                # در این سایت معمولا آیدی مشخص است
                price_tag = soup.find(id="arz-price")
                
                if price_tag:
                    p_text = price_tag.get_text(strip=True).replace(',', '')
                    price = float(p_text)
                    source = "ArzLive"
        except Exception as e:
            print(f"ArzLive Error: {e}")

    # ------------------------------------------------------------------
    # تلاش ۳: IrArz (منبع سوم)
    # ------------------------------------------------------------------
    if price == 0:
        try:
            print("Checking IrArz...")
            resp = scraper.get("https://irarz.com/", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                # جستجوی کلاس قیمت دلار
                usd_tag = soup.find('span', id='usd_price')
                if usd_tag:
                    price = float(usd_tag.text.replace(',', ''))
                    source = "IrArz"
        except Exception as e:
            print(f"IrArz Error: {e}")

    return price, source

def main():
    print("--- STARTING BOT ---")
    price, source = get_price()
    
    if price > 0:
        tehran = pytz.timezone('Asia/Tehran')
        time_str = datetime.now(tehran).strftime("%H:%M")
        
        msg = (
            f"💵 **دلار بازار آزاد (کد جدید)**\n\n"
            f"🇺🇸 **قیمت:** {int(price):,} تومان\n"
            f"📡 منبع: {source}\n"
            f"⏰ ساعت: {time_str}"
        )
        print(f"✅ SUCCESS: {price} from {source}")
        send_telegram(msg)
    else:
        print("❌ FAILED: All sources (Bonbast, ArzLive, IrArz) failed.")

if __name__ == "__main__":
    main()
