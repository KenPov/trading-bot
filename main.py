import time
import json
import os
import config
from concurrent.futures import ThreadPoolExecutor
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
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Fast Parallel Scan...")
    
    try:
        btc_df = fetch_data("BTC/USDT", "15m", 5)
        btc_price = btc_df.iloc[-1]['close']
    except Exception as e:
        print(f"Failed to fetch BTC price: {e}")
        return

    try:
        assets = get_active_usdt_markets()
        print(f"Scanning {len(assets)} assets in parallel...")
    except Exception as e:
        print(f"Failed to fetch markets: {e}")
        return

    if send_heartbeat:
        send_startup_message(len(assets), btc_price)

    last_signals = load_last_signals()
    new_signals_found = False

    # Parallel Execution using ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=15) as executor:
        results = list(executor.map(analyze_trend_pullback, assets))

    for signal in results:
        if signal and signal.get("setup_found"):
            symbol = signal["symbol"]
            current_time = time.time()
            last_time = last_signals.get(symbol, 0)
            
            if current_time - last_time > (config.SIGNAL_COOLDOWN_MINUTES * 60):
                direction = signal['direction']
                print(f"🔥 SNIPER {direction} FOUND: {symbol} @ {signal['entry_price']:.6f}")
                send_signal(signal)
                last_signals[symbol] = current_time
                new_signals_found = True

    if new_signals_found:
        save_last_signals(last_signals)
        
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Parallel Scan Completed.")

if __name__ == "__main__":
    start_time = time.time()
    max_duration = 5 * 3600 + 55 * 60 
    
    first_run = True
    while time.time() - start_time < max_duration:
        try:
            run_once(send_heartbeat=first_run)
        except Exception as e:
            print(f"Critical error: {e}")
            
        first_run = False
        time.sleep(config.CHECK_INTERVAL_SECONDS)
