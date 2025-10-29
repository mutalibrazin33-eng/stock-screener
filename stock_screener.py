import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="US Stock Screener v1.1", layout="wide")
st.title("📊 US Stock Screener v1.1 (Safe & Faster)")

# --- Filters ---
col1, col2, col3, col4 = st.columns(4)
min_volume = col1.number_input("📈 Min Daily Volume", 50000, step=10000)
min_adr = col2.number_input("⚡ Min ADR %", 4.0, step=0.5)
min_gain_1m = col3.number_input("📆 Min 1-Month Gain %", 50.0, step=5.0)
min_gain_3m = col4.number_input("🕒 Min 3-Month Gain %", 100.0, step=10.0)

tickers_input = st.text_area(
    "📜 Enter Comma-Separated Tickers (or leave default)", 
    "AAPL,TSLA,NVDA,AMZN,MSFT,META,AMD,NFLX,GOOG"
)

# --- Helper Functions ---
def adr_percent(df):
    return ((df["High"] - df["Low"]) / df["Close"]) * 100

def consolidation_score(df, lookback=10):
    recent = df.tail(lookback)
    return (recent["High"].max() - recent["Low"].min()) / recent["Close"].mean()

def fetch_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        df.dropna(inplace=True)
        if len(df) < 20:
            return pd.DataFrame()
        df["10SMA"] = df["Close"].rolling(10).mean()
        df["20SMA"] = df["Close"].rolling(20).mean()
        df["ADR%"] = adr_percent(df)
        return df
    except Exception:
        return pd.DataFrame()

def percent_change(df, days):
    if len(df) < days:
        return 0
    start = df["Close"].iloc[-days]
    end = df["Close"].iloc[-1]
    return ((end - start) / start) * 100

# --- Scan Button ---
if st.button("🔍 SCAN NOW"):
    tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
    results = []

    progress_text = "Scanning tickers..."
    my_bar = st.progress(0, text=progress_text)

    for i, tkr in enumerate(tickers):
        df = fetch_data(tkr)
        if df.empty:
            continue  # skip tickers with insufficient data

        avg_vol = df["Volume"].mean()
        avg_adr = df["ADR%"].mean()
        gain_1m = percent_change(df, 21)
        gain_3m = percent_change(df, 63)
        gain_6m = percent_change(df, 126)
        cons = consolidation_score(df)

        try:
            above_sma = df["Close"].iloc[-1] > df["10SMA"].iloc[-1] and df["Close"].iloc[-1] > df["20SMA"].iloc[-1]
        except:
            continue  # skip if SMA calculation fails

        if (
            avg_vol >= min_volume
            and avg_adr >= min_adr
            and gain_1m >= min_gain_1m
            and gain_3m >= min_gain_3m
            and above_sma
            and cons < 0.1
        ):
            results.append({
                "Ticker": tkr,
                "1M Gain %": round(gain_1m,1),
                "3M Gain %": round(gain_3m,1),
                "6M Gain %": round(gain_6m,1),
                "Avg Volume": int(avg_vol),
                "ADR %": round(avg_adr,2),
                "Consolidation": round(cons,3)
            })

        # Update progress bar
        my_bar.progress((i+1)/len(tickers), text=f"Scanning {tkr} ({i+1}/{len(tickers)})")

    my_bar.empty()  # remove progress bar

    if results:
        df_res = pd.DataFrame(results).sort_values("3M Gain %", ascending=False)
        st.success(f"✅ Found {len(df_res)} stocks matching filters")
        st.dataframe(df_res, use_container_width=True)

        sel = st.selectbox("📊 Select a Ticker to View Chart", df_res["Ticker"])
        dfc = fetch_data(sel)

        fig = go.Figure(
            data=[
                go.Candlestick(
                    x=dfc.index, open=dfc["Open"], high=dfc["High"], low=dfc["Low"], close=dfc["Close"], name="Price"
                ),
                go.Scatter(x=dfc.index, y=dfc["10SMA"], line=dict(color="orange"), name="10 SMA"),
                go.Scatter(x=dfc.index, y=dfc["20SMA"], line=dict(color="blue"), name="20 SMA"),
            ]
        )
        fig.update_layout(title=f"{sel} – Daily Chart", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("No stocks matched your filters.")
