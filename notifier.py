import requests
import config
import time

def send_telegram_message(message):
    """
    Sends a message to the configured Telegram chat with Markdown parsing.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("❌ ERROR: Telegram Bot Token or Chat ID is MISSING!")
        return
        
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    
    try:
        response = requests.post(
            url, 
            json=payload, 
            timeout=15, 
            headers={"Connection": "close"}
        )
        response.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

def send_startup_message(assets_count, btc_price):
    """
    Sends an elegant startup confirmation message to Telegram.
    """
    message = (
        f"🤖 *HIGH-FREQUENCY FUTURES BOT ACTIVE* 🤖\n\n"
        f"🌐 **Exchange Engine:** MEXC (Futures Setup)\n"
        f"⏰ **Scanning Frequency:** Every 60 Seconds\n"
        f"🔥 **Liquidity Filters:** Top {assets_count} Most Active Coins (> $5M Vol)\n"
        f"🐳 **Anti-Whale Shield:** STATISTICAL OUTLIER FILTER ACTIVE\n"
        f"💰 **Current BTC Price:** ${btc_price:,.2f}\n\n"
        f"📈 *Ready to capture premium 5m momentum signals. Let's trade!*"
    )
    send_telegram_message(message)

def send_futures_signal(signal_data):
    """
    Sends a premium, highly actionable futures trading alert to Telegram.
    """
    direction = signal_data['direction']
    emoji = "🟢" if direction == "LONG" else "🔴"
    action = "BUY / LONG" if direction == "LONG" else "SELL / SHORT"
    symbol = signal_data['symbol']
    
    entry = signal_data['entry_price']
    tp = signal_data['tp']
    sl = signal_data['sl']
    
    # Elegant decimal formatting based on price scale
    def fmt_price(val):
        if val > 100:
            return f"{val:.2f}"
        elif val > 1:
            return f"{val:.4f}"
        else:
            return f"{val:.6f}"
            
    message = (
        f"🔥 **FUTURES PRO SNIPER ALERT** 🔥\n\n"
        f"📈 **Asset:** `{symbol}`\n"
        f"🎯 **Action:** {emoji} **{action}**\n"
        f"⚡️ **Leverage:** `Cross {signal_data['leverage']}x` (Recommended)\n\n"
        f"📥 **Entry Limit:** `{fmt_price(entry)}`\n"
        f"💰 **Take Profit (TP):** `{fmt_price(tp)}` (Risk-Reward 1:{config.RISK_REWARD_RATIO:.1f})\n"
        f"🛑 **Stop Loss (SL):** `{fmt_price(sl)}` (-{signal_data['sl_pct']:.2f}%)\n\n"
        f"📊 **Signal Parameters:**\n"
        f"• ADX Trend Strength: `{signal_data['adx']:.1f}`\n"
        f"• RSI Strength: `{signal_data['rsi']:.1f}`\n"
        f"• System Logic: `5m Momentum Trend Pullback`\n\n"
        f"⚠️ _Configure SL and TP order conditions immediately in your futures broker!_"
    )
    
    send_telegram_message(message)
