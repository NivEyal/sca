import requests
from bs4 import BeautifulSoup
import re
import streamlit as st

@st.cache_data(ttl=300)
def scrape_google_finance_clean(ticker):
    url = f"https://www.google.com/finance/quote/{ticker}:NASDAQ"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        res = requests.get(url, headers=headers, timeout=10)
        print(f"[DEBUG] Status Code for {ticker}: {res.status_code}")
        
        if res.status_code != 200:
            print(f"[ERROR] Failed to fetch {url}")
            return {
                "ticker": ticker,
                "after_price": None,
                "after_change": None,
                "after_pct": None
            }

        soup = BeautifulSoup(res.text, 'html.parser')
        raw_text = soup.get_text(separator=" ", strip=True)
        print(f"[DEBUG] Raw Text for {ticker}:\n{raw_text[:500]}...\n")  # רק ההתחלה

        # חיפוש מחיר נוכחי
        price_match = re.search(r"\$(\d{1,4}\.\d{2})(?=After Hours|Closed)", raw_text)
        current_price = f"${price_match.group(1)}" if price_match else "לא נמצא"
        print(f"[DEBUG] Current Price Match: {current_price}")

        # חיפוש after hours
        after_match = re.search(r"After Hours:\$(\d{1,4}\.\d{2})\(([-\d.]+%)\)([-\d.]+)?", raw_text)
        if after_match:
            after_price = f"${after_match.group(1)}"
            after_percent = after_match.group(2)
            after_dollar = after_match.group(3) if after_match.group(3) else "N/A"

            print(f"[DEBUG] After-Hours Match: price={after_price}, pct={after_percent}, delta={after_dollar}")

            # תיקון סימן מינוס אם חסר
            if after_dollar.startswith("-") and not after_percent.startswith("-"):
                after_percent = f"-{after_percent}"
        else:
            print(f"[INFO] No After-Hours match found for {ticker}")
            after_price = None
            after_dollar = None
            after_percent = None

        return {
            "ticker": ticker,
            "after_price": after_price,
            "after_change": after_dollar,
            "after_pct": after_percent
        }

    except Exception as e:
        print(f"[ERROR] Exception while scraping {ticker}: {e}")
        return {
            "ticker": ticker,
            "after_price": None,
            "after_change": None,
            "after_pct": None
        }
