import requests
import config
import time

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
        f"🚀 *1H TOP MOVERS SCANNER ACTIVE* 🚀\n\n"
        f"🌐 **Data Source:** MEXC\n"
        f"📊 **Scanning:** {assets_count} Top Coins\n"
        f"💰 **BTC Price:** ${btc_price:,.2f}\n"
        f"📡 **Mode:** Top 5 Report Every 2h\n"
        f"🎯 **Strategy:** 1-Hour Volatility & Trend"
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
    
def send_top_5_report(top_opportunities):
    if not top_opportunities:
        send_telegram_message("🔍 *Market Scan:* No high-probability 4h S/R setups found at this time.")
        return
        
    message = "📊 *TOP 5 TRADING OPPORTUNITIES (4H S/R)* 📊\n\n"
    message += f"Scan Time: `{time.strftime('%Y-%m-%d %H:%M')}`\n\n"
    
    for i, op in enumerate(top_opportunities, 1):
        icon = "🟢" if "LONG" in op['direction'] else "🔴"
        message += f"{i}. {icon} **{op['symbol']}**\n"
        message += f"   • Action: *{op['direction']}*\n"
        message += f"   • Price: `{op['price']:.6f}`\n"
        message += f"   • 4h Level: `{op['level']:.6f}`\n\n"
        
    message += "⚠️ _Focus on price action near these levels before entering._"
    send_telegram_message(message)

def send_top_5_movers_report(top_opportunities):
    if not top_opportunities:
        send_telegram_message("🔍 *Market Scan:* No coins moving significantly on the 1H timeframe.")
        return
        
    message = "🔥 *TOP 5 ACTIVE COINS (1H MOVERS)* 🔥\n\n"
    message += f"Scan Time: `{time.strftime('%Y-%m-%d %H:%M')}`\n\n"
    
    for i, op in enumerate(top_opportunities, 1):
        icon = "🟢" if op['change'] > 0 else "🔴"
        message += f"{i}. {icon} **{op['symbol']}**\n"
        message += f"   • Price: `{op['price']:.6f}`\n"
        message += f"   • 1h Volatility: `*{op['volatility']:.2f}%*`\n"
        message += f"   • 1h Change: `{op['change']:.2f}%`\n\n"
        
    message += "⚠️ _These coins have the most movement right now. Trade carefully!_"
    send_telegram_message(message)
