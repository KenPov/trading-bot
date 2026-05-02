import requests
import config

def send_telegram_message(message):
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("❌ ERROR: Telegram Bot Token or Chat ID is MISSING!")
        return
        
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            timeout=60, 
            headers={"Connection": "close"}
        )
        response.raise_for_status()
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def send_startup_message(assets_count, btc_price):
    message = (
        f"🚀 *HIGH-LEVERAGE SNIPER ACTIVE* 🚀\n\n"
        f"🌐 **Data Source:** MEXC (Binance Compatible)\n"
        f"📊 **Scanning:** {assets_count} Top Coins\n"
        f"💰 **BTC Price:** ${btc_price:,.2f}\n"
        f"📡 **Status:** Searching for Sniper Entries...\n"
        f"🎯 **Target:** $2 -> $6 (X75 Leverage)"
    )
    send_telegram_message(message)

def send_signal(signal_data):
    direction = signal_data['direction']
    emoji = "🟢" if direction == "LONG" else "🔴"
    action = "BUY / LONG" if direction == "LONG" else "SELL / SHORT"
    
    message = (
        f"🎯 *SNIPER {direction} SIGNAL* 🎯\n\n"
        f"**Asset:** `{signal_data['symbol']}`\n"
        f"**Direction:** {emoji} *{action}*\n"
        f"**Leverage:** `X75` (High Risk)\n\n"
        f"🔹 **Safe Limit Entry:** `{signal_data['entry_price']:.6f}`\n"
        f"💰 **Take Profit:** `{signal_data['tp']:.6f}` (+$4.00)\n"
        f"🛑 **Stop Loss:** `{signal_data['sl']:.6f}` (Max 1.2%)\n\n"
        f"✅ *Macro Trend:* `Confirmed`\n"
        f"✅ *Entry Logic:* `EMA 200 Magnet Bounce`\n\n"
        f"⚠️ _Place a LIMIT order at the Entry price on Binance._"
    )
    
    send_telegram_message(message)
