import os
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from flask import Flask
from threading import Thread
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ============================================
# 1. WEB SERVER (FOR 24/7 UPTIME ON RENDER)
# ============================================
app = Flask('')
@app.route('/')
def home():
    return "Goldman Sachs AI Pro is Online!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ============================================
# 2. ANALYSIS LOGIC (TECHNICAL INDICATORS)
# ============================================
class TechnicalAnalyzer:
    @staticmethod
    def calculate_indicators(df):
        if df is None or len(df) < 30: return None
        # RSI Calculation
        df['rsi'] = ta.rsi(df['close'], length=14)
        # MACD Calculation
        macd = ta.macd(df['close'])
        df['macd'] = macd['MACD_12_26_9']
        df['macd_signal'] = macd['MACDs_12_26_9']
        # ATR for Dynamic SL/TP
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        return df

def get_signal(symbol):
    try:
        # Fetching Real Market Data from KuCoin
        exchange = ccxt.kucoin()
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=100)
        df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        
        # Calculate Technicals
        df = TechnicalAnalyzer.calculate_indicators(df)
        last = df.iloc[-1]
        
        # Scoring Logic
        score = 50
        if last['rsi'] < 35: score += 20
        elif last['rsi'] > 65: score -= 20
        
        if last['macd'] > last['macd_signal']: score += 15
        else: score -= 15
        
        # Direction and Risk Management
        direction = "NEUTRAL"
        if score >= 60: direction = "LONG"
        elif score <= 40: direction = "SHORT"
        
        curr_price = last['close']
        atr = last['atr']
        
        if direction == "LONG":
            sl = curr_price - (atr * 1.5)
            tp = curr_price + (atr * 3)
            action = "✅ STRONG BUY"
        elif direction == "SHORT":
            sl = curr_price + (atr * 1.5)
            tp = curr_price - (atr * 3)
            action = "🔴 STRONG SELL"
        else:
            sl, tp = 0, 0
            action = "⏳ NO TRADE (Wait)"

        return {
            "price": curr_price,
            "direction": direction,
            "action": action,
            "tp": tp,
            "sl": sl,
            "score": score
        }
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

# ============================================
# 3. TELEGRAM BOT HANDLERS
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome = "🚀 *Goldman Sachs AI Pro v9.0*\n\n" \
              "Main active hoon! Signal ke liye likhein:\n" \
              "`/analyze BTC/USDT`"
    await update.message.reply_text(welcome, parse_mode='Markdown')

async def analyze(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Pair missing! Example: `/analyze ETH/USDT`", parse_mode='Markdown')
        return

    symbol = context.args[0].upper()
    await update.message.reply_text(f"🔍 Analyzing {symbol}... Market data fetch ho raha hai.")
    
    data = get_signal(symbol)
    
    if data:
        msg = f"📊 *ANALYSIS: {symbol}*\n" \
              f"━━━━━━━━━━━━━━━━━━\n" \
              f"💰 *Price:* ${data['price']:.4f}\n" \
              f"📌 *Signal:* {data['direction']}\n" \
              f"🤖 *AI Confidence:* {data['score']}%\n" \
              f"━━━━━━━━━━━━━━━━━━\n" \
              f"🧠 *Action:* `{data['action']}`\n\n" \
              f"✅ *Target (TP):* ${data['tp']:.4f}\n" \
              f"🛑 *Stop Loss (SL):* ${data['sl']:.4f}\n" \
              f"━━━━━━━━━━━━━━━━━━\n" \
              f"⚠️ _Risk 1-2% per trade._"
        await update.message.reply_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Symbol galat hai ya market data nahi mil raha. Pair ko `BTC/USDT` format mein likhein.")

# ============================================
# 4. RUN EVERYTHING
# ============================================
if __name__ == "__main__":
    # Start Web Server for Render
    keep_alive()
    
    # Replace the string below with your REAL TOKEN from BotFather
    TOKEN = "8430165040:AAGpUfdJx9eBT7FPm-dFpKFvs71WjeOwumg" 
    
    # Initialize Application
    app_bot = Application.builder().token(TOKEN).build()
    
    # Add Commands
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("analyze", analyze))
    
    print("✅ Bot is running and waiting for signals...")
    app_bot.run_polling()
