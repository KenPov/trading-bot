import requests
import config
import time

def send_telegram_message(message):
    """
    Sends a message to the configured Telegram chat with robust HTML parsing.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        print("[ERROR] Telegram Bot Token or Chat ID is MISSING!")
        return
        
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": config.TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
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
        print(f"[ERROR] Failed to send Telegram message: {e}")

def send_startup_message(assets_count, btc_price):
    """
    Sends an elegant startup confirmation message to Telegram using HTML.
    """
    message = (
        f"🤖 <b>HIGH-FREQUENCY FUTURES BOT ACTIVE</b> 🤖\n\n"
        f"🌐 <b>Exchange Engine:</b> MEXC (Futures Setup)\n"
        f"⏰ <b>Scanning Frequency:</b> Every 60 Seconds\n"
        f"🔥 <b>Liquidity Filters:</b> Top {assets_count} Most Active Coins (&gt; $5M Vol)\n"
        f"🐳 <b>Anti-Whale Shield:</b> STATISTICAL OUTLIER FILTER ACTIVE\n"
        f"💰 <b>Current BTC Price:</b> ${btc_price:,.2f}\n\n"
        f"📈 <i>Ready to capture premium 5m momentum signals. Let's trade!</i>"
    )
    send_telegram_message(message)

def send_futures_signal(signal_data):
    """
    Sends a premium, highly actionable futures trading alert to Telegram using HTML.
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
        f"🔥 <b>FUTURES PRO SNIPER ALERT</b> 🔥\n\n"
        f"📈 <b>Asset:</b> <code>{symbol}</code>\n"
        f"🎯 <b>Action:</b> {emoji} <b>{action}</b>\n"
        f"⚡️ <b>Leverage:</b> <code>Cross {signal_data['leverage']}x</code> (Recommended)\n\n"
        f"📥 <b>Entry Limit:</b> <code>{fmt_price(entry)}</code>\n"
        f"💰 <b>Take Profit (TP):</b> <code>{fmt_price(tp)}</code> (Risk-Reward 1:{config.RISK_REWARD_RATIO:.1f})\n"
        f"🛑 <b>Stop Loss (SL):</b> <code>{fmt_price(sl)}</code> (-{signal_data['sl_pct']:.2f}%)\n\n"
        f"📊 <b>Signal Parameters:</b>\n"
        f"• ADX Trend Strength: <code>{signal_data['adx']:.1f}</code>\n"
        f"• RSI Strength: <code>{signal_data['rsi']:.1f}</code>\n"
        f"• System Logic: <code>5m Momentum Trend Pullback</code>\n\n"
        f"⚠️ <i>Configure SL and TP order conditions immediately in your futures broker!</i>"
    )
    
    send_telegram_message(message)
