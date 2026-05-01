import requests
import config

async def send_signal(signal_data):
    """
    Sends the formatted SMC signal to the telegram group.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("❌ ERROR: Telegram Bot Token or Chat ID is MISSING in GitHub Secrets!")
        return
    
    direction = signal_data['direction']
    emoji = "🟢" if direction == "LONG" else "🔴"
    
    message = (
        f"💎 *PRO SNIPER DEEP LIMIT ENTRY* 💎\n\n"
        f"**Asset:** `{signal_data['symbol']}`\n"
        f"**Direction:** {emoji} *{direction}*\n"
        f"**Timeframe:** {signal_data['timeframe']}\n"
        f"**Strategy:** `{signal_data['setup_type']}`\n\n"
        f"🔹 **Entry (Safe Limit):** `{signal_data['entry_price']:.6f}`\n"
        f"💰 **Target (350% ROE):** `{signal_data['tp']:.6f}`\n"
        f"🛑 **Stop Loss (1.2% Max):** `{signal_data['sl']:.6f}`\n\n"
        f"✅ *Volume Confirmed:* `Yes` (>1.5x)\n"
        f"✅ *BTC Trend Sync:* `Yes` (Aligned with BTC)\n"
        f"⚡ *Leverage:* `X75 (Cross)`\n\n"
        f"⚠️ _Deep Limit Entry at Support/Resistance to avoid SL hits._"
    )
    
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
        print(f"Signal sent to Telegram for {signal_data['symbol']} {direction}")
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

async def send_startup_message(assets_count, btc_price):
    """
    Sends a test message on bot startup to verify Kraken and Telegram connection.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("❌ ERROR: Telegram Bot Token or Chat ID is MISSING in GitHub Secrets!")
        return
        
    message = (
        f"✅ *SMC Scanner Heartbeat*\n\n"
        f"🌐 **Exchange:** Kraken\n"
        f"📊 **Tracking Assets:** {assets_count} coins\n"
        f"💰 **Current BTC Price:** ${btc_price:,.2f}\n"
        f"📡 **Status:** Scanning for Perfect Entries...\n"
    )
    
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
        print("Startup confirmation sent to Telegram.")
    except Exception as e:
        print(f"Failed to send startup Telegram message: {e}")
