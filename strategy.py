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
    Golden Confluence High-Leverage (X75) Sniper Strategy.
    Scans for Long/Short setups at key levels with momentum confirmation.
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
        
        # Calculate Indicators
        df['ema_200'] = ta.ema(df['close'], length=config.EMA_PERIOD)
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=config.ATR_PERIOD)
        df['vol_sma'] = ta.sma(df['volume'], length=config.VOL_SMA_PERIOD)
        
        # MACD Calculation
        macd_df = ta.macd(df['close'], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
        macd_hist_col = [c for c in macd_df.columns if 'MACDh' in c][0]
        df['macd_hist'] = macd_df[macd_hist_col]
        
        # Bollinger Bands
        bbands = ta.bbands(df['close'], length=config.BB_LENGTH, std=config.BB_STD)
        df['bb_lower'] = bbands[f'BBL_{config.BB_LENGTH}_{config.BB_STD}']
        df['bb_upper'] = bbands[f'BBU_{config.BB_LENGTH}_{config.BB_STD}']
        
        # Current and Previous Data points
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        # Structural Variables (last 3 completed candles)
        recent_low = df['low'].iloc[-4:-1].min()
        recent_high = df['high'].iloc[-4:-1].max()
        recent_rsi_min = df['rsi'].iloc[-4:-1].min()
        recent_rsi_max = df['rsi'].iloc[-4:-1].max()
        
        current_px = curr['close']
        current_ema = curr['ema_200']
        
        # ATR-based Risk Calculation (Capped at MAX_SL_PERCENT)
        raw_sl_pct = (curr['atr'] * 1.5) / current_px
        sl_pct = min(raw_sl_pct, config.MAX_SL_PERCENT)
        tp_pct = sl_pct * config.MIN_RR_RATIO
        
        # --- LONG SETUP ---
        if macro_bullish and current_px > current_ema:
            # 1. Pullback Zone: Price dipped near lower BB or EMA recently
            dip_detected = recent_low < prev['bb_lower'] or recent_low < prev['ema_200'] * 1.002
            
            # 2. RSI Hook: Was oversold, now turning up
            rsi_hook = recent_rsi_min < config.RSI_OVERSOLD and curr['rsi'] > prev['rsi']
            
            # 3. MACD Momentum Shift: Histogram rising (bearish momentum fading)
            macd_bullish = curr['macd_hist'] > prev['macd_hist']
            
            # 4. Volume Confirmation: High volume on the bounce
            vol_confirm = curr['volume'] > curr['vol_sma'] or prev['volume'] > prev['vol_sma']
            
            if dip_detected and rsi_hook and macd_bullish and vol_confirm:
                return {
                    "setup_found": True, "direction": "LONG", "symbol": symbol,
                    "entry_price": current_px, "tp": current_px * (1 + tp_pct),
                    "sl": current_px * (1 - sl_pct),
                    "signal_id": f"LONG_{int(time.time())}_{symbol}"
                }

        # --- SHORT SETUP ---
        if macro_bearish and current_px < current_ema:
            # 1. Pullback Zone: Price spiked near upper BB or EMA recently
            peak_detected = recent_high > prev['bb_upper'] or recent_high > prev['ema_200'] * 0.998
            
            # 2. RSI Hook: Was overbought, now turning down
            rsi_hook = recent_rsi_max > config.RSI_OVERBOUGHT and curr['rsi'] < prev['rsi']
            
            # 3. MACD Momentum Shift: Histogram falling (bullish momentum fading)
            macd_bearish = curr['macd_hist'] < prev['macd_hist']
            
            # 4. Volume Confirmation: High volume on the rejection
            vol_confirm = curr['volume'] > curr['vol_sma'] or prev['volume'] > prev['vol_sma']
            
            if peak_detected and rsi_hook and macd_bearish and vol_confirm:
                return {
                    "setup_found": True, "direction": "SHORT", "symbol": symbol,
                    "entry_price": current_px, "tp": current_px * (1 - tp_pct),
                    "sl": current_px * (1 + sl_pct),
                    "signal_id": f"SHORT_{int(time.time())}_{symbol}"
                }
                
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        pass
        
    return {"setup_found": False}
