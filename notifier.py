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
        f"✅ *SMC Scanner Heartbeat*\n\n"
        f"🌐 **Exchange:** Kraken\n"
        f"📊 **Tracking Assets:** {assets_count} coins\n"
        f"💰 **Current BTC Price:** ${btc_price:,.2f}\n"
        f"📡 **Status:** Scanning for Perfect Entries...\n"
    )
    send_telegram_message(message)

def send_signal(signal_data):
    direction = signal_data['direction']
    emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = (
        f"🎯 *PRO SNIPER TREND PULLBACK* 🎯\n\n"
        f"**Asset:** `{signal_data['symbol']}`\n"
        f"**Direction:** {emoji} *{direction}*\n"
        f"**Timeframe:** {config.TIMEFRAME_ENTRY}\n\n"
        f"🔹 **Entry (Safe Limit):** `{signal_data['entry_price']:.6f}`\n"
        f"💰 **Take Profit (300% ROE):** `{signal_data['tp']:.6f}`\n"
        f"🛑 **Stop Loss (Max 1.2%):** `{signal_data['sl']:.6f}`\n\n"
        f"✅ *Macro Trend:* `Bullish`\n"
        f"✅ *RSI Pierced:* `Yes (Oversold Dip)`\n"
        f"⚡ *Leverage:* `X75`\n\n"
        f"⚠️ _Place a limit order at the exact Entry price to catch the bounce._"
    )
    
    send_telegram_message(message)
