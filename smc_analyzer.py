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

def analyze_smc(df, symbol, timeframe, external_bias=None):
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
        
        # SNIPER ENTRY: OTE (Optimal Trade Entry) at 70.5% Retracement
        # This is a much deeper pullback for high leverage (X75)
        range_size = row['high'] - row['low']
        ote_entry_long = row['high'] - (range_size * 0.705)
        ote_entry_short = row['low'] + (range_size * 0.705)
        
        # Target for X75 Leverage (400% ROE = 5.33% price move)
        TARGET_MOVE = 0.0533 
        MAX_SL_DIST = 0.012  # 1.2% Max SL to avoid liquidation at X75
        
        # LONG SETUP: Supertrend flips to Bullish (1) from Bearish (-1)
        st_bull_flip = row['supertrend_dir'] == 1 and prev_row['supertrend_dir'] == -1
        is_uptrend = row['close'] > row['ema_200']
        rsi_bullish = row['rsi'] > config.RSI_BULL_MOMENTUM
        
        if st_bull_flip and is_uptrend and rsi_bullish and vol_confirmed and htf_trend_bullish:
            # Only signal if we can still set a limit at the OTE level
            if current_px > ote_entry_long:
                setup_found = True
                direction = "LONG"
                setup_type = "PRO SNIPER (Vol + MTF + OTE)"
                entry_price = ote_entry_long
                signal_id = f"PRO_SNIPER_{df.index[-2]}_LONG_{symbol}_{timeframe}"
                
                # SL logic for X75: Use the tighter of Supertrend or 1.2%
                st_sl = row['supertrend_val']
                percent_sl = entry_price * (1 - MAX_SL_DIST)
                sl = max(st_sl, percent_sl) 
                
                # TP for 400% ROE
                tp = entry_price * (1 + TARGET_MOVE)
            else:
                pass
                
        # SHORT SETUP: Supertrend flips to Bearish (-1) from Bullish (1)
        st_bear_flip = row['supertrend_dir'] == -1 and prev_row['supertrend_dir'] == 1
        is_downtrend = row['close'] < row['ema_200']
        rsi_bearish = row['rsi'] < config.RSI_BEAR_MOMENTUM
        
        if st_bear_flip and is_downtrend and rsi_bearish and vol_confirmed and not htf_trend_bullish:
            if current_px < ote_entry_short:
                setup_found = True
                direction = "SHORT"
                setup_type = "PRO SNIPER (Vol + MTF + OTE)"
                entry_price = ote_entry_short
                signal_id = f"PRO_SNIPER_{df.index[-2]}_SHORT_{symbol}_{timeframe}"
                
                # SL logic for X75
                st_sl = row['supertrend_val']
                percent_sl = entry_price * (1 + MAX_SL_DIST)
                sl = min(st_sl, percent_sl)
                
                # TP for 400% ROE
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
