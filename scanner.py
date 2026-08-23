import yfinance as yf
import pandas as pd
import requests
import io

# הגדרות הבוט שלך ישירות בקוד
TELEGRAM_TOKEN = "8948426809:AAG5Kzm9e2R1NLnmS737"
CHAT_ID = "640397492"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        print("תשובת טלגרם:", response.text)
        return response.json()
    except Exception as e:
        print(f"שגיאה בשליחת הודעה: {e}")

def get_all_us_tickers():
    try:
        url = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
        s = requests.get(url, timeout=15).content
        nasdaq = pd.read_csv(io.BytesIO(s), sep='|')
        
        url_other = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"
        s_other = requests.get(url_other, timeout=15).content
        other = pd.read_csv(io.BytesIO(s_other), sep='|')
        
        tickers = list(nasdaq['Symbol'].dropna()) + list(other['NASDAQ Symbol'].dropna())
        clean_tickers = [t.strip() for t in tickers if isinstance(t, str) and '^' not in t and '.' not in t and '$' not in t]
        return list(set(clean_tickers))
    except Exception as e:
        print(f"שגיאה בהורדת רשימת המניות: {e}")
        return ["AAPL", "AMD", "TSLA", "F", "PLTR"]

def scan_momentum_stocks():
    print("מוריד את רשימת כל המניות בבורסה...")
    tickers_to_check = get_all_us_tickers()
    print(f"נמצאו {len(tickers_to_check)} מניות לסריקה. מתחיל בדיקה...")
    
    results = []
    
    for ticker in tickers_to_check[:1500]:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="5d", timeout=5)
            
            if hist.empty or len(hist) < 2:
                continue
                
            price = hist['Close'].iloc[-1]
            
            if price >= 10:
                continue
                
            volume = hist['Volume'].iloc[-1]
            if volume <= 500_000:
                continue
                
            info = stock.info
            float_shares = info.get('floatShares', 0)
            
            if 0 < float_shares < 20_000_000:
                prev_close = hist['Close'].iloc[-2]
                change_pct = ((price - prev_close) / prev_close) * 100
                
                results.append({
                    "Ticker": ticker,
                    "Price": round(price, 2),
                    "Change %": round(change_pct, 2),
                    "Volume": volume,
                    "Float (M)": round(float_shares / 1_000_000, 2)
                })
        except Exception:
            continue
            
    df = pd.DataFrame(results)
    
    if not df.empty:
        df = df.sort_values(by="Change %", ascending=False)
        df_top = df.head(20)
        msg = "🚨 *תוצאות סורק המומנטום* 🚨\n\n```\n" + df_top.to_string(index=False) + "\n```"
    else:
        msg = "סורק המומנטום סיים את הבדיקה: לא נמצאו מניות העונות על הקריטריונים היום."
        
    send_telegram_message(msg)
    print("התהליך הסתיים!")

scan_momentum_stocks()
