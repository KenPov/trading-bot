import ccxt
import pandas as pd
import pandas_ta_classic as ta
import config

def get_active_usdt_markets():
    exchange = ccxt.kraken()
    tickers = exchange.fetch_tickers()
    
    usdt_pairs = []
    for symbol, data in tickers.items():
        if '/USDT' in symbol and symbol not in config.STABLECOINS and data.get('quoteVolume') is not None:
            usdt_pairs.append((symbol, data['quoteVolume']))
            
    usdt_pairs.sort(key=lambda x: x[1], reverse=True)
    sorted_symbols = [pair[0] for pair in usdt_pairs]
    
    return sorted_symbols[:config.MAX_COINS]

def fetch_data(symbol, timeframe, limit):
    exchange = ccxt.kraken({'enableRateLimit': True})
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def analyze_trend_pullback(symbol):
    """
    The Ultimate EMA Bounce Strategy for X75 Leverage.
    Only takes Longs during panic dips in a macro uptrend.
    """
    try:
        # 1. Macro Trend Check (1 Hour)
        df_1h = fetch_data(symbol, config.TIMEFRAME_MACRO, 250)
        if len(df_1h) < 250: return {"setup_found": False}
        
        df_1h['ema_200'] = ta.ema(df_1h['close'], length=config.EMA_PERIOD)
        macro_bullish = df_1h.iloc[-1]['close'] > df_1h.iloc[-1]['ema_200']
        
        if not macro_bullish:
            return {"setup_found": False} # We strictly only buy dips in an uptrend

        # 2. Micro Trend & Pullback Check (15 Minutes)
        df = fetch_data(symbol, config.TIMEFRAME_ENTRY, 250)
        if len(df) < 250: return {"setup_found": False}
        
        df['ema_200'] = ta.ema(df['close'], length=config.EMA_PERIOD)
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        
        # Calculate Bollinger Bands
        bbands = ta.bbands(df['close'], length=config.BB_LENGTH, std=config.BB_STD)
        df['bb_lower'] = bbands[f'BBL_{config.BB_LENGTH}_{config.BB_STD}']
        
        current_px = df.iloc[-1]['close']
        current_ema = df.iloc[-1]['ema_200']
        
        # Check if we are in a Micro Uptrend
        micro_bullish = current_px > current_ema
        
        # Check for a Panic Dip (RSI Oversold AND piercing lower BB)
        # We check the last 2 closed candles to catch recent dips
        row1 = df.iloc[-2]
        row2 = df.iloc[-3]
        
        dip_found = (row1['rsi'] < config.RSI_OVERSOLD and row1['low'] < row1['bb_lower']) or \
                    (row2['rsi'] < config.RSI_OVERSOLD and row2['low'] < row2['bb_lower'])
                    
        if micro_bullish and dip_found:
            # We found a panic dip in a strong uptrend.
            # Entry point is exactly at the 200 EMA to catch the ultimate bounce
            limit_entry = current_ema
            
            # Ensure the price hasn't already fallen below our limit entry
            if current_px > limit_entry:
                tp = limit_entry * (1 + config.TP_PRICE_MOVE)
                sl = limit_entry * (1 - config.SL_PRICE_MOVE)
                
                signal_id = f"SNIPER_DIP_{df.index[-1]}_{symbol}"
                
                return {
                    "setup_found": True,
                    "direction": "LONG",
                    "symbol": symbol,
                    "entry_price": limit_entry,
                    "tp": tp,
                    "sl": sl,
                    "signal_id": signal_id
                }
                
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        
    return {"setup_found": False}
