import time
import asyncio
import config
import json
import os
from smc_analyzer import fetch_data, analyze_smc
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

def run_once():
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Starting Scan...")
    
    # Connection Test
    try:
        print(f"Testing connection to Binance for {config.ASSETS[0]}...")
        fetch_data(config.ASSETS[0], "15m", 5)
        print("✅ Binance Connection: SUCCESSFUL")
    except Exception as e:
        print(f"❌ Binance Connection: FAILED! Error: {e}")
        return

    last_signals = load_last_signals()
    new_signals_found = False
    
    for symbol in config.ASSETS:
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
    run_once()
