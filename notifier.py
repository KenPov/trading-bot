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
        if response.status_code != 200:
            print(f"[ERROR] Telegram API Response: {response.text}")
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

def send_futures_digest(signals, btc_price):
    """
    Sends a beautiful consolidated futures S&R digest containing all detected setups.
    If no setups are found, sends a clean status confirmation.
    """
    # Price formatting helper based on currency scale
    def fmt_price(val):
        if val > 100:
            return f"{val:.2f}"
        elif val > 1:
            return f"{val:.4f}"
        else:
            return f"{val:.6f}"
            
    if not signals:
        message = (
            f"🤖 <b>FUTURES S&R SCAN COMPLETE</b> 🤖\n\n"
            f"💰 <b>Current BTC Price:</b> ${btc_price:,.2f}\n"
            f"ℹ️ <i>No high-probability Support & Resistance setups met the RRR & proximity bounds in this scan.</i>"
        )
        send_telegram_message(message)
        return

    # Compile the digest header
    header = (
        f"🔥 <b>FUTURES S&R SNIPER DIGEST</b> 🔥\n"
        f"🌐 <b>Exchange Engine:</b> MEXC (1H & 4H Charts)\n"
        f"💰 <b>Current BTC Price:</b> ${btc_price:,.2f}\n"
        f"📈 <b>Found:</b> <code>{len(signals)} Key Setup(s)</code>\n"
        f"-----------------------------------------\n\n"
    )
    
    body_blocks = []
    for sig in signals:
        symbol = sig['symbol']
        tf = sig['timeframe']
        direction = sig['direction']
        emoji = "🟢" if direction == "LONG" else "🔴"
        action = "BUY/LONG" if direction == "LONG" else "SELL/SHORT"
        
        entry = sig['entry_price']
        tp = sig['tp']
        sl = sig['sl']
        sl_pct = sig['sl_pct']
        rrr = sig['rrr']
        support = sig['support']
        resistance = sig['resistance']
        
        block = (
            f"{emoji} <b>{symbol} ({tf})</b> | <b>{action}</b>\n"
            f"📥 <b>Entry:</b> <code>{fmt_price(entry)}</code>\n"
            f"🛑 <b>SL:</b> <code>{fmt_price(sl)}</code> (-{sl_pct:.2f}%)\n"
            f"🎯 <b>TP:</b> <code>{fmt_price(tp)}</code> (Risk-Reward 1:{rrr:.1f})\n"
            f"📊 <b>Levels:</b> Sup <code>{fmt_price(support)}</code> | Res <code>{fmt_price(resistance)}</code>\n"
        )
        body_blocks.append(block)
        
    footer = (
        f"-----------------------------------------\n"
        f"⚠️ <i>Verify charts & set broker SL/TP orders immediately!</i>"
    )
    
    # Build and split message if it exceeds Telegram limits (4096 characters)
    current_message = header
    for block in body_blocks:
        if len(current_message) + len(block) + len(footer) > 4000:
            send_telegram_message(current_message + footer)
            current_message = header + "\n(Continued...)\n\n" + block
        else:
            current_message += block + "\n"
            
    send_telegram_message(current_message + footer)

