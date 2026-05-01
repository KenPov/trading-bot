import ccxt
import pandas as pd
import pandas_ta_classic as ta
import config

def get_active_usdt_markets():
    exchange = ccxt.kraken()
    tickers = exchange.fetch_tickers()
    
    # Filter for USDT pairs, exclude stablecoins, and sort by 24h volume
    usdt_pairs = []
    for symbol, data in tickers.items():
        if '/USDT' in symbol and symbol not in getattr(config, 'STABLECOINS', []) and data.get('quoteVolume') is not None:
            usdt_pairs.append((symbol, data['quoteVolume']))
            
    # Sort by volume descending
    usdt_pairs.sort(key=lambda x: x[1], reverse=True)
    sorted_symbols = [pair[0] for pair in usdt_pairs]
    
    if hasattr(config, 'MAX_COINS') and config.MAX_COINS:
        return sorted_symbols[:config.MAX_COINS]
    return sorted_symbols

def fetch_data(symbol, timeframe, limit):
    # Using Kraken - It is US-based and will NOT block GitHub Actions.
    exchange = ccxt.kraken({
        'enableRateLimit': True,
    })
    
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def get_btc_trend():
    """
    Determines the master trend of the market using BTC's 4h 200 EMA.
    Returns 'BULLISH', 'BEARISH', or 'UNKNOWN'
    """
    try:
        # Check 4h timeframe for solid BTC trend
        df = fetch_data("BTC/USDT", "4h", 250)
        ema_200 = ta.ema(df['close'], length=200)
        current_close = df.iloc[-1]['close']
        current_ema = ema_200.iloc[-1]
        if current_close > current_ema:
            return "BULLISH"
        else:
            return "BEARISH"
    except Exception as e:
        print(f"Failed to fetch BTC trend: {e}")
        return "UNKNOWN"

def analyze_smc(df, symbol, timeframe, external_bias=None, btc_trend="UNKNOWN"):
    """
    Supertrend Momentum Breakout Strategy
    Calculates Supertrend, 200 EMA, and RSI for high-probability signals.
    Note: kept the function name `analyze_smc` to prevent breaking imports in main.py
    """
    if len(df) < 250: # Minimum data check for 200 EMA
        return {"setup_found": False}

    try:
        # Calculate Indicators
        # 1. EMA 200
        df['ema_200'] = ta.ema(df['close'], length=config.EMA_PERIOD)
        
        # 2. Supertrend
        st = ta.supertrend(df['high'], df['low'], df['close'], length=config.SUPERTREND_LENGTH, multiplier=config.SUPERTREND_MULTIPLIER)
        if st is None or st.empty:
            return {"setup_found": False}
            
        st_dir_col = [col for col in st.columns if col.startswith('SUPERTd_')][0]
        st_val_col = [col for col in st.columns if col.startswith('SUPERT_')][0]
        df['supertrend_dir'] = st[st_dir_col]
        df['supertrend_val'] = st[st_val_col]
        
        # 3. RSI
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        
        # 4. Volume MA (for Volume Confirmation)
        df['vol_ma'] = df['volume'].rolling(window=10).mean()
        
    except Exception as e:
        print(f"Error calculating indicators for {symbol} {timeframe}: {e}")
        return {"setup_found": False}
        
    current_px = df.iloc[-1]['close']
    current_time = df.index[-1]
    
    setup_found = False
    setup_type = ""
    direction = ""
    entry_price = 0
    sl = 0
    tp = 0
    signal_id = ""

    # --- PROFESSIONAL MTF TREND CHECK ---
    # Only take 15m signals if 1h trend is aligned. Only 1h if 4h is aligned.
    higher_tf = "1h" if timeframe == "15m" else "4h"
    try:
        # Re-use exchange instance to check higher timeframe
        exchange = ccxt.kraken({'enableRateLimit': True})
        htf_ohlcv = exchange.fetch_ohlcv(symbol, higher_tf, limit=50)
        htf_df = pd.DataFrame(htf_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        htf_ema = ta.ema(htf_df['close'], length=50) # Faster EMA for HTF trend
        htf_trend_bullish = htf_df['close'].iloc[-1] > htf_ema.iloc[-1]
    except Exception as e:
        print(f"MTF Check failed for {symbol}: {e}")
        htf_trend_bullish = True # Default to True if fetch fails to avoid missing all signals

    try:
        # Check the last closed candle (index -2) for the trigger
        row = df.iloc[-2]
        prev_row = df.iloc[-3]
        
        # Volume Confirmation: Trigger candle volume > 1.5x average
        vol_confirmed = row['volume'] > (row['vol_ma'] * 1.5)
        
        # Target for X75 Leverage (350% ROE = 4.66% price move)
        TARGET_MOVE = 0.0466 
        MAX_SL_DIST = 0.012  # 1.2% Max SL to avoid liquidation at X75 (approx 90% ROE loss)
        
        # LONG SETUP: Supertrend flips to Bullish (1) from Bearish (-1)
        st_bull_flip = row['supertrend_dir'] == 1 and prev_row['supertrend_dir'] == -1
        is_uptrend = row['close'] > row['ema_200']
        rsi_bullish = row['rsi'] > config.RSI_BULL_MOMENTUM
        
        # BTC Trend Filter: Only LONG if BTC is BULLISH
        btc_aligned_long = btc_trend == "BULLISH" or btc_trend == "UNKNOWN"
        
        if st_bull_flip and is_uptrend and rsi_bullish and vol_confirmed and htf_trend_bullish and btc_aligned_long:
            # DEEP LIMIT ENTRY: Wait for a pullback to the Supertrend Support Line
            deep_entry_long = row['supertrend_val']
            
            # Only signal if we can still set a limit at the deep entry level
            if current_px > deep_entry_long:
                setup_found = True
                direction = "LONG"
                setup_type = "PRO SNIPER (Deep Limit + BTC Sync)"
                entry_price = deep_entry_long
                signal_id = f"PRO_SNIPER_{df.index[-2]}_LONG_{symbol}_{timeframe}"
                
                # SL logic for X75: Fixed 1.2% below the deep entry
                sl = entry_price * (1 - MAX_SL_DIST)
                
                # TP for 350% ROE
                tp = entry_price * (1 + TARGET_MOVE)
            else:
                pass
                
        # SHORT SETUP: Supertrend flips to Bearish (-1) from Bullish (1)
        st_bear_flip = row['supertrend_dir'] == -1 and prev_row['supertrend_dir'] == 1
        is_downtrend = row['close'] < row['ema_200']
        rsi_bearish = row['rsi'] < config.RSI_BEAR_MOMENTUM
        
        # BTC Trend Filter: Only SHORT if BTC is BEARISH
        btc_aligned_short = btc_trend == "BEARISH" or btc_trend == "UNKNOWN"
        
        if st_bear_flip and is_downtrend and rsi_bearish and vol_confirmed and not htf_trend_bullish and btc_aligned_short:
            # DEEP LIMIT ENTRY: Wait for a pullback to the Supertrend Resistance Line
            deep_entry_short = row['supertrend_val']
            
            if current_px < deep_entry_short:
                setup_found = True
                direction = "SHORT"
                setup_type = "PRO SNIPER (Deep Limit + BTC Sync)"
                entry_price = deep_entry_short
                signal_id = f"PRO_SNIPER_{df.index[-2]}_SHORT_{symbol}_{timeframe}"
                
                # SL logic for X75: Fixed 1.2% above the deep entry
                sl = entry_price * (1 + MAX_SL_DIST)
                
                # TP for 350% ROE
                tp = entry_price * (1 - TARGET_MOVE)
            else:
                pass
                
    except Exception as e:
        print(f"Error in strategy logic for {symbol}: {e}")
        
    return {
        "setup_found": setup_found,
        "setup_type": setup_type,
        "direction": direction,
        "entry_price": entry_price,
        "sl": sl,
        "tp": tp,
        "signal_id": signal_id,
        "current_time": current_time,
        "bias": "TREND"
    }
