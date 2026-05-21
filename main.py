import time
import json
import os
import config
from concurrent.futures import ThreadPoolExecutor
from strategy import get_active_usdt_markets, analyze_futures_strategy, fetch_data
from notifier import send_startup_message, send_futures_digest

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

def run_once():
    """Runs a single active scanning loop across high-momentum coins on 1h and 4h timeframes."""
    print(f"\n[SCAN] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Support & Resistance Futures Scan...")
    
    # 1. Fetch benchmark BTC price for status info
    try:
        btc_df = fetch_data("BTC/USDT", "1h", limit=5)
        btc_price = btc_df.iloc[-1]['close'] if not btc_df.empty else 0.0
    except Exception as e:
        print(f"[WARNING] Failed to fetch BTC benchmark price: {e}")
        btc_price = 0.0

    # 2. Get currently moving high-liquidity coins
    try:
        assets = get_active_usdt_markets()
        print(f"[INFO] Top {len(assets)} active coins isolated. Running parallel S&R scan...")
    except Exception as e:
        print(f"[ERROR] Critical: Failed to retrieve active markets from exchange: {e}")
        return

    # 3. Load cooldown state
    last_signals = load_last_signals()
    signals_to_dispatch = []
    
    # 4. Scan each timeframe
    for tf in config.SCAN_TIMEFRAMES:
        print(f"[INFO] Scanning timeframe: {tf}...")
        
        # Parallel scan for each coin
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Map returns results in order
            futures_results = executor.map(lambda symbol: analyze_futures_strategy(symbol, tf), assets)
            results = list(futures_results)
            
        valid_signals = [r for r in results if r and r.get('setup_found')]
        
        current_time = time.time()
        for sig in valid_signals:
            symbol = sig['symbol']
            # Create a unique key per symbol and timeframe to allow setups on both 1h and 4h independently
            signal_key = f"{symbol}_{tf}"
            last_sent_timestamp = last_signals.get(signal_key, 0)
            
            # Check cooldown safety (24 hours)
            cooldown_elapsed = current_time - last_sent_timestamp
            cooldown_limit = config.SIGNAL_COOLDOWN_MINUTES * 60
            
            if cooldown_elapsed >= cooldown_limit:
                print(f"[SIGNAL] S&R CONFLUENCE FOUND: {sig['direction']} setup on {symbol} ({tf})!")
                signals_to_dispatch.append(sig)
                last_signals[signal_key] = current_time
            else:
                minutes_left = int((cooldown_limit - cooldown_elapsed) / 60)
                print(f"[COOLDOWN] Alert ignored for {symbol} ({tf}). Cooldown active ({minutes_left} mins remaining).")
                
    # 5. Dispatch single Telegram digest message with all valid trade setups
    try:
        send_futures_digest(signals_to_dispatch, btc_price)
        if signals_to_dispatch:
            save_last_signals(last_signals)
    except Exception as e:
        print(f"[ERROR] Failed to compile and send Telegram digest: {e}")
        
    print(f"[INFO] [{time.strftime('%Y-%m-%d %H:%M:%S')}] Scan cycle completed.")

if __name__ == "__main__":
    print("[STARTUP] Rebuilt Support & Resistance Futures Bot Engine Initialized.")
    run_once()

