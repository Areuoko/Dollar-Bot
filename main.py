import cloudscraper
import re
import requests
import os
from bs4 import BeautifulSoup

# ===========================================================
# تنظیمات اتصال به کلودفلر
# ===========================================================
CLOUDFLARE_URL = "https://golden-bot.tilapila007.workers.dev/"
SECRET_KEY = "MY_SECURE_PASSWORD_123"
# ===========================================================

def send_to_cloudflare(price, source):
    print(f"🚀 Sending Price ({price:,}) from {source} to Cloudflare...")
    
    try:
        payload = {
            "price": price,
            "source": source
        }
        headers = {
            "X-Secret-Key": SECRET_KEY,
            "Content-Type": "application/json"
        }
        
        resp = requests.post(CLOUDFLARE_URL, json=payload, headers=headers, timeout=20)
        
        if resp.status_code == 200:
            print("✅ Data sent to Cloudflare successfully!")
            print(f"Response: {resp.text}")
        else:
            print(f"❌ Cloudflare Error: {resp.status_code}")
            print(f"Details: {resp.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def parse_price_string(text_val):
    """تبدیل اعداد فارسی و انگلیسی با کاما به عدد اعشاری/صحیح"""
    if not text_val:
        return 0
    # تبدیل ارقام فارسی به انگلیسی
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    text_val = text_val.translate(translation_table)
    
    # پیدا کردن اعداد همراه با کاما
    match = re.search(r'([\d,]{5,10})', text_val)
    if match:
        clean_str = match.group(1).replace(',', '')
        try:
            return float(clean_str)
        except ValueError:
            return 0
    return 0

def get_cash_price():
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    price = 0
    source = ""

    # -----------------------------------------------------------
    # تلاش ۱: آلن‌چند (AlanChand) با استفاده از BeautifulSoup
    # -----------------------------------------------------------
    if price == 0:
        try:
            print("Checking AlanChand...")
            resp = scraper.get("https://alanchand.com/currencies-price/usd", timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # حذف تمام اسکریپت‌ها و استایل‌ها برای جلوگیری از گرفتن اعداد نامربوط
                for script in soup(["script", "style"]):
                    script.extract()

                # روش اول: جستجو در متاتگ‌ها (معمولاً دقیق‌ترین و پایدارترین راه در آلن‌چند)
                meta_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    extracted = parse_price_string(meta_desc["content"])
                    if extracted > 10000: # اطمینان از منطقی بودن قیمت
                        price = extracted
                        source = "AlanChand (Meta)"

                # روش دوم: در صورت عدم موفقیت، جستجو در متن پالایش‌شده صفحه
                if price == 0:
                    text_content = soup.get_text(separator=' ')
                    # جستجوی عبارت قیمت دلار
                    match = re.search(r'قیمت\s*دلار\s*آمریکا[^\d]*([\d,]{5,10})', text_content)
                    if match:
                        price = float(match.group(1).replace(',', ''))
                        source = "AlanChand (Parsed Text)"
        except Exception as e:
            print(f"AlanChand Error: {e}")

    # -----------------------------------------------------------
    # تلاش ۲: نوسان (Navasan)
    # -----------------------------------------------------------
    if price == 0:
        try:
            print("Checking Navasan...")
            resp = scraper.get("https://www.navasan.net/", timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for script in soup(["script", "style"]):
                    script.extract()
                
                # پیدا کردن المان مربوط به usd_sell یا دلار تهران
                usd_elem = soup.find(id="usd_sell") or soup.find(class_="usd_sell")
                if usd_elem:
                    extracted = parse_price_string(usd_elem.text)
                    if extracted > 10000:
                        price = extracted
                        source = "Navasan"
                else:
                    # جستجوی متنی در نوسان
                    text_content = soup.get_text(separator=' ')
                    match = re.search(r'دلار\s*تهران[^\d]*([\d,]{5,10})', text_content)
                    if match:
                        price = float(match.group(1).replace(',', ''))
                        source = "Navasan (Text)"
        except Exception as e:
            print(f"Navasan Error: {e}")

    return price, source

def main():
    print("--- GitHub Scraper Started ---")
    price, source = get_cash_price()
    
    if price > 0:
        send_to_cloudflare(price, source)
    else:
        print("❌ FAILED: Could not find cash price on any site.")

if __name__ == "__main__":
    main()
