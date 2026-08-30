import os
import re
import sys
import cloudscraper
import requests
from bs4 import BeautifulSoup

# ===========================================================
# تنظیمات اتصال به کلودفلر
# ===========================================================
CLOUDFLARE_URL = os.getenv("CLOUDFLARE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

if not CLOUDFLARE_URL or not SECRET_KEY:
    print("❌ Error: CLOUDFLARE_URL or SECRET_KEY environment variables are missing!")
    sys.exit(1)
# ===========================================================

def normalize_digits(text: str) -> str:
    """تبدیل ارقام فارسی و عربی به انگلیسی"""
    if not text:
        return ""
    p_digits = '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩'
    e_digits = '01234567890123456789'
    return str(text).translate(str.maketrans(p_digits, e_digits))

def parse_price(text: str) -> float:
    """استخراج عدد تمیز قیمت"""
    clean_text = normalize_digits(text).replace(',', '')
    match = re.search(r'(\d{4,12})', clean_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    return 0.0

def parse_change(text: str) -> str:
    """استخراج درصد تغییرات"""
    clean_text = normalize_digits(text).replace('٪', '%')
    match = re.search(r'([-+]?\s*\d*\.?\d+\s*%)', clean_text)
    if match:
        return match.group(1).replace(" ", "")
    return ""

def to_toman_currency(val: float) -> float:
    """تبدیل ریال به تومان برای ارزها (اگر بالای ۱ میلیون ریال باشد)"""
    if val >= 1_000_000:
        return val / 10.0
    return val

def to_toman_gold(val: float) -> float:
    """تبدیل ریال به تومان برای طلا و سکه (اگر بالای ۵۰۰ میلیون ریال باشد)"""
    if val >= 500_000_000:
        return val / 10.0
    return val

def get_oil_price(ticker: str) -> float:
    """دریافت قیمت جهانی نفت"""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            return float(data['chart']['result'][0]['meta']['regularMarketPrice'])
    except Exception as e:
        print(f"⚠️ Error fetching oil price for {ticker}: {e}")
    return 0.0

def scrape_alanchand():
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )

    data = {
        "currencies": {
            "usd": {"price": 0.0, "change": ""},
            "eur": {"price": 0.0, "change": ""},
            "gbp": {"price": 0.0, "change": ""}
        },
        "gold_coins": {
            "mesghal": {"price": 0.0, "change": ""},
            "emami": {"price": 0.0, "change": ""},
            "bahar": {"price": 0.0, "change": ""},
            "nim": {"price": 0.0, "change": ""},
            "rob": {"price": 0.0, "change": ""}
        },
        "source": "AlanChand"
    }

    try:
        print("🔍 Scraping AlanChand Tables...")
        resp = scraper.get("https://alanchand.com/", timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # بررسی تک تک سطرهای جدول به صورت ایزوله
            for tr in soup.find_all('tr'):
                cells = tr.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue

                row_title = cells[0].get_text(strip=True)
                row_full = tr.get_text(separator=' ', strip=True)

                # استخراج درصد تغییرات سطر
                change_val = parse_change(row_full)

                # استخراج ارقام ستون‌های قیمت
                prices = []
                for td in cells[1:]:
                    p = parse_price(td.get_text(strip=True))
                    if p > 0:
                        prices.append(p)

                if not prices:
                    continue

                # آخرین قیمت معمولاً قیمت فروش است
                target_price = prices[-1]

                # ۱. ارزها
                if row_title == "دلار آمریکا" or ("دلار" in row_title and "آمریکا" in row_title and "حواله" not in row_title and "استرالیا" not in row_title and "کانادا" not in row_title):
                    if data["currencies"]["usd"]["price"] == 0:
                        data["currencies"]["usd"]["price"] = to_toman_currency(target_price)
                        data["currencies"]["usd"]["change"] = change_val

                elif row_title == "یورو" or ("یورو" in row_title and "حواله" not in row_title and "استامبول" not in row_title):
                    if data["currencies"]["eur"]["price"] == 0:
                        data["currencies"]["eur"]["price"] = to_toman_currency(target_price)
                        data["currencies"]["eur"]["change"] = change_val

                elif row_title == "پوند انگلیس" or ("پوند" in row_title and "حواله" not in row_title):
                    if data["currencies"]["gbp"]["price"] == 0:
                        data["currencies"]["gbp"]["price"] = to_toman_currency(target_price)
                        data["currencies"]["gbp"]["change"] = change_val

                # ۲. طلا و سکه
                elif "آبشده" in row_title or "مثقال" in row_title:
                    if data["gold_coins"]["mesghal"]["price"] == 0:
                        data["gold_coins"]["mesghal"]["price"] = to_toman_gold(target_price)
                        data["gold_coins"]["mesghal"]["change"] = change_val

                elif "امامی" in row_title or "طرح جدید" in row_title:
                    if data["gold_coins"]["emami"]["price"] == 0:
                        data["gold_coins"]["emami"]["price"] = to_toman_gold(target_price)
                        data["gold_coins"]["emami"]["change"] = change_val

                elif "بهار آزادی" in row_title or "طرح قدیم" in row_title:
                    if data["gold_coins"]["bahar"]["price"] == 0:
                        data["gold_coins"]["bahar"]["price"] = to_toman_gold(target_price)
                        data["gold_coins"]["bahar"]["change"] = change_val

                elif "نیم سکه" in row_title:
                    if data["gold_coins"]["nim"]["price"] == 0:
                        data["gold_coins"]["nim"]["price"] = to_toman_gold(target_price)
                        data["gold_coins"]["nim"]["change"] = change_val

                elif "ربع سکه" in row_title:
                    if data["gold_coins"]["rob"]["price"] == 0:
                        data["gold_coins"]["rob"]["price"] = to_toman_gold(target_price)
                        data["gold_coins"]["rob"]["change"] = change_val

    except Exception as e:
        print(f"⚠️ Table scrap error: {e}")

    # فال‌بک برای دلار در صورت ناقص بودن
    if data["currencies"]["usd"]["price"] == 0:
        try:
            print("🔍 Fetching USD fallback page...")
            resp = scraper.get("https://alanchand.com/currencies-price/usd", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                meta_desc = soup.find("meta", property="og:description") or soup.find("meta", attrs={"name": "description"})
                if meta_desc and meta_desc.get("content"):
                    p = parse_price(meta_desc["content"])
                    if p > 0:
                        data["currencies"]["usd"]["price"] = to_toman_currency(p)
                        data["currencies"]["usd"]["change"] = parse_change(meta_desc["content"])
        except Exception as e:
            print(f"⚠️ USD fallback error: {e}")

    return data

def send_to_cloudflare(payload):
    print("🚀 Sending Correct Market Data to Cloudflare...")
    try:
        headers = {
            "X-Secret-Key": SECRET_KEY,
            "Content-Type": "application/json"
        }
        resp = requests.post(CLOUDFLARE_URL, json=payload, headers=headers, timeout=20)
        if resp.status_code == 200:
            print("✅ Data sent to Cloudflare successfully!")
        else:
            print(f"❌ Cloudflare Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def main():
    print("--- GitHub Scraper Started ---")
    market_data = scrape_alanchand()

    brent = get_oil_price("BZ=F")
    wti = get_oil_price("CL=F")
    
    usd_price = market_data["currencies"]["usd"]["price"]
    print(f"Extracted -> USD: {usd_price:,.0f} Toman, EUR: {market_data['currencies']['eur']['price']:,.0f} Toman, GBP: {market_data['currencies']['gbp']['price']:,.0f} Toman")

    payload = {
        "price": usd_price,
        "source": market_data["source"],
        "currencies": market_data["currencies"],
        "gold_coins": market_data["gold_coins"],
        "brent": brent,
        "wti": wti
    }

    if usd_price > 0:
        send_to_cloudflare(payload)
    else:
        print("❌ FAILED: USD price is 0.")

if __name__ == "__main__":
    main()
