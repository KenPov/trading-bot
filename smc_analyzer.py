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

    try:
        # Check the last closed candle (index -2) for the trigger, compared to index -3
        row = df.iloc[-2]
        prev_row = df.iloc[-3]
        
        # LONG SETUP: Supertrend flips to Bullish (1) from Bearish (-1)
        st_bull_flip = row['supertrend_dir'] == 1 and prev_row['supertrend_dir'] == -1
        is_uptrend = row['close'] > row['ema_200']
        rsi_bullish = row['rsi'] > config.RSI_BULL_MOMENTUM
        
        if st_bull_flip and is_uptrend and rsi_bullish:
            setup_found = True
            direction = "LONG"
            setup_type = "Supertrend Breakout"
            entry_price = current_px
            signal_id = f"ST_{df.index[-2]}_LONG_{symbol}_{timeframe}"
            sl = row['supertrend_val'] # SL at Supertrend line
            risk = entry_price - sl
            if risk > 0:
                tp = entry_price + (risk * config.RISK_REWARD_RATIO)
            else:
                setup_found = False # Safety check
                
        # SHORT SETUP: Supertrend flips to Bearish (-1) from Bullish (1)
        st_bear_flip = row['supertrend_dir'] == -1 and prev_row['supertrend_dir'] == 1
        is_downtrend = row['close'] < row['ema_200']
        rsi_bearish = row['rsi'] < config.RSI_BEAR_MOMENTUM
        
        if st_bear_flip and is_downtrend and rsi_bearish:
            setup_found = True
            direction = "SHORT"
            setup_type = "Supertrend Breakout"
            entry_price = current_px
            signal_id = f"ST_{df.index[-2]}_SHORT_{symbol}_{timeframe}"
            sl = row['supertrend_val']
            risk = sl - entry_price
            if risk > 0:
                tp = entry_price - (risk * config.RISK_REWARD_RATIO)
            else:
                setup_found = False
                
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
