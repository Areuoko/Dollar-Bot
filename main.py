import cloudscraper
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime
import pytz
import requests

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

def get_cash_price():
    # ساخت یک مرورگر جعلی که کلادفلر را دور می‌زند
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        }
    )
    
    price = 0
    source = ""

    # ---------------------------------------------------------
    # تلاش ۱: سایت Tala.ir (مرجع طلا و ارز)
    # ---------------------------------------------------------
    try:
        print("Checking Tala.ir...")
        # درخواست به سایت طلا
        resp = scraper.get("https://www.tala.ir/", timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'lxml')
            
            # پیدا کردن سطر مربوط به دلار
            # معمولا در این سایت دلار با تگ‌هایی که شامل "دلار" است مشخص می‌شود
            # ما دنبال عددی می‌گردیم که در باکس "دلار" باشد
            
            # روش جستجوی هوشمند در متن HTML
            text_content = soup.get_text()
            # الگوی جستجو: کلمه دلار ... فاصله ... عدد ۵ یا ۶ رقمی (مثل 60,150)
            match = re.search(r'دلار\s*آزاد.*?([\d,]{5,7})', text_content, re.DOTALL)
            
            if not match:
                # تلاش دوم برای ساختار موبایل
                match = re.search(r'دلار\s*[:\-\s]+([\d,]{5,7})', text_content)

            if match:
                price_str = match.group(1).replace(',', '')
                price = float(price_str)
                # فیلتر قیمت نامعقول (زیر ۴۰ هزار تومن و بالای ۱۰۰ هزار تومن یعنی اشتباه گرفته)
                if 40000 < price < 100000:
                    source = "Tala.ir"
                else:
                    price = 0
    except Exception as e:
        print(f"Tala.ir Error: {e}")

    # ---------------------------------------------------------
    # تلاش ۲: سایت Mesghal.com (اگر طلا نشد)
    # ---------------------------------------------------------
    if price == 0:
        try:
            print("Checking Mesghal...")
            resp = scraper.get("https://www.mesghal.com/", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'lxml')
                # در مثقال معمولا قیمت دلار در جدول است
                # جستجو برای آیدی های معروف
                dollar_tag = soup.find(id="price_dollar") # گاهی این آیدی هست
                
                if dollar_tag:
                    price = float(dollar_tag.text.replace(',', ''))
                    source = "Mesghal.com"
                else:
                    # جستجوی متنی در مثقال
                    text = soup.get_text()
                    match = re.search(r'دلار.*?([\d,]{5,6})', text)
                    if match:
                        p = float(match.group(1).replace(',', ''))
                        if 40000 < p < 100000:
                            price = p
                            source = "Mesghal"
        except Exception as e:
            print(f"Mesghal Error: {e}")

    # ---------------------------------------------------------
    # تلاش ۳: TGJU Mobile (نسخه سبک)
    # ---------------------------------------------------------
    if price == 0:
        try:
            print("Checking TGJU Mobile...")
            resp = scraper.get("https://mobile.tgju.org/", timeout=15)
            if resp.status_code == 200:
                text = resp.text
                # در نسخه موبایل قیمت‌ها در لیست ساده هستند
                # جستجوی 'price_dollar_rl'
                match = re.search(r'price_dollar_rl.*?([\d,]{5,7})', text)
                if match:
                    p = float(match.group(1).replace(',', ''))
                    # tgju ریال میده، تبدیل به تومان
                    if p > 100000: p /= 10
                    
                    if 40000 < p < 100000:
                        price = p
                        source = "TGJU"
        except Exception as e:
            print(f"TGJU Error: {e}")

    return price, source

def main():
    print("Starting Cash Dollar Check...")
    price, source = get_cash_price()
    
    if price > 0:
        tehran = pytz.timezone('Asia/Tehran')
        time_str = datetime.now(tehran).strftime("%H:%M")
        
        msg = (
            f"💵 **گزارش دلار کاغذی (گیت‌هاب)**\n\n"
            f"🇺🇸 **قیمت:** {int(price):,} تومان\n"
            f"🏗 منبع: {source}\n"
            f"⏰ ساعت: {time_str}"
        )
        print(f"SUCCESS: {price} from {source}")
        send_telegram(msg)
    else:
        print("FAILED: No cash price found on any site.")
        # چون تتر نمیخواستی، اگر پیدا نکرد هیچ پیامی به تلگرام نمیده
        # که الکی شلوغ نشه، ولی تو لاگ میتونی ببینی failed شده.

if __name__ == "__main__":
    main()
