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
    if val >= 1_000_000:
        return val / 10.0
    return val

def to_toman_gold(val: float) -> float:
    if val >= 500_000_000:
        return val / 10.0
    return val

def get_market_quote(ticker: str) -> float:
    """دریافت قیمت نفت و انس نقره از یاهو فایننس"""
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
        print(f"⚠️ Error fetching {ticker}: {e}")
    return 0.0

def parse_gold_elements(soup, data):
    """پارس جدول و المان‌های اختصاصی طلا و سکه"""
    # ۱. بررسی جداول
    for tr in soup.find_all('tr'):
        cells = tr.find_all(['td', 'th'])
        if len(cells) < 2:
            continue
        row_title = cells[0].get_text(strip=True)
        cell_text = tr.get_text(separator=' ', strip=True)
        p = parse_price(cell_text)
        ch = parse_change(cell_text)

        if ("آبشده" in row_title or "مثقال" in row_title) and data["gold_coins"]["mesghal"]["price"] == 0:
            if p > 1000000:
                data["gold_coins"]["mesghal"]["price"] = to_toman_gold(p)
                data["gold_coins"]["mesghal"]["change"] = ch

        elif ("امامی" in row_title or "طرح جدید" in row_title) and data["gold_coins"]["emami"]["price"] == 0:
            if p > 1000000:
                data["gold_coins"]["emami"]["price"] = to_toman_gold(p)
                data["gold_coins"]["emami"]["change"] = ch

        elif ("بهار آزادی" in row_title or "طرح قدیم" in row_title) and data["gold_coins"]["bahar"]["price"] == 0:
            if p > 1000000:
                data["gold_coins"]["bahar"]["price"] = to_toman_gold(p)
                data["gold_coins"]["bahar"]["change"] = ch

        elif ("نیم سکه" in row_title or "نیم‌سکه" in row_title) and data["gold_coins"]["nim"]["price"] == 0:
            if p > 500000:
                data["gold_coins"]["nim"]["price"] = to_toman_gold(p)
                data["gold_coins"]["nim"]["change"] = ch

        elif ("ربع سکه" in row_title or "ربع‌سکه" in row_title) and data["gold_coins"]["rob"]["price"] == 0:
            if p > 300000:
                data["gold_coins"]["rob"]["price"] = to_toman_gold(p)
                data["gold_coins"]["rob"]["change"] = ch

    # ۲. بررسی کارت‌ها و بلاک‌های متنی
    for el in soup.find_all(['div', 'li', 'a', 'p']):
        txt = el.get_text(separator=' ', strip=True)
        if len(txt) > 120:
            continue
        p = parse_price(txt)
        if p == 0:
            continue
        ch = parse_change(txt)

        if ("آبشده" in txt or "مثقال طلا" in txt) and data["gold_coins"]["mesghal"]["price"] == 0:
            if p > 1000000:
                data["gold_coins"]["mesghal"]["price"] = to_toman_gold(p)
                data["gold_coins"]["mesghal"]["change"] = ch

        elif ("سکه امامی" in txt or "طرح جدید" in txt) and data["gold_coins"]["emami"]["price"] == 0:
            if p > 1000000:
                data["gold_coins"]["emami"]["price"] = to_toman_gold(p)
                data["gold_coins"]["emami"]["change"] = ch

        elif ("بهار آزادی" in txt or "طرح قدیم" in txt) and data["gold_coins"]["bahar"]["price"] == 0:
            if p > 1000000:
                data["gold_coins"]["bahar"]["price"] = to_toman_gold(p)
                data["gold_coins"]["bahar"]["change"] = ch

        elif ("نیم سکه" in txt or "نیم‌سکه" in txt) and data["gold_coins"]["nim"]["price"] == 0:
            if p > 500000:
                data["gold_coins"]["nim"]["price"] = to_toman_gold(p)
                data["gold_coins"]["nim"]["change"] = ch

        elif ("ربع سکه" in txt or "ربع‌سکه" in txt) and data["gold_coins"]["rob"]["price"] == 0:
            if p > 300000:
                data["gold_coins"]["rob"]["price"] = to_toman_gold(p)
                data["gold_coins"]["rob"]["change"] = ch

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

    # ۱. اسکرپ صفحه اصلی برای ارزها
    try:
        print("🔍 1. Scraping Currencies from AlanChand...")
        resp = scraper.get("https://alanchand.com/", timeout=20)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for tr in soup.find_all('tr'):
                cells = tr.find_all(['td', 'th'])
                if len(cells) < 2:
                    continue
                row_title = cells[0].get_text(strip=True)
                row_full = tr.get_text(separator=' ', strip=True)
                change_val = parse_change(row_full)
                prices = [parse_price(td.get_text(strip=True)) for td in cells[1:] if parse_price(td.get_text(strip=True)) > 0]
                if not prices:
                    continue
                target_price = prices[-1]

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

            # بررسی طلا و سکه موجود در صفحه اصلی
            parse_gold_elements(soup, data)
    except Exception as e:
        print(f"⚠️ Main page error: {e}")

    # ۲. اسکرپ مستقیم صفحه اختصاصی طلا و سکه (gold-price)
    if any(v["price"] == 0 for v in data["gold_coins"].values()):
        try:
            print("🔍 2. Scraping Gold & Coins from https://alanchand.com/gold-price...")
            resp = scraper.get("https://alanchand.com/gold-price", timeout=20)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                parse_gold_elements(soup, data)
        except Exception as e:
            print(f"⚠️ Gold page error: {e}")

    return data

def send_to_cloudflare(payload):
    print("🚀 Sending Full Market Data to Cloudflare...")
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

    # استخراج نفت و انس نقره از یاهو فایننس
    brent = get_market_quote("BZ=F")
    wti = get_market_quote("CL=F")
    silver = get_market_quote("SI=F")
    
    usd_price = market_data["currencies"]["usd"]["price"]
    print(f"Currencies -> USD: {usd_price:,.0f}, EUR: {market_data['currencies']['eur']['price']:,.0f}, GBP: {market_data['currencies']['gbp']['price']:,.0f}")
    print(f"Gold/Coins -> Mesghal: {market_data['gold_coins']['mesghal']['price']:,.0f}, Emami: {market_data['gold_coins']['emami']['price']:,.0f}, Bahar: {market_data['gold_coins']['bahar']['price']:,.0f}")
    print(f"Commodities -> Brent: {brent}$, WTI: {wti}$, Silver: {silver}$")

    payload = {
        "price": usd_price,
        "source": market_data["source"],
        "currencies": market_data["currencies"],
        "gold_coins": market_data["gold_coins"],
        "brent": brent,
        "wti": wti,
        "silver": silver
    }

    if usd_price > 0:
        send_to_cloudflare(payload)
    else:
        print("❌ FAILED: USD price is 0.")

if __name__ == "__main__":
    main()
