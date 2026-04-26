import time
# Version 2.0 - Jumpstart Timer
import asyncio
import config
import json
import os
from smc_analyzer import fetch_data, analyze_smc, get_active_usdt_markets
from telegram_notifier import send_signal, send_startup_message

# Signal tracking file for GitHub Actions persistence
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
    
    # Connection Test
    try:
        print(f"Testing connection to Kraken...")
        btc_df = fetch_data("BTC/USDT", "15m", 5)
        btc_price = btc_df.iloc[-1]['close']
        print(f"✅ Kraken Connection: SUCCESSFUL. BTC Price: ${btc_price:.2f}")
    except Exception as e:
        print(f"❌ Kraken Connection: FAILED! Error: {e}")
        return

    last_signals = load_last_signals()
    
    # We remove the forced message now that we know it works!
    # The bot will now only alert you when a REAL setup is found.

    new_signals_found = False
    
    # Dynamically fetch markets
    try:
        print("Fetching active USDT markets from Kraken...")
        assets = get_active_usdt_markets()
        print(f"Found {len(assets)} active USDT pairs to scan.")
    except Exception as e:
        print(f"❌ Failed to fetch markets: {e}")
        return
        
    # Send Heartbeat message on startup
    if send_heartbeat:
        try:
            asyncio.run(send_startup_message(len(assets), btc_price))
        except Exception as e:
            print(f"Failed to send heartbeat: {e}")

    for symbol in assets:
        # Determine HTF Bias (highest timeframe in the list)
        htf = config.TIMEFRAMES[-1]
        htf_bias = "NEUTRAL"
        try:
            htf_df = fetch_data(symbol, htf, config.LOOKBACK_CANDLES)
            from smc_analyzer import get_market_bias, smc
            swing_highs_lows = smc.swing_highs_lows(htf_df)
            bos_choch_df = smc.bos_choch(htf_df, swing_highs_lows)
            htf_bias = get_market_bias(bos_choch_df)
            print(f"   [{symbol}] HTF Bias ({htf}): {htf_bias}")
        except Exception as e:
            print(f"Error getting HTF bias for {symbol}: {e}")

        for timeframe in config.TIMEFRAMES:
            try:
                df = fetch_data(symbol, timeframe, config.LOOKBACK_CANDLES)
                signal = analyze_smc(df, symbol, timeframe, external_bias=htf_bias)
                
                if signal.get("setup_found"):
                    sig_id = signal["signal_id"]
                    asset_tf_key = f"{symbol}_{timeframe}"
                    
                    if last_signals.get(asset_tf_key) != sig_id:
                        print(f"!!! PERFECT SETUP: {symbol} {timeframe} - {signal['direction']} @ {signal['entry_price']:.2f}")
                        
                        signal['symbol'] = symbol
                        signal['timeframe'] = timeframe
                        
                        asyncio.run(send_signal(signal))
                        last_signals[asset_tf_key] = sig_id
                        new_signals_found = True
            except Exception as e:
                print(f"Error checking {symbol} on {timeframe}: {e}")
            
    if new_signals_found:
        save_last_signals(last_signals)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Scan Completed.")

if __name__ == "__main__":
    start_time = time.time()
    max_duration = 5 * 3600 + 55 * 60 # 5 hours and 55 minutes
    
    first_run = True
    while time.time() - start_time < max_duration:
        try:
            run_once(send_heartbeat=first_run)
        except Exception as e:
            print(f"Critical error during scan: {e}")
            
        first_run = False
        print(f"Waiting {config.CHECK_INTERVAL_SECONDS} seconds for the next scan...")
        time.sleep(config.CHECK_INTERVAL_SECONDS)
        
    print("Maximum execution time reached. Exiting gracefully for next GitHub Action run.")
