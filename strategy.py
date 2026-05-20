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

def analyze_futures_strategy(symbol):
    """
    Main strategy generator targeting moving coins.
    Confluence indicators: Dual EMA (20/50), RSI (strength bounds), MACD (momentum), ADX (trend strength).
    Risk settings: ATR-based dynamic Stop Loss and Take Profit.
    """
    try:
        # 1. Fetch entry timeframe data (5m)
        df_5m = fetch_data(symbol, config.TIMEFRAME_ENTRY, limit=100)
        if df_5m.empty or len(df_5m) < 50:
            return {"setup_found": False, "reason": "Insufficient 5m historical data"}
            
        # 2. Fetch macro trend timeframe data (15m)
        df_15m = fetch_data(symbol, config.TIMEFRAME_TREND, limit=100)
        if df_15m.empty or len(df_15m) < 50:
            return {"setup_found": False, "reason": "Insufficient 15m trend data"}

        # 3. Apply Whale Pump & Dump Filter immediately
        if is_whale_pump_dump(df_5m):
            return {"setup_found": False, "reason": "Whale Pump/Dump detection flagged"}
            
        # --- MACRO TREND ALIGNMENT (15m) ---
        df_15m['ema_fast'] = ta.ema(df_15m['close'], length=config.EMA_FAST)
        df_15m['ema_slow'] = ta.ema(df_15m['close'], length=config.EMA_SLOW)
        
        macro_close = df_15m.iloc[-1]['close']
        macro_ema20 = df_15m.iloc[-1]['ema_fast']
        macro_ema50 = df_15m.iloc[-1]['ema_slow']
        
        macro_bullish = macro_close > macro_ema20 > macro_ema50
        macro_bearish = macro_close < macro_ema20 < macro_ema50
        
        if not macro_bullish and not macro_bearish:
            return {"setup_found": False, "reason": "Macro trend is not strongly aligned"}

        # --- ENTRY CONFLUENCE CALCULATION (5m) ---
        # Calculate Dual EMA
        df_5m['ema_fast'] = ta.ema(df_5m['close'], length=config.EMA_FAST)
        df_5m['ema_slow'] = ta.ema(df_5m['close'], length=config.EMA_SLOW)
        
        # Calculate RSI
        df_5m['rsi'] = ta.rsi(df_5m['close'], length=config.RSI_PERIOD)
        
        # Calculate ADX
        adx_df = ta.adx(df_5m['high'], df_5m['low'], df_5m['close'], length=config.ADX_PERIOD)
        df_5m['adx'] = adx_df[f'ADX_{config.ADX_PERIOD}']
        
        # Calculate MACD
        macd_df = ta.macd(df_5m['close'], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
        macd_hist_col = [c for c in macd_df.columns if 'MACDh' in c][0]
        df_5m['macd_hist'] = macd_df[macd_hist_col]
        
        # Calculate ATR for dynamic risk pricing
        df_5m['atr'] = ta.atr(df_5m['high'], df_5m['low'], df_5m['close'], length=config.ATR_PERIOD)
        
        # Retrieve latest candles
        curr = df_5m.iloc[-1]
        prev = df_5m.iloc[-2]
        prev2 = df_5m.iloc[-3]
        
        current_price = curr['close']
        atr_value = curr['atr']
        
        # Trend strength check
        trend_strong = curr['adx'] >= config.ADX_MIN
        if not trend_strong:
            return {"setup_found": False, "reason": f"ADX too low ({curr['adx']:.1f} < {config.ADX_MIN})"}

        # --- LONG SIGNAL DETECTION ---
        if macro_bullish:
            # 5m Trend confirmation
            entry_trend_bullish = current_price > curr['ema_fast'] > curr['ema_slow']
            
            # Pullback logic: Close is resting near the EMA 20, OR EMA 20 crossed over EMA 50 within the last 3 candles
            near_ema20 = abs(current_price - curr['ema_fast']) / curr['ema_fast'] <= 0.003
            in_ema_pocket = curr['ema_slow'] <= current_price <= curr['ema_fast']
            ema_cross = (prev['ema_fast'] <= prev['ema_slow'] and curr['ema_fast'] > curr['ema_slow']) or \
                        (prev2['ema_fast'] <= prev2['ema_slow'] and prev['ema_fast'] > prev['ema_slow'])
            
            pullback_confirmed = near_ema20 or in_ema_pocket or ema_cross
            
            # RSI momentum space: strong, active, but has room to climb (not overbought)
            rsi_confirmed = config.RSI_LONG_MIN <= curr['rsi'] <= config.RSI_LONG_MAX
            
            # MACD bullish momentum: positive and increasing histogram
            macd_confirmed = curr['macd_hist'] > 0 and curr['macd_hist'] > prev['macd_hist']
            
            if entry_trend_bullish and pullback_confirmed and rsi_confirmed and macd_confirmed:
                # Dynamic ATR-based Stop Loss (1.5 * ATR below current price)
                sl = current_price - (atr_value * 1.5)
                sl_pct = (current_price - sl) / current_price
                
                # Enforce Strict Maximum SL Limit
                if sl_pct > config.MAX_SL_PERCENT:
                    sl = current_price * (1.0 - config.MAX_SL_PERCENT)
                    sl_pct = config.MAX_SL_PERCENT
                
                # Take Profit based on exact Risk Reward Ratio
                tp = current_price + (current_price - sl) * config.RISK_REWARD_RATIO
                
                return {
                    "setup_found": True,
                    "direction": "LONG",
                    "symbol": symbol,
                    "entry_price": current_price,
                    "tp": tp,
                    "sl": sl,
                    "sl_pct": sl_pct * 100,
                    "leverage": config.LEVERAGE,
                    "rsi": curr['rsi'],
                    "adx": curr['adx'],
                    "strategy": "MOMENTUM_PULLBACK_5M"
                }

        # --- SHORT SIGNAL DETECTION ---
        if macro_bearish:
            # 5m Trend confirmation
            entry_trend_bearish = current_price < curr['ema_fast'] < curr['ema_slow']
            
            # Pullback logic: Close is resting near the EMA 20, OR EMA 20 crossed below EMA 50 within the last 3 candles
            near_ema20 = abs(current_price - curr['ema_fast']) / curr['ema_fast'] <= 0.003
            in_ema_pocket = curr['ema_fast'] <= current_price <= curr['ema_slow']
            ema_cross = (prev['ema_fast'] >= prev['ema_slow'] and curr['ema_fast'] < curr['ema_slow']) or \
                        (prev2['ema_fast'] >= prev2['ema_slow'] and prev['ema_fast'] < prev['ema_slow'])
            
            pullback_confirmed = near_ema20 or in_ema_pocket or ema_cross
            
            # RSI momentum space: strong downward trend, but has room to drop (not oversold)
            rsi_confirmed = config.RSI_SHORT_MIN <= curr['rsi'] <= config.RSI_SHORT_MAX
            
            # MACD bearish momentum: negative and decreasing histogram
            macd_confirmed = curr['macd_hist'] < 0 and curr['macd_hist'] < prev['macd_hist']
            
            if entry_trend_bearish and pullback_confirmed and rsi_confirmed and macd_confirmed:
                # Dynamic ATR-based Stop Loss (1.5 * ATR above current price)
                sl = current_price + (atr_value * 1.5)
                sl_pct = (sl - current_price) / current_price
                
                # Enforce Strict Maximum SL Limit
                if sl_pct > config.MAX_SL_PERCENT:
                    sl = current_price * (1.0 + config.MAX_SL_PERCENT)
                    sl_pct = config.MAX_SL_PERCENT
                
                # Take Profit based on exact Risk Reward Ratio
                tp = current_price - (sl - current_price) * config.RISK_REWARD_RATIO
                
                return {
                    "setup_found": True,
                    "direction": "SHORT",
                    "symbol": symbol,
                    "entry_price": current_price,
                    "tp": tp,
                    "sl": sl,
                    "sl_pct": sl_pct * 100,
                    "leverage": config.LEVERAGE,
                    "rsi": curr['rsi'],
                    "adx": curr['adx'],
                    "strategy": "MOMENTUM_PULLBACK_5M"
                }

        return {"setup_found": False, "reason": "Technical indicators did not align"}
        
    except Exception as e:
        print(f"[ERROR] Error analyzing strategy for {symbol}: {e}")
        return {"setup_found": False, "reason": f"Execution error: {e}"}
