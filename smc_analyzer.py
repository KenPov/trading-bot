import ccxt
import pandas as pd
import pandas_ta_classic as ta
from smartmoneyconcepts import smc
import config

def get_active_usdt_markets():
    exchange = ccxt.kraken()
    markets = exchange.load_markets()
    # Filter for USDT pairs
    usdt_pairs = [symbol for symbol in markets if '/USDT' in symbol]
    
    if hasattr(config, 'MAX_COINS') and config.MAX_COINS:
        return usdt_pairs[:config.MAX_COINS]
    return usdt_pairs

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

def get_market_bias(bos_choch_df):
    """
    Determine underlying market bias by checking the most recent CHoCH or BOS
    """
    # Iterate backwards looking for the latest structure break
    for i in range(len(bos_choch_df)-1, -1, -1):
        row = bos_choch_df.iloc[i]
        if 'BOS' in row and row['BOS'] != 0:
            return "BULLISH" if row['BOS'] == 1 else "BEARISH"
        if 'CHoCH' in row and row['CHoCH'] != 0:
            return "BULLISH" if row['CHoCH'] == 1 else "BEARISH"
            
    return "NEUTRAL"

def analyze_smc(df, symbol, timeframe, external_bias=None):
    """
    Given a dataframe, calculate the Golden Confluence Strategy (EMA, BB, MACD, RSI, SMC)
    for the best entries on all coins.
    """
    if len(df) < 50: # Minimum data check
        return {"setup_found": False}

    try:
        # Calculate Indicators
        # 1. EMA 200
        df['ema_200'] = ta.ema(df['close'], length=config.EMA_PERIOD)
        
        # 2. Bollinger Bands
        bbands = ta.bbands(df['close'], length=config.BB_PERIOD, std=config.BB_STD_DEV)
        if bbands is None or bbands.empty:
            return {"setup_found": False}
            
        bbl_col = [col for col in bbands.columns if 'BBL' in col][0]
        bbu_col = [col for col in bbands.columns if 'BBU' in col][0]
        df['bbl'] = bbands[bbl_col]
        df['bbu'] = bbands[bbu_col]
        
        # 3. RSI
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        
        # 4. MACD
        macd = ta.macd(df['close'], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
        if macd is None or macd.empty:
            return {"setup_found": False}
            
        macd_col = [col for col in macd.columns if col.startswith('MACD_')][0]
        macds_col = [col for col in macd.columns if col.startswith('MACDs_')][0]
        df['macd'] = macd[macd_col]
        df['macd_signal'] = macd[macds_col]
        
        # 5. SMC Bias Context
        swing_highs_lows = smc.swing_highs_lows(df)
        bos_choch_df = smc.bos_choch(df, swing_highs_lows)
        
        bias = external_bias if external_bias else get_market_bias(bos_choch_df)
        
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
        # Check the last 3 candles for the trigger (to catch crossovers)
        for i in range(-3, 0):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            
            # LONG SETUP CONFLUENCE
            is_uptrend = row['close'] > row['ema_200']
            touched_lower_bb = row['low'] <= row['bbl'] or prev_row['low'] <= prev_row['bbl']
            macd_bull_cross = row['macd'] > row['macd_signal'] and prev_row['macd'] <= prev_row['macd_signal']
            rsi_oversold_recovery = row['rsi'] < config.RSI_OVERSOLD or prev_row['rsi'] < config.RSI_OVERSOLD
            
            if is_uptrend and touched_lower_bb and macd_bull_cross and rsi_oversold_recovery:
                setup_found = True
                direction = "LONG"
                setup_type = "Golden Confluence (EMA200 + BB + MACD + RSI)"
                entry_price = current_px
                signal_id = f"GOLDEN_{df.index[i]}_LONG_{symbol}_{timeframe}"
                sl = row['bbl'] * 0.995 # SL slightly below Bollinger Band
                risk = entry_price - sl
                tp = entry_price + (risk * config.RISK_REWARD_RATIO)
                break
                
            # SHORT SETUP CONFLUENCE
            is_downtrend = row['close'] < row['ema_200']
            touched_upper_bb = row['high'] >= row['bbu'] or prev_row['high'] >= prev_row['bbu']
            macd_bear_cross = row['macd'] < row['macd_signal'] and prev_row['macd'] >= prev_row['macd_signal']
            rsi_overbought_recovery = row['rsi'] > config.RSI_OVERBOUGHT or prev_row['rsi'] > config.RSI_OVERBOUGHT
            
            if is_downtrend and touched_upper_bb and macd_bear_cross and rsi_overbought_recovery:
                setup_found = True
                direction = "SHORT"
                setup_type = "Golden Confluence (EMA200 + BB + MACD + RSI)"
                entry_price = current_px
                signal_id = f"GOLDEN_{df.index[i]}_SHORT_{symbol}_{timeframe}"
                sl = row['bbu'] * 1.005 # SL slightly above Bollinger Band
                risk = sl - entry_price
                tp = entry_price - (risk * config.RISK_REWARD_RATIO)
                break
                
    except Exception as e:
        print(f"Error in confluence logic for {symbol}: {e}")
        
    return {
        "setup_found": setup_found,
        "setup_type": setup_type,
        "direction": direction,
        "entry_price": entry_price,
        "sl": sl,
        "tp": tp,
        "signal_id": signal_id,
        "current_time": current_time,
        "bias": bias
    }
