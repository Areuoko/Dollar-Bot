import cloudscraper
import re
import requests
import os
import sys
from bs4 import BeautifulSoup

# ===========================================================
# تنظیمات اتصال به کلودفلر (خواندن ۱۰۰٪ امن از گیت‌هاب سکرت)
# ===========================================================
CLOUDFLARE_URL = os.getenv("CLOUDFLARE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

# بررسی وجود متغیرهای حیاتی برای جلوگیری از کرش بیهوده یا ارسال ناموفق
if not CLOUDFLARE_URL or not SECRET_KEY:
    print("❌ Error: CLOUDFLARE_URL or SECRET_KEY environment variables are missing!")
    sys.exit(1)
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
    persian_digits = '۰۱۲۳۴۵۶۷۸۹'
    english_digits = '0123456789'
    translation_table = str.maketrans(persian_digits, english_digits)
    text_val = text_val.translate(translation_table)
    
    match = re.search(r'([\d,]{5,10})', text_val)
    if match:
        clean_str = match.group(1).replace(',', '')
        try:
            return float(clean_str)
        except ValueError:
            return 0
    return 0
    
def get_oil_price(ticker):
    """دریافت قیمت نفت (برنت یا WTI) از یاهو فایننس"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # استخراج قیمت فعلی بازار از ساختار جی‌سان یاهو
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return float(price)
    except Exception as e:
        print(f"Error fetching oil price for {ticker}: {e}")
    return 0.0

def get_cash_price():
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    price = 0
    source = ""

    # -----------------------------------------------------------
    # تلاش ۱: آلن‌چند (AlanChand)
    # -----------------------------------------------------------
    try:
        print("Checking AlanChand...")
        resp = scraper.get("https://alanchand.com/currencies-price/usd", timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            for script in soup(["script", "style"]):
                script.extract()

            meta_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
            if meta_desc and meta_desc.get("content"):
                extracted = parse_price_string(meta_desc["content"])
                if extracted > 10000:
                    price = extracted
                    source = "AlanChand (Meta)"

            if price == 0:
                text_content = soup.get_text(separator=' ')
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
                
                usd_elem = soup.find(id="usd_sell") or soup.find(class_="usd_sell")
                if usd_elem:
                    extracted = parse_price_string(usd_elem.text)
                    if extracted > 10000:
                        price = extracted
                        source = "Navasan"
                else:
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
