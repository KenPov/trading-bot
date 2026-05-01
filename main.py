import time
import json
import os
import config
from strategy import get_active_usdt_markets, analyze_trend_pullback, fetch_data
from notifier import send_startup_message, send_signal

SIGNAL_TRACKER_FILE = "last_signals.json"

def load_last_signals():
    if os.path.exists(SIGNAL_TRACKER_FILE):
        try:
            with open(SIGNAL_TRACKER_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_last_signals(signals):
    with open(SIGNAL_TRACKER_FILE, "w") as f:
        json.dump(signals, f)

def run_once(send_heartbeat=False):
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Scan...")
    
    try:
        btc_df = fetch_data("BTC/USDT", "15m", 5)
        btc_price = btc_df.iloc[-1]['close']
    except Exception as e:
        print(f"Failed to fetch BTC price: {e}")
        return

    try:
        assets = get_active_usdt_markets()
    except Exception as e:
        print(f"Failed to fetch markets: {e}")
        return

    if send_heartbeat:
        send_startup_message(len(assets), btc_price)

    last_signals = load_last_signals()
    new_signals_found = False

    for symbol in assets:
        try:
            signal = analyze_trend_pullback(symbol)
            if signal.get("setup_found"):
                sig_id = signal["signal_id"]
                current_time = time.time()
                last_time = last_signals.get(symbol, 0)
                
                # Handle old format where last_signals stored strings
                if isinstance(last_time, str):
                    last_time = 0
                
                cooldown_seconds = getattr(config, 'SIGNAL_COOLDOWN_MINUTES', 60) * 60
                
                if current_time - last_time > cooldown_seconds:
                    print(f"!!! PERFECT SETUP: {symbol} - LONG @ {signal['entry_price']:.2f}")
                    send_signal(signal)
                    last_signals[symbol] = current_time
                    new_signals_found = True
        except Exception as e:
            print(f"Error processing {symbol}: {e}")

    if new_signals_found:
        save_last_signals(last_signals)
        
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Scan Completed.")

if __name__ == "__main__":
    start_time = time.time()
    # Run for just under 6 hours (standard for GitHub actions)
    max_duration = 5 * 3600 + 55 * 60 
    
    first_run = True
    while time.time() - start_time < max_duration:
        try:
            run_once(send_heartbeat=first_run)
        except Exception as e:
            print(f"Critical error during scan: {e}")
            
        first_run = False
        time.sleep(config.CHECK_INTERVAL_SECONDS)
