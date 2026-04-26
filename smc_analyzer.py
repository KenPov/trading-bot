import ccxt
import pandas as pd
import pandas_ta_classic as ta
from smartmoneyconcepts import smc
import config

def fetch_data(symbol, timeframe, limit):
    # Using Kraken - It is US-based and will NOT block GitHub Actions.
    # It has very accurate data for BTC, ETH, BNB, and Gold (XAUT).
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

def check_rsi_divergence(df, swing_df, direction):
    """
    Checks if there is a momentum divergence at the current price
    Direction LONG: Price Lower Low (or equal) while RSI Higher Low
    Direction SHORT: Price Higher High (or equal) while RSI Lower High
    """
    try:
        current_rsi = df['rsi'].iloc[-1]
        current_px = df['close'].iloc[-1]
        
        # We look back at the last few structural swings to compare
        if direction == "LONG":
            # Filter for swing lows (-1)
            swings = swing_df[swing_df['HighLow'] == -1].tail(config.DIVERGENCE_LOOKBACK)
            for idx, row in swings.iterrows():
                # Compare current price/rsi to this past swing point
                prev_rsi = df.loc[idx, 'rsi']
                prev_px = df.loc[idx, 'low']
                
                # Bullish Divergence: Price is lower or same, but RSI is stronger (higher)
                if current_px <= prev_px and current_rsi > prev_rsi:
                    return True
        else:
            # Filter for swing highs (1)
            swings = swing_df[swing_df['HighLow'] == 1].tail(config.DIVERGENCE_LOOKBACK)
            for idx, row in swings.iterrows():
                prev_rsi = df.loc[idx, 'rsi']
                prev_px = df.loc[idx, 'high']
                
                # Bearish Divergence: Price is higher or same, but RSI is weaker (lower)
                if current_px >= prev_px and current_rsi < prev_rsi:
                    return True
    except Exception:
        pass
    
    return False

def analyze_smc(df, symbol, timeframe, external_bias=None):
    """
    Given a dataframe, calculate SMC indicators and find the 'Perfect best entry'
    """
    
    try:
        # Calculate RSI first
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        
        fvg_df = smc.fvg(df)
        swing_highs_lows = smc.swing_highs_lows(df)
        ob_df = smc.ob(df, swing_highs_lows)
        bos_choch_df = smc.bos_choch(df, swing_highs_lows)
        
        # Use HTF bias if provided (MTF Confirmation), otherwise calculate from current DF
        bias = external_bias if external_bias else get_market_bias(bos_choch_df)
        
    except Exception as e:
        print(f"Error calculating SMC/RSI for {symbol} {timeframe}: {e}")
        return {"setup_found": False}
        
    current_px = df.iloc[-1]['close']
    current_time = df.index[-1]
    
    setup_found = False
    setup_type = ""
    direction = ""
    entry_price = 0
    sl = 0
    tp = 0
    divergence_confirmed = False
    signal_id = ""

    # "Perfect Best Entry" Rules:
    # 1. OB must be unmitigated
    # 2. OB direction MUST align with the market bias
    # 3. RSI Divergence MUST be present (The momentum filter)

    try:
        recent_obs = ob_df.iloc[-25:] 
        for i in range(len(recent_obs)-1, -1, -1):
            row = recent_obs.iloc[i]
            
            if 'OB' in row and row['OB'] != 0 and ('Mitigated' in row and row['Mitigated'] == 0):
                ob_dir = "LONG" if row['OB'] == 1 else "SHORT"
                
                # 1. TREND FILTER
                if ob_dir == "LONG" and bias != "BULLISH":
                    continue 
                if ob_dir == "SHORT" and bias != "BEARISH":
                    continue 

                top = row['Top']
                bottom = row['Bottom']
                
                # 2. PRICE ACTION (Are we in the zone?)
                if bottom <= current_px <= top:
                    # 3. MOMENTUM FILTER (The RSI Divergence check)
                    divergence_confirmed = check_rsi_divergence(df, swing_highs_lows, ob_dir)
                    
                    if divergence_confirmed:
                        setup_found = True
                        setup_type = f"Perfect SMC Entry (Bias: {bias} + RSI Divergence)"
                        direction = ob_dir
                        entry_price = current_px
                        signal_id = f"PERFECT_{recent_obs.index[i]}_{direction}_{symbol}_{timeframe}"
                        
                        if direction == "LONG":
                            sl = bottom * 0.998
                            risk = entry_price - sl
                            tp = entry_price + (risk * config.RISK_REWARD_RATIO)
                        else:
                            sl = top * 1.002
                            risk = sl - entry_price
                            tp = entry_price - (risk * config.RISK_REWARD_RATIO)
                        break
                    else:
                        # Potential setup but no momentum confirmation yet
                        pass

    except Exception as e:
        print(f"Error parsing SMC output: {e}")
        
    return {
        "setup_found": setup_found,
        "setup_type": setup_type,
        "direction": direction,
        "entry_price": entry_price,
        "sl": sl,
        "tp": tp,
        "divergence_confirmed": divergence_confirmed,
        "signal_id": signal_id,
        "current_time": current_time,
        "bias": bias
    }
