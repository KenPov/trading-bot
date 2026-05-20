import time
import json
import os
import config
from concurrent.futures import ThreadPoolExecutor
from strategy import get_active_usdt_markets, analyze_futures_strategy, fetch_data
from notifier import send_startup_message, send_futures_signal

def load_last_signals():
    """Loads previously sent signals from a tracking JSON file to prevent duplicate alerts."""
    if os.path.exists(config.SIGNAL_TRACKER_FILE):
        try:
            with open(config.SIGNAL_TRACKER_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARNING] Could not parse {config.SIGNAL_TRACKER_FILE}: {e}")
            return {}
    return {}

def save_last_signals(signals):
    """Saves the signal timestamps to a local tracking JSON file."""
    try:
        with open(config.SIGNAL_TRACKER_FILE, "w") as f:
            json.dump(signals, f)
    except Exception as e:
        print(f"[ERROR] Error saving signals state: {e}")

def run_once(send_heartbeat=False):
    """Runs a single active scanning loop across high-momentum coins."""
    print(f"\n[SCAN] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting High-Frequency Futures Scan...")
    
    # 1. Fetch benchmark BTC price for startup status
    try:
        btc_df = fetch_data("BTC/USDT", "15m", limit=5)
        btc_price = btc_df.iloc[-1]['close'] if not btc_df.empty else 0.0
    except Exception as e:
        print(f"[WARNING] Failed to fetch BTC benchmark price: {e}")
        btc_price = 0.0

    # 2. Get currently moving high-liquidity coins
    try:
        assets = get_active_usdt_markets()
        print(f"[INFO] Top {len(assets)} moving coins isolated. Running parallel strategies...")
    except Exception as e:
        print(f"[ERROR] Critical: Failed to retrieve active markets from exchange: {e}")
        return

    # 3. Send Telegram confirmation on bot startup/heartbeat
    if send_heartbeat:
        try:
            send_startup_message(len(assets), btc_price)
        except Exception as e:
            print(f"[WARNING] Startup notification failed: {e}")

    # 4. Load cooldown state
    last_signals = load_last_signals()
    new_signals_found = False

    # 5. Run strategy scans in parallel threads (safely, maximum 5 workers to prevent rate limits)
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(analyze_futures_strategy, assets))
    
    # 6. Process strategy signal triggers
    valid_signals = [r for r in results if r and r.get('setup_found')]
    
    current_time = time.time()
    
    for sig in valid_signals:
        symbol = sig['symbol']
        last_sent_timestamp = last_signals.get(symbol, 0)
        
        # Check signal cooldown safety to prevent notification spam
        cooldown_elapsed = current_time - last_sent_timestamp
        cooldown_limit = config.SIGNAL_COOLDOWN_MINUTES * 60
        
        if cooldown_elapsed >= cooldown_limit:
            print(f"[SIGNAL] SIGNAL CONFLUENCE FOUND: {sig['direction']} setup on {symbol}!")
            try:
                send_futures_signal(sig)
                last_signals[symbol] = current_time
                new_signals_found = True
            except Exception as e:
                print(f"[ERROR] Error sending telegram signal alert for {symbol}: {e}")
        else:
            minutes_left = int((cooldown_limit - cooldown_elapsed) / 60)
            print(f"[COOLDOWN] Alert ignored for {symbol}. Cooldown still active ({minutes_left} mins remaining).")
            
    # 7. Persist active state if signals were triggered
    if new_signals_found:
        save_last_signals(last_signals)
        
    print(f"[INFO] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Scan cycle completed.")

if __name__ == "__main__":
    start_time = time.time()
    # Set the execution window to 5h 55m. This ensures clean shutdown inside the GitHub Actions 6h runner limit.
    max_duration_seconds = 5 * 3600 + 55 * 60 
    
    first_run = True
    print("[STARTUP] Rebuilt Futures Sniper Trading Bot Engine Initialized.")
    
    while time.time() - start_time < max_duration_seconds:
        loop_start = time.time()
        try:
            run_once(send_heartbeat=first_run)
        except Exception as e:
            print(f"[ERROR] Loop crash prevented: {e}")
            
        first_run = False
        
        # Calculate precise sleep window to account for scanning time and maintain steady 60s intervals
        execution_time = time.time() - loop_start
        sleep_duration = max(1.0, config.CHECK_INTERVAL_SECONDS - execution_time)
        
        print(f"[SLEEP] Sleeping for {sleep_duration:.1f} seconds until next scan cycle...")
        time.sleep(sleep_duration)
