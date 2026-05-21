import ccxt
import pandas as pd
import pandas_ta_classic as ta
import config
import time
import numpy as np

# Initialize global MEXC exchange instance
exchange = ccxt.mexc({'enableRateLimit': True})

def get_active_usdt_markets():
    """
    Fetches all tickers from MEXC, filters out stablecoins and low-liquidity coins,
    and returns the top ACTIVE_COINS_TO_SCAN coins with the highest absolute 24h volatility/movement.
    This guarantees we ONLY trade coins that are moving.
    """
    try:
        print("[INFO] Fetching market tickers from MEXC...")
        tickers = exchange.fetch_tickers()
        
        candidates = []
        for symbol, data in tickers.items():
            # Check 1: Must be a USDT pair, not a stablecoin, and have active price data
            if '/USDT' in symbol and symbol not in config.STABLECOINS:
                quote_volume = data.get('quoteVolume', 0)
                last_price = data.get('last', 0)
                change_pct = data.get('percentage', 0) # 24h change percentage
                
                # Filter out low-price meme/shitcoins to reduce extreme manipulation risks
                if quote_volume and quote_volume > config.MIN_24H_VOLUME and last_price > 0.00001:
                    candidates.append({
                        "symbol": symbol,
                        "volume": quote_volume,
                        "change_abs": abs(change_pct) if change_pct is not None else 0,
                        "change_raw": change_pct if change_pct is not None else 0
                    })
        
        # Sort by absolute 24h price change (movers) to find the most volatile, active coins
        candidates.sort(key=lambda x: x['change_abs'], reverse=True)
        
        # Take the top ACTIVE_COINS_TO_SCAN coins
        final_list = [c['symbol'] for c in candidates[:config.ACTIVE_COINS_TO_SCAN]]
        
        if not final_list:
            print("[WARNING] No highly active markets met the volume filters. Falling back to core majors.")
            return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT']
            
        print(f"[SUCCESS] Found {len(final_list)} highly active moving coins for scanning.")
        return final_list
        
    except Exception as e:
        print(f"[ERROR] Error fetching active markets: {e}")
        return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT']

def fetch_data(symbol, timeframe, limit=100):
    """
    Fetches OHLCV data from MEXC with rate limit safety and retries.
    """
    retries = 2
    for attempt in range(retries):
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            return df
        except Exception as e:
            if attempt == retries - 1:
                print(f"[ERROR] Failed to fetch data for {symbol} on {timeframe} after {retries} attempts: {e}")
                return pd.DataFrame()
            time.sleep(0.5)
    return pd.DataFrame()

def is_whale_pump_dump(df):
    """
    Detects if the coin has been subject to sudden, extreme whale pump/dump manipulation.
    Uses mean and standard deviation analysis on the previous 20 candles to isolate statistical outliers.
    """
    if len(df) < 25:
        return False
        
    # We inspect the latest completed candle [-2] and the current active candle [-1]
    # Reference range is the 20 candles before them
    ref_df = df.iloc[-22:-2]
    
    # Calculate price range percentage for each reference candle: (High - Low) / Low * 100
    ref_ranges_pct = ((ref_df['high'] - ref_df['low']) / ref_df['low']) * 100
    ref_volumes = ref_df['volume']
    
    # Compute statistical baselines (mean and standard deviation)
    mean_range = ref_ranges_pct.mean()
    std_range = ref_ranges_pct.std()
    mean_volume = ref_volumes.mean()
    std_volume = ref_volumes.std()
    
    # Avoid zero division or overly tight metrics on extremely flat history
    std_range = max(std_range, 0.05)
    std_volume = max(std_volume, 1.0)
    
    # Test both the latest completed candle and the active forming candle
    test_candles = [df.iloc[-2], df.iloc[-1]]
    
    for i, candle in enumerate(test_candles):
        # Calculate current candle metrics
        c_range_pct = ((candle['high'] - candle['low']) / candle['low']) * 100
        c_volume = candle['volume']
        
        # Wick check (sum of wicks vs entire candle height)
        # Rejection wick size = total height - body size
        c_height = candle['high'] - candle['low']
        c_body = abs(candle['close'] - candle['open'])
        c_wick = c_height - c_body
        c_wick_ratio = (c_wick / c_height) if c_height > 0 else 0
        
        # Condition A: Extreme simultaneous price & volume outlier (Standard Pump & Dump)
        is_price_outlier = c_range_pct > (mean_range + config.WHALE_RANGE_MULTIPLIER * std_range)
        is_volume_outlier = c_volume > (mean_volume + config.WHALE_VOLUME_MULTIPLIER * std_volume)
        
        if is_price_outlier and is_volume_outlier:
            candle_desc = "active" if i == 1 else "previous completed"
            print(f"[FILTERED] Whale pump/dump detected on {candle_desc} candle. Price range outlier: {c_range_pct:.2f}% (avg: {mean_range:.2f}%), Volume outlier: {c_volume:.0f} (avg: {mean_volume:.0f}).")
            return True
            
        # Condition B: Extreme flash rejection (long wicks on high volume, i.e., dump-and-pump or pump-and-dump rejection)
        if c_wick_ratio > config.WHALE_WICK_THRESHOLD and c_range_pct > (mean_range + 1.5 * std_range) and is_volume_outlier:
            candle_desc = "active" if i == 1 else "previous completed"
            print(f"[FILTERED] Flash whale wick manipulation detected on {candle_desc} candle. Wick ratio: {c_wick_ratio:.2%} (limit: {config.WHALE_WICK_THRESHOLD:.2%}).")
            return True
            
    return False

def calculate_sr_levels(df, window=5):
    """
    Finds historical confirmed support (pivot lows) and resistance (pivot highs) levels.
    Uses a standard pivot fractal algorithm.
    """
    lows = df['low'].values
    highs = df['high'].values
    n = len(df)
    
    support_levels = []
    resistance_levels = []
    
    # Scan historical candles, leaving a margin of 'window' at the end to ensure they are confirmed pivots
    for i in range(window, n - window):
        # Pivot Low (Support)
        is_pivot_low = True
        for j in range(i - window, i + window + 1):
            if lows[j] < lows[i]:
                is_pivot_low = False
                break
        if is_pivot_low:
            support_levels.append(lows[i])
            
        # Pivot High (Resistance)
        is_pivot_high = True
        for j in range(i - window, i + window + 1):
            if highs[j] > highs[i]:
                is_pivot_high = False
                break
        if is_pivot_high:
            resistance_levels.append(highs[i])
            
    # Include absolute extreme high and low of the lookback period as major fallback levels
    support_levels.append(df['low'].min())
    resistance_levels.append(df['high'].max())
    
    return support_levels, resistance_levels

def cluster_levels(levels, threshold_pct=0.0075):
    """
    Groups levels that are within threshold_pct of an anchor to prevent chaining
    and isolate distinct key structural zones.
    """
    if not levels:
        return []
    sorted_levels = sorted(list(set(levels)))
    clustered = []
    current_group = [sorted_levels[0]]
    
    for val in sorted_levels[1:]:
        # Compare to the anchor of the current group to prevent chaining
        if (val - current_group[0]) / current_group[0] <= threshold_pct:
            current_group.append(val)
        else:
            clustered.append(sum(current_group) / len(current_group))
            current_group = [val]
    clustered.append(sum(current_group) / len(current_group))
    return clustered


def analyze_futures_strategy(symbol, timeframe="1h"):
    """
    Analyzes an asset on a given timeframe (1h/4h) for high-probability Support & Resistance setups.
    LONG Setup: Price is close to a confirmed support level (S1) and holding above it.
    SHORT Setup: Price is close to a confirmed resistance level (R1) and holding below it.
    """
    try:
        # Fetch OHLCV data (e.g. 100 candles of 1h or 4h)
        df = fetch_data(symbol, timeframe, limit=100)
        if df.empty or len(df) < 30:
            return {"setup_found": False, "reason": "Insufficient historical data"}
            
        # Apply Whale Pump & Dump Filter
        if is_whale_pump_dump(df):
            return {"setup_found": False, "reason": "Whale Pump/Dump detection flagged"}
            
        # Calculate Technical Indicators
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=config.ATR_PERIOD)
        
        curr = df.iloc[-1]
        current_price = curr['close']
        atr_val = curr['atr']
        rsi_val = curr['rsi'] if not pd.isna(curr['rsi']) else 50.0
        
        # Calculate raw support and resistance levels
        raw_supports, raw_resistances = calculate_sr_levels(df, window=config.SR_WINDOW)
        
        # Cluster levels to consolidate nearby wicks (0.75% default threshold)
        supports = cluster_levels(raw_supports)
        resistances = cluster_levels(raw_resistances)

        
        # Isolate S1 (highest support below current price)
        supports_below = [s for s in supports if s < current_price]
        S1 = max(supports_below) if supports_below else df['low'].min()
        
        # Isolate R1 (lowest resistance above current price)
        resistances_above = [r for r in resistances if r > current_price]
        R1 = min(resistances_above) if resistances_above else df['high'].max()
        
        # Calculate ATR-based buffer for Stop Loss and entry triggers
        atr_buffer = 0.5 * atr_val if not pd.isna(atr_val) else (current_price * 0.005)
        
        # Proximity threshold: within config.SR_PROXIMITY_PCT (1.5%) of the level
        proximity_limit = current_price * config.SR_PROXIMITY_PCT
        
        # 1. LONG Opportunity (Price testing or bouncing off Support)
        dist_to_support = current_price - S1
        is_near_support = dist_to_support <= proximity_limit
        
        if is_near_support:
            entry = current_price
            sl = S1 - atr_buffer
            tp = R1 - atr_buffer
            
            risk = entry - sl
            reward = tp - entry
            rrr = reward / risk if risk > 0 else 0
            
            if rrr >= config.SR_MIN_RRR:
                sl_pct = (risk / entry) * 100
                return {
                    "setup_found": True,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "direction": "LONG",
                    "entry_price": entry,
                    "tp": tp,
                    "sl": sl,
                    "sl_pct": sl_pct,
                    "rrr": rrr,
                    "rsi": rsi_val,
                    "support": S1,
                    "resistance": R1,
                    "strategy": f"S&R Support Bounce ({timeframe})"
                }
                
        # 2. SHORT Opportunity (Price testing or rejecting Resistance)
        dist_to_resistance = R1 - current_price
        is_near_resistance = dist_to_resistance <= proximity_limit
        
        if is_near_resistance:
            entry = current_price
            sl = R1 + atr_buffer
            tp = S1 + atr_buffer
            
            risk = sl - entry
            reward = entry - tp
            rrr = reward / risk if risk > 0 else 0
            
            if rrr >= config.SR_MIN_RRR:
                sl_pct = (risk / entry) * 100
                return {
                    "setup_found": True,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "direction": "SHORT",
                    "entry_price": entry,
                    "tp": tp,
                    "sl": sl,
                    "sl_pct": sl_pct,
                    "rrr": rrr,
                    "rsi": rsi_val,
                    "support": S1,
                    "resistance": R1,
                    "strategy": f"S&R Resistance Rejection ({timeframe})"
                }
                
        return {"setup_found": False, "reason": "No high-probability S&R setups meeting RRR bounds found"}
        
    except Exception as e:
        print(f"[ERROR] Error analyzing S&R strategy for {symbol} on {timeframe}: {e}")
        return {"setup_found": False, "reason": f"Execution error: {e}"}

