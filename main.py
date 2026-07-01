import cloudscraper
import re
import requests
import os

# ===========================================================
# تنظیمات اتصال به کلودفلر
# ===========================================================
CLOUDFLARE_URL = os.environ.get("CLOUDFLARE_URL", "https://golden-bot.tilapila007.workers.dev/")
SECRET_KEY = os.environ.get("SECRET_KEY", "")
# ===========================================================

def send_to_cloudflare(price, source):
    if not SECRET_KEY:
        print("❌ SECRET_KEY is not set. Cannot send data to Cloudflare.")
        return
    
    print(f"🚀 Sending Price ({price}) from {source} to Cloudflare...")
    
    try:
        payload = {
            "price": price,
            "source": source
        }
        # هدر امنیتی برای اینکه کلودفلر بفهمد ما خودی هستیم
        headers = {
            "X-Secret-Key": SECRET_KEY,
            "Content-Type": "application/json"
        }
        
        # ارسال درخواست به کلودفلر
        resp = requests.post(CLOUDFLARE_URL, json=payload, headers=headers, timeout=20)
        
        if resp.status_code == 200:
            print("✅ Data sent to Cloudflare successfully!")
            print(f"Response: {resp.text}")
        else:
            print(f"❌ Cloudflare Error: {resp.status_code}")
            print(f"Details: {resp.text}")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def get_cash_price():
    # ساخت مرورگر جعلی برای عبور از فایروال
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    price = 0
    source = ""

    # -----------------------------------------------------------
    # تلاش ۱: آلن‌چند (AlanChand HTML)
    # -----------------------------------------------------------
    if price == 0:
        try:
            print("Checking AlanChand...")
            resp = scraper.get("https://alanchand.com/currencies-price/usd", timeout=20)
            if resp.status_code == 200:
                text = resp.text
                # الگوی جستجوی دقیق برای اعداد ۵ تا ۱۰ رقمی (پشتیبانی از قیمت‌های بالای ۱۰۰ هزار)
                match = re.search(r'دلار\s*آمریکا.*?([\d,]{5,10})', text, re.DOTALL)
                
                if match:
                    price = float(match.group(1).replace(',', ''))
                    source = "AlanChand"
                else:
                    # بکاپ: جستجو در تایتل صفحه
                    match_title = re.search(r'قیمت\s*دلار.*?([\d,]{5,10})', text)
                    if match_title:
                        price = float(match_title.group(1).replace(',', ''))
                        source = "AlanChand (Title)"
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
                text = resp.text
                match = re.search(r'id="usd_sell".*?>([\d,]+)<', text)
                if match:
                    price = float(match.group(1).replace(',', ''))
                    source = "Navasan"
        except Exception as e:
            print(f"Navasan Error: {e}")

    return price, source

def main():
    print("--- GitHub Scraper Started ---")
    
    # ۱. پیدا کردن قیمت دلار
    price, source = get_cash_price()
    
    # ۲. ارسال به کلودفلر (اگر قیمت پیدا شد)
    if price > 0:
        send_to_cloudflare(price, source)
    else:
        print("❌ FAILED: Could not find cash price on any site.")

if __name__ == "__main__":
    main()
