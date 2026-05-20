import time
import json
import os
import config
from concurrent.futures import ThreadPoolExecutor
from strategy import get_active_usdt_markets, analyze_1h_movement, fetch_data
from notifier import send_startup_message, send_top_5_movers_report

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
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(analyze_1h_movement, assets))
    
    # Filter out None results and sort by score
    valid_opportunities = [r for r in results if r is not None]
    valid_opportunities.sort(key=lambda x: x['score'], reverse=True)
    
    # Select top 5
    top_5 = valid_opportunities[:config.TOP_COINS_COUNT]
    
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Found {len(valid_opportunities)} moving coins, sending Top 5.")
    send_top_5_movers_report(top_5)

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
