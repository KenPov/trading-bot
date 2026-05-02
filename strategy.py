import ccxt
import pandas as pd
import pandas_ta_classic as ta
import config
import time

# Create a single global exchange instance for rate limit management
exchange = ccxt.mexc({'enableRateLimit': True})

def get_active_usdt_markets():
    """Dynamically finds high-volume USDT markets from MEXC."""
    try:
        # Fetch all tickers to get volume data
        tickers = exchange.fetch_tickers()
        
        usdt_pairs = []
        for symbol, data in tickers.items():
            # Filter: Must be USDT, not a stablecoin
            if '/USDT' in symbol and symbol not in config.STABLECOINS:
                quote_volume = data.get('quoteVolume', 0)
                # Minimum 100k USDT volume to avoid extremely low liquidity "shitcoins"
                if quote_volume and quote_volume > 100000: 
                    usdt_pairs.append((symbol, quote_volume))
        
        # Sort by volume (highest first)
        usdt_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Take the top MAX_COINS (e.g. Top 150)
        # These are almost guaranteed to be the ones also listed on Binance
        final_list = [pair[0] for pair in usdt_pairs[:config.MAX_COINS]]
        
        return final_list
    except Exception as e:
        print(f"Error fetching markets: {e}")
        # Fallback to mainstream coins if dynamic fetch fails
        return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT']

def fetch_data(symbol, timeframe, limit):
    """Fetches OHLCV data from MEXC using the shared instance."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def analyze_trend_pullback(symbol):
    """
    The Ultimate High-Leverage (X75) Sniper Strategy.
    Scans for both Long and Short setups at key bounce levels.
    """
    try:
        # 1. Macro Trend Check (1 Hour)
        df_1h = fetch_data(symbol, config.TIMEFRAME_MACRO, 250)
        if len(df_1h) < 250: return {"setup_found": False}
        
        df_1h['ema_200'] = ta.ema(df_1h['close'], length=config.EMA_PERIOD)
        current_1h_close = df_1h.iloc[-1]['close']
        macro_ema = df_1h.iloc[-1]['ema_200']
        
        macro_bullish = current_1h_close > macro_ema
        macro_bearish = current_1h_close < macro_ema

        # 2. Entry Timeframe Analysis (15 Minutes)
        df = fetch_data(symbol, config.TIMEFRAME_ENTRY, 250)
        if len(df) < 250: return {"setup_found": False}
        
        df['ema_200'] = ta.ema(df['close'], length=config.EMA_PERIOD)
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        
        bbands = ta.bbands(df['close'], length=config.BB_LENGTH, std=config.BB_STD)
        df['bb_lower'] = bbands[f'BBL_{config.BB_LENGTH}_{config.BB_STD}']
        df['bb_upper'] = bbands[f'BBU_{config.BB_LENGTH}_{config.BB_STD}']
        
        current_px = df.iloc[-1]['close']
        current_ema = df.iloc[-1]['ema_200']
        
        recent_low = df['low'].iloc[-3:].min()
        recent_high = df['high'].iloc[-3:].max()
        recent_rsi_min = df['rsi'].iloc[-3:].min()
        recent_rsi_max = df['rsi'].iloc[-3:].max()
        
        # --- LONG SETUP ---
        if macro_bullish and current_px > current_ema:
            dip_detected = recent_rsi_min < config.RSI_OVERSOLD and recent_low < df.iloc[-1]['bb_lower']
            if dip_detected:
                limit_entry = current_ema
                if current_px > limit_entry:
                    return {
                        "setup_found": True, "direction": "LONG", "symbol": symbol,
                        "entry_price": limit_entry, "tp": limit_entry * (1 + config.TP_PRICE_MOVE),
                        "sl": limit_entry * (1 - config.SL_PRICE_MOVE),
                        "signal_id": f"LONG_{int(time.time())}_{symbol}"
                    }

        # --- SHORT SETUP ---
        if macro_bearish and current_px < current_ema:
            peak_detected = recent_rsi_max > config.RSI_OVERBOUGHT and recent_high > df.iloc[-1]['bb_upper']
            if peak_detected:
                limit_entry = current_ema
                if current_px < limit_entry:
                    return {
                        "setup_found": True, "direction": "SHORT", "symbol": symbol,
                        "entry_price": limit_entry, "tp": limit_entry * (1 - config.TP_PRICE_MOVE),
                        "sl": limit_entry * (1 + config.SL_PRICE_MOVE),
                        "signal_id": f"SHORT_{int(time.time())}_{symbol}"
                    }
                
    except Exception as e:
        pass
        
    return {"setup_found": False}
