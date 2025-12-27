import cloudscraper
import os
import re
import requests
from datetime import datetime
import pytz

# تنظیمات
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

def send_telegram(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ Error: Secrets missing!")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    requests.post(url, json=payload, timeout=10)

def get_data():
    scraper = cloudscraper.create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False}
    )
    
    # متغیرها
    cash_dollar = 0
    tether = 0
    btc = 0
    gold_ounce = 0
    silver_ounce = 0

    # ==========================================
    # 1. دریافت دلار کاغذی (از آلن‌چند یا نوسان)
    # ==========================================
    try:
        print("Fetching Cash Dollar...")
        resp = scraper.get("https://alanchand.com/currencies-price/usd", timeout=15)
        if resp.status_code == 200:
            text = resp.text
            # الگوی جستجوی دقیق برای اعداد ۵ تا ۱۰ رقمی
            match = re.search(r'دلار\s*آمریکا.*?([\d,]{5,10})', text, re.DOTALL)
            if match:
                cash_dollar = float(match.group(1).replace(',', ''))
            else:
                # بکاپ: جستجو در تایتل
                match_title = re.search(r'قیمت\s*دلار.*?([\d,]{5,10})', text)
                if match_title:
                    cash_dollar = float(match_title.group(1).replace(',', ''))
    except Exception as e:
        print(f"Dollar Error: {e}")

    # بکاپ دلار (نوسان)
    if cash_dollar == 0:
        try:
            resp = scraper.get("https://www.navasan.net/", timeout=15)
            match = re.search(r'id="usd_sell".*?>([\d,]+)<', resp.text)
            if match:
                cash_dollar = float(match.group(1).replace(',', ''))
        except: pass

    # ==========================================
    # 2. دریافت تتر (نوبیتکس / والکس)
    # ==========================================
    try:
        print("Fetching Tether...")
        # نوبیتکس
        resp = requests.get("https://api.nobitex.ir/market/stats?srcCurrency=usdt&dstCurrency=rls", timeout=10)
        data = resp.json()
        tether = float(data['stats']['usdt-rls']['bestSell']) / 10
    except:
        try:
            # والکس (بکاپ)
            resp = requests.get("https://api.wallex.ir/v1/markets", timeout=10)
            data = resp.json()
            tether = float(data['result']['symbols']['USDTTMN']['stats']['lastPrice'])
        except: pass

    # ==========================================
    # 3. دریافت بیت‌کوین (Coinbase)
    # ==========================================
    try:
        print("Fetching BTC...")
        resp = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=10)
        data = resp.json()
        btc = float(data['data']['amount'])
    except: pass

    # ==========================================
    # 4. دریافت انس طلا (Kraken)
    # ==========================================
    try:
        print("Fetching Gold Ounce...")
        resp = requests.get("https://api.kraken.com/0/public/Ticker?pair=PAXGUSD", timeout=10)
        data = resp.json()
        ticker = data['result'].get('PAXGUSD') or data['result'].get('XPAXGUSD')
        if ticker:
            gold_ounce = float(ticker['c'][0])
    except: pass

    # ==========================================
    # 5. دریافت انس نقره (Coinbase)
    # ==========================================
    try:
        print("Fetching Silver Ounce...")
        resp = requests.get("https://api.coinbase.com/v2/prices/XAG-USD/spot", timeout=10)
        data = resp.json()
        silver_ounce = float(data['data']['amount'])
    except: 
        # بکاپ نقره (Binance)
        try:
             resp = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=XAGUSDT", timeout=10)
             data = resp.json()
             silver_ounce = float(data['price'])
        except: pass

    return cash_dollar, tether, btc, gold_ounce, silver_ounce

def main():
    print("--- Running Combined Bot ---")
    cash, tether, btc, gold, silver = get_data()
    
    # اگر حداقل دلار یا تتر را داشتیم پیام بفرست
    if cash > 0 or tether > 0:
        tehran = pytz.timezone('Asia/Tehran')
        time_str = datetime.now(tehran).strftime("%H:%M")
        
        # فرمت دهی اعداد (۳ رقم ۳ رقم)
        fmt = lambda x: "{:,}".format(int(x)) if x > 0 else "---"
        fmt_dec = lambda x: "{:,.2f}".format(x) if x > 0 else "---"

        msg = (
            f"💰 **گزارش جامع بازار**\n\n"
            f"💵 **دلار آزاد:** {fmt(cash)} تومان\n"
            f"💎 **تتر:** {fmt(tether)} تومان\n\n"
            f"🌍 **انس طلا:** {fmt_dec(gold)} دلار\n"
            f"⚪️ **انس نقره:** {fmt_dec(silver)} دلار\n"
            f"🅱️ **بیت‌کوین:** {fmt_dec(btc)} دلار\n\n"
            f"⏰ ساعت: {time_str}"
        )
        
        send_telegram(msg)
        print("✅ Full Message Sent!")
    else:
        print("❌ Failed: No main prices found.")

if __name__ == "__main__":
    main()
