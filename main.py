import os
import re
import sys
import cloudscraper
import requests
from bs4 import BeautifulSoup

# ===========================================================
# تنظیمات اتصال به کلودفلر (خواندن از سکرت‌های گیت‌هاب)
# ===========================================================
CLOUDFLARE_URL = os.getenv("CLOUDFLARE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")

if not CLOUDFLARE_URL or not SECRET_KEY:
    print("❌ Error: CLOUDFLARE_URL or SECRET_KEY environment variables are missing!")
    sys.exit(1)
# ===========================================================

def normalize_digits(text: str) -> str:
    """تبدیل تمام ارقام فارسی و عربی به انگلیسی"""
    if not text:
        return ""
    p_digits = '۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩'
    e_digits = '01234567890123456789'
    trans = str.maketrans(p_digits, e_digits)
    return str(text).translate(trans)

def parse_price(text: str) -> float:
    """استخراج عدد قیمت از متن با فیلتر کاما و تبدیل به اعشاری"""
    clean_text = normalize_digits(text).replace(',', '')
    match = re.search(r'(\d{4,12})', clean_text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return 0.0
    return 0.0

def parse_change(text: str) -> str:
    """استخراج درصد یا مقدار تغییرات از متن"""
    clean_text = normalize_digits(text).replace('٪', '%')
    match = re.search(r'([-+]?\s*\d*\.?\d+\s*%)', clean_text)
    if match:
        return match.group(1).replace(" ", "")
    return ""

def get_oil_price(ticker: str) -> float:
    """دریافت قیمت نفت (برنت یا WTI) از یاهو فایننس"""
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
    """استخراج کامل ارزها و سکه‌ها با درصد تغییرات از سایت الان‌چند"""
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
        print("🔍 Scraping AlanChand (Main & Markets)...")
        resp = scraper.get("https://alanchand.com/", timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tag in soup(["script", "style", "noscript"]):
                tag.extract()

            rows = soup.find_all(['tr', 'div', 'li'])
            for row in rows:
                row_text = row.get_text(separator=' ', strip=True)

                # --- ۱. ارزها ---
                # دلار
                if "دلار آمریکا" in row_text and data["currencies"]["usd"]["price"] == 0:
                    prices = re.findall(r'[\d,]{5,10}', normalize_digits(row_text))
                    if prices:
                        data["currencies"]["usd"]["price"] = float(prices[-1].replace(',', ''))
                        data["currencies"]["usd"]["change"] = parse_change(row_text)

                # یورو
                elif "یورو" in row_text and "حواله" not in row_text and data["currencies"]["eur"]["price"] == 0:
                    prices = re.findall(r'[\d,]{5,10}', normalize_digits(row_text))
                    if prices:
                        data["currencies"]["eur"]["price"] = float(prices[-1].replace(',', ''))
                        data["currencies"]["eur"]["change"] = parse_change(row_text)

                # پوند
                elif "پوند" in row_text and "حواله" not in row_text and data["currencies"]["gbp"]["price"] == 0:
                    prices = re.findall(r'[\d,]{5,10}', normalize_digits(row_text))
                    if prices:
                        data["currencies"]["gbp"]["price"] = float(prices[-1].replace(',', ''))
                        data["currencies"]["gbp"]["change"] = parse_change(row_text)

                # --- ۲. طلا و سکه ---
                # آبشده (مثقال طلا)
                if ("آبشده" in row_text or "مثقال طلا" in row_text) and data["gold_coins"]["mesghal"]["price"] == 0:
                    price = parse_price(row_text)
                    if price > 1000000:
                        data["gold_coins"]["mesghal"]["price"] = price
                        data["gold_coins"]["mesghal"]["change"] = parse_change(row_text)

                # سکه امامی (طرح جدید)
                elif ("سکه امامی" in row_text or "طرح جدید" in row_text) and data["gold_coins"]["emami"]["price"] == 0:
                    price = parse_price(row_text)
                    if price > 1000000:
                        data["gold_coins"]["emami"]["price"] = price
                        data["gold_coins"]["emami"]["change"] = parse_change(row_text)

                # سکه بهار آزادی (طرح قدیم)
                elif ("بهار آزادی" in row_text or "طرح قدیم" in row_text) and data["gold_coins"]["bahar"]["price"] == 0:
                    price = parse_price(row_text)
                    if price > 1000000:
                        data["gold_coins"]["bahar"]["price"] = price
                        data["gold_coins"]["bahar"]["change"] = parse_change(row_text)

                # نیم سکه
                elif "نیم سکه" in row_text and data["gold_coins"]["nim"]["price"] == 0:
                    price = parse_price(row_text)
                    if price > 500000:
                        data["gold_coins"]["nim"]["price"] = price
                        data["gold_coins"]["nim"]["change"] = parse_change(row_text)

                # ربع سکه
                elif "ربع سکه" in row_text and data["gold_coins"]["rob"]["price"] == 0:
                    price = parse_price(row_text)
                    if price > 300000:
                        data["gold_coins"]["rob"]["price"] = price
                        data["gold_coins"]["rob"]["change"] = parse_change(row_text)

    except Exception as e:
        print(f"⚠️ AlanChand Scraper Error: {e}")

    # فال‌بک تکمیلی صفحه اختصاصی طلا در صورت ناقص بودن داده‌ها
    if any(v["price"] == 0 for v in data["gold_coins"].values()):
        try:
            print("🔍 Fetching Gold & Coin Subpage Fallback...")
            resp = scraper.get("https://alanchand.com/gold-price", timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                rows = soup.find_all(['tr', 'div', 'li'])
                for row in rows:
                    txt = row.get_text(separator=' ', strip=True)
                    if ("آبشده" in txt or "مثقال" in txt) and data["gold_coins"]["mesghal"]["price"] == 0:
                        data["gold_coins"]["mesghal"]["price"] = parse_price(txt)
                        data["gold_coins"]["mesghal"]["change"] = parse_change(txt)
                    elif "سکه امامی" in txt and data["gold_coins"]["emami"]["price"] == 0:
                        data["gold_coins"]["emami"]["price"] = parse_price(txt)
                        data["gold_coins"]["emami"]["change"] = parse_change(txt)
                    elif "بهار آزادی" in txt and data["gold_coins"]["bahar"]["price"] == 0:
                        data["gold_coins"]["bahar"]["price"] = parse_price(txt)
                        data["gold_coins"]["bahar"]["change"] = parse_change(txt)
                    elif "نیم سکه" in txt and data["gold_coins"]["nim"]["price"] == 0:
                        data["gold_coins"]["nim"]["price"] = parse_price(txt)
                        data["gold_coins"]["nim"]["change"] = parse_change(txt)
                    elif "ربع سکه" in txt and data["gold_coins"]["rob"]["price"] == 0:
                        data["gold_coins"]["rob"]["price"] = parse_price(txt)
                        data["gold_coins"]["rob"]["change"] = parse_change(txt)
        except Exception as e:
            print(f"⚠️ Gold subpage fallback error: {e}")

    return data

def send_to_cloudflare(payload):
    print("🚀 Sending Market Data to Cloudflare...")
    try:
        headers = {
            "X-Secret-Key": SECRET_KEY,
            "Content-Type": "application/json"
        }
        resp = requests.post(CLOUDFLARE_URL, json=payload, headers=headers, timeout=20)
        if resp.status_code == 200:
            print("✅ Data sent to Cloudflare successfully!")
            print(f"Response: {resp.text}")
        else:
            print(f"❌ Cloudflare Error: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Connection Error: {e}")

def main():
    print("--- GitHub Scraper Started ---")
    market_data = scrape_alanchand()

    brent = get_oil_price("BZ=F")
    wti = get_oil_price("CL=F")
    print(f"Oil prices -> Brent: {brent}$, WTI: {wti}$")

    payload = {
        "price": market_data["currencies"]["usd"]["price"],  # حفظ سازگاری
        "source": market_data["source"],
        "currencies": market_data["currencies"],
        "gold_coins": market_data["gold_coins"],
        "brent": brent,
        "wti": wti
    }

    if payload["price"] > 0 or payload["currencies"]["eur"]["price"] > 0:
        send_to_cloudflare(payload)
    else:
        print("❌ FAILED: Could not find valid prices.")

if __name__ == "__main__":
    main()
