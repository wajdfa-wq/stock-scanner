import yfinance as yf
import pandas as pd
import requests
import io
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# שליפת פרטי המייל מתוך ה-Secrets של GitHub
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def send_email(message_body):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("שגיאה: פרטי המייל לא הוגדרו כהלכה ב-Secrets של GitHub.")
        return

    recipient = EMAIL_USER  # שולח את המייל אל עצמך
    subject = "🚨 תוצאות סורק המומנטום 🚨"

    msg = MIMEMultipart()
    msg['From'] = EMAIL_USER
    msg['To'] = recipient
    msg['Subject'] = subject

    msg.attach(MIMEText(message_body, 'plain', 'utf-8'))

    try:
        # התחברות מאובטחת לשרת ה-SMTP של Gmail
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.sendmail(EMAIL_USER, recipient, msg.as_string())
        server.quit()
        print("המייל נשלח בהצלחה תיבת הדואר שלך!")
    except Exception as e:
        print(f"שגיאה בשליחת המייל: {e}")

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
        msg = "תוצאות סורק המומנטום:\n\n" + df_top.to_string(index=False)
    else:
        msg = "סורק המומנטום סיים את הבדיקה: לא נמצאו מניות העונות על הקריטריונים היום."
        
    send_email(msg)
    print("התהליך הסתיים!")

scan_momentum_stocks()
