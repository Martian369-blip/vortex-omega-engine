import os
import datetime
import requests
import yfinance as yf
import pandas as pd
import numpy as np

# 🔑 CRITICAL CORE CONFIGURATIONS
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

META_API_TOKEN = os.getenv("META_API_TOKEN")
META_ACCOUNT_ID = os.getenv("META_ACCOUNT_ID")
META_URL = f"https://agiliumtrade.ai{META_ACCOUNT_ID}"

RISK_PERCENT = 0.01

MARKET_MAP = {
    "USDZAR=X": {"name": "USD/ZAR", "symbol": "USDZAR"},
    "GBPUSD=X": {"name": "GBP/USD", "symbol": "GBPUSD"},
    "GC=F": {"name": "Gold", "symbol": "XAUUSD"},
    "EURUSD=X": {"name": "EUR/USD", "symbol": "EURUSD"},
    "USDJPY=X": {"name": "USD/JPY", "symbol": "USDJPY"},
    "AUDUSD=X": {"name": "AUD/USD", "symbol": "AUDUSD"},
    "USDCAD=X": {"name": "USD/CAD", "symbol": "USDCAD"}
}

def get_mt4_account_equity():
    headers = {"auth-token": META_API_TOKEN, "Content-Type": "application/json"}
    try:
        res = requests.get(f"{META_URL}/account-information", headers=headers, timeout=10)
        if res.status_code == 200: return float(res.json().get("equity", 1000.0))
    except Exception: pass
    return 1000.0

def execute_mt4_order(symbol, action, lots, sl_price, tp_price):
    url = f"{META_URL}/trade"
    headers = {"auth-token": META_API_TOKEN, "Content-Type": "application/json"}
    order_type = "ORDER_TYPE_BUY" if action == "BUY" else "ORDER_TYPE_SELL"
    payload = {
        "actionType": "ORDER_TYPE_MARKET", "symbol": symbol, "orderType": order_type,
        "volume": float(lots), "stopLoss": round(float(sl_price), 4), "takeProfit": round(float(tp_price), 4)
    }
    try: return requests.post(url, json=payload, headers=headers, timeout=10).status_code == 200
    except Exception: return False

def calculate_bollinger_bands(df, window=20, num_std=2):
    rolling_mean = df['Close'].rolling(window=window).mean()
    rolling_std = df['Close'].rolling(window=window).std()
    return rolling_mean + (rolling_std * num_std), rolling_mean, rolling_mean - (rolling_std * num_std)

def calculate_atr(df, window=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1).rolling(window=window).mean()

def send_telegram_broadcast(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://telegram.org{TELEGRAM_BOT_TOKEN}/sendMessage"
    try: requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}, timeout=10)
    except Exception: pass

live_equity = get_mt4_account_equity()
print(f"🌀 Initiating VORTEX_OMEGA System Scan. Equity Baseline: {live_equity}")

for market_key, asset_data in MARKET_MAP.items():
    try:
        feed = yf.Ticker(market_key)
        df_30m = feed.history(period="5d", interval="30m")
        if not df_30m.empty and len(df_30m) >= 20:
            current_price = df_30m['Close'].iloc[-1]
            upper_30m, _, lower_30m = calculate_bollinger_bands(df_30m)
            last_atr = calculate_atr(df_30m).iloc[-1]
            last_upper, last_lower = upper_30m.iloc[-1], lower_30m.iloc[-1]
            
            prev_close = df_30m['Close'].iloc[-2]
            is_gap_volatile = np.abs(current_price - prev_close) > last_atr
            risk_mult = 0.5 if is_gap_volatile else 1.0
            gap_warning = "⚠️ *HIGH-RISK SUNDAY OPEN GAP! VOLUME DOWNSIZED 50%.*\n\n" if is_gap_volatile else ""
            
            if current_price < last_lower and (df_30m['High'].iloc[-1] - df_30m['Low'].iloc[-1]) > (1.5 * last_atr):
                stop_distance = last_atr * (2.5 if is_gap_volatile else 2.0)
                sl, tp1 = current_price - stop_distance, current_price + (stop_distance * 1.5)
                rec_lot = max(0.01, round((live_equity * RISK_PERCENT * risk_mult) / (stop_distance * 1000 if stop_distance > 0 else 1), 2))
                
                exec_status = "⏳ STANDBY MODE (BRIDGE OFFLINE)"
                if META_API_TOKEN != "STANDBY" and META_API_TOKEN is not None:
                    if execute_mt4_order(asset_data["symbol"], "BUY", rec_lot, sl, tp1): exec_status = "🎯 SUCCESSFUL (MT4 POSITION ACTIVE)"
                
                msg = f"🌀 *VORTEX_OMEGA LIQUIDATION TRAP (BUY)*\n\n{gap_warning}📈 *Asset:* {asset_data['name']}\n💵 *Entry:* {current_price:.4f}\n\n🛡️ *RISK MANAGEMENT MATRIX:*\n📊 *Volume:* `{rec_lot}` Lots\n🔴 *Stop-Loss:* {sl:.4f}\n🟢 *Take-Profit:* {tp1:.4f}\n\n⚡ *MT4 CLOUD PIPELINE STATUS:* `{exec_status}`"
                send_telegram_broadcast(msg)
                
            elif current_price > last_upper and (df_30m['High'].iloc[-1] - df_30m['Low'].iloc[-1]) > (1.5 * last_atr):
                stop_distance = last_atr * (2.5 if is_gap_volatile else 2.0)
                sl, tp1 = current_price + stop_distance, current_price - (stop_distance * 1.5)
                rec_lot = max(0.01, round((live_equity * RISK_PERCENT * risk_mult) / (stop_distance * 1000 if stop_distance > 0 else 1), 2))
                
                exec_status = "⏳ STANDBY MODE (BRIDGE OFFLINE)"
                if META_API_TOKEN != "STANDBY" and META_API_TOKEN is not None:
                    if execute_mt4_order(asset_data["symbol"], "SELL", rec_lot, sl, tp1): exec_status = "🎯 SUCCESSFUL (MT4 POSITION ACTIVE)"
                
                msg = f"🌀 *VORTEX_OMEGA LIQUIDATION TRAP (SELL)*\n\n{gap_warning}📈 *Asset:* {asset_data['name']}\n💵 *Entry:* {current_price:.4f}\n\n🛡️ *RISK MANAGEMENT MATRIX:*\n📊 *Volume:* `{rec_lot}` Lots\n🔴 *Stop-Loss:* {sl:.4f}\n🟢 *Take-Profit:* {tp1:.4f}\n\n⚡ *MT4 CLOUD PIPELINE STATUS:* `{exec_status}`"
                send_telegram_broadcast(msg)
    except Exception as e: print(f"Error: {e}")

