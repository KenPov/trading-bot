import ccxt
import pandas as pd
import pandas_ta_classic as ta
import config
import time

# Create global exchange instances
exchange = ccxt.mexc({'enableRateLimit': True})

def get_active_usdt_markets():
    """
    Dynamically finds the 'Best Coins' for professional trading.
    Prioritizes high-volume, liquid markets that follow structural patterns.
    """
    try:
        # Fetch MEXC tickers for volume and price data
        tickers = exchange.fetch_tickers()
        
        candidates = []
        for symbol, data in tickers.items():
            # Filter: Must be USDT, not a stablecoin, and must have a price
            if '/USDT' in symbol and symbol not in config.STABLECOINS:
                quote_volume = data.get('quoteVolume', 0)
                last_price = data.get('last', 0)
                
                # Professional Filter:
                # 1. Minimum Volume ($1,000,000+ per 24h for basic liquidity)
                # 2. Exclude extremely cheap 'shitcoins' with too many zeros (manipulation risk)
                if quote_volume and quote_volume > 1000000 and last_price > 0.00001:
                    candidates.append({
                        "symbol": symbol,
                        "volume": quote_volume,
                        "change": abs(data.get('percentage', 0)) # Volatility/Trendiness
                    })
        
        # Sort by Volume first, then by movement (Trendiness)
        candidates.sort(key=lambda x: x['volume'], reverse=True)
        
        # Take the top MAX_COINS (e.g., top 250)
        final_list = [c['symbol'] for c in candidates[:config.MAX_COINS]]
        
        if not final_list:
            print("⚠️ No suitable coins found based on volume filters.")
            return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'] # Core fallback
            
        return final_list
        
    except Exception as e:
        print(f"Error fetching MEXC markets: {e}")
        return ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']

def fetch_data(symbol, timeframe, limit):
    """Fetches OHLCV data from MEXC using the shared instance."""
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df

def get_sr_levels(df, window=5):
    """
    Identifies significant Support and Resistance levels using local extrema.
    """
    levels = []
    for i in range(window, len(df) - window):
        # Resistance (Local High)
        if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
            levels.append({"price": df['high'].iloc[i], "type": "RESISTANCE"})
        # Support (Local Low)
        if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
            levels.append({"price": df['low'].iloc[i], "type": "SUPPORT"})
    return levels

def detect_fvg(df):
    """Detects the most recent Fair Value Gap (Imbalance)."""
    # Bullish FVG: Low of candle[i] > High of candle[i-2]
    # Bearish FVG: High of candle[i] < Low of candle[i-2]
    
    last_3 = df.iloc[-3:]
    curr_low = last_3.iloc[-1]['low']
    curr_high = last_3.iloc[-1]['high']
    prev2_high = last_3.iloc[-3]['high']
    prev2_low = last_3.iloc[-3]['low']
    
    # Bullish FVG
    if curr_low > prev2_high:
        gap = curr_low - prev2_high
        if gap / prev2_high > config.FVG_MIN_PCT:
            return {"type": "BULLISH", "top": curr_low, "bottom": prev2_high}
            
    # Bearish FVG
    if curr_high < prev2_low:
        gap = prev2_low - curr_high
        if gap / curr_high > config.FVG_MIN_PCT:
            return {"type": "BEARISH", "top": prev2_low, "bottom": curr_high}
            
    return None

def detect_msb(df, direction):
    """Detects Market Structure Break (MSB)."""
    lookback = config.STRUCT_LOOKBACK
    recent_data = df.iloc[-(lookback+1):-1]
    
    if direction == "LONG":
        # Break of recent Swing High
        recent_high = recent_data['high'].max()
        if df.iloc[-1]['close'] > recent_high:
            return True
    else:
        # Break of recent Swing Low
        recent_low = recent_data['low'].min()
        if df.iloc[-1]['close'] < recent_low:
            return True
    return False

def calculate_ote(df, direction):
    """Calculates Optimal Trade Entry levels based on the recent swing leg."""
    lookback = config.STRUCT_LOOKBACK
    recent_data = df.iloc[-lookback:]
    
    if direction == "LONG":
        low = recent_data['low'].min()
        high = recent_data['high'].max()
        diff = high - low
        ote_top = high - (diff * config.OTE_LOW)
        ote_bottom = high - (diff * config.OTE_HIGH)
        return {"top": ote_top, "bottom": ote_bottom}
    else:
        high = recent_data['high'].max()
        low = recent_data['low'].min()
        diff = high - low
        ote_top = low + (diff * config.OTE_HIGH)
        ote_bottom = low + (diff * config.OTE_LOW)
        return {"top": ote_top, "bottom": ote_bottom}

def analyze_trend_pullback(symbol):
    """
    Professional Sniper Strategy with SMC, OTE, and Market Structure.
    """
    try:
        # 1. Macro Trend Check (1 Hour)
        df_1h = fetch_data(symbol, config.TIMEFRAME_MACRO, 250)
        if len(df_1h) < 250: return {"setup_found": False}
        
        df_1h['ema_50'] = ta.ema(df_1h['close'], length=config.EMA_50)
        df_1h['ema_100'] = ta.ema(df_1h['close'], length=config.EMA_100)
        df_1h['ema_200'] = ta.ema(df_1h['close'], length=config.EMA_200)
        current_1h_close = df_1h.iloc[-1]['close']
        
        # Relaxed Macro Trend: Just check 50/100 EMA and price above/below
        macro_bullish = (df_1h.iloc[-1]['ema_50'] > df_1h.iloc[-1]['ema_100']) and (current_1h_close > df_1h.iloc[-1]['ema_100'])
        macro_bearish = (df_1h.iloc[-1]['ema_50'] < df_1h.iloc[-1]['ema_100']) and (current_1h_close < df_1h.iloc[-1]['ema_100'])

        # 2. Entry Timeframe Analysis (15 Minutes)
        df = fetch_data(symbol, config.TIMEFRAME_ENTRY, 250)
        if len(df) < 250: return {"setup_found": False}
        
        # Calculate Indicators
        df['ema_50'] = ta.ema(df['close'], length=config.EMA_50)
        df['ema_100'] = ta.ema(df['close'], length=config.EMA_100)
        df['ema_200'] = ta.ema(df['close'], length=config.EMA_200)
        
        # Supertrend
        supertrend = ta.supertrend(df['high'], df['low'], df['close'], length=config.SUPERTREND_LENGTH, multiplier=config.SUPERTREND_MULTIPLIER)
        df['supertrend_dir'] = supertrend[f'SUPERTd_{config.SUPERTREND_LENGTH}_{config.SUPERTREND_MULTIPLIER.is_integer() and int(config.SUPERTREND_MULTIPLIER) or config.SUPERTREND_MULTIPLIER}.0'] if f'SUPERTd_{config.SUPERTREND_LENGTH}_{config.SUPERTREND_MULTIPLIER.is_integer() and int(config.SUPERTREND_MULTIPLIER) or config.SUPERTREND_MULTIPLIER}.0' in supertrend.columns else supertrend.iloc[:, 1]
        
        # ADX, RSI, ATR, MACD, etc.
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=config.ADX_PERIOD)
        df['adx'] = adx_df[f'ADX_{config.ADX_PERIOD}']
        df['rsi'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=config.ATR_PERIOD)
        df['vol_sma'] = ta.sma(df['volume'], length=config.VOL_SMA_PERIOD)
        
        # MACD
        macd_df = ta.macd(df['close'], fast=config.MACD_FAST, slow=config.MACD_SLOW, signal=config.MACD_SIGNAL)
        macd_hist_col = [c for c in macd_df.columns if 'MACDh' in c][0]
        df['macd_hist'] = macd_df[macd_hist_col]
        
        # Bollinger Bands
        bbands = ta.bbands(df['close'], length=config.BB_LENGTH, std=config.BB_STD)
        df['bb_lower'] = bbands[f'BBL_{config.BB_LENGTH}_{config.BB_STD}']
        df['bb_upper'] = bbands[f'BBU_{config.BB_LENGTH}_{config.BB_STD}']
        
        # Professional Filters
        fvg = detect_fvg(df)
        
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_px = curr['close']
        # Relaxed ADX: If trend is strong OR if we have Supertrend alignment
        adx_strong = curr['adx'] > config.ADX_THRESHOLD or (curr['adx'] > 12)
        st_bullish = curr['supertrend_dir'] == 1
        st_bearish = curr['supertrend_dir'] == -1
        
        # Institutional Volume Confirm (check previous closed candle OR current spike)
        vol_confirm = (prev['volume'] > prev['vol_sma'] * config.VOLUME_INSTITUTIONAL_MULT) or \
                      (curr['volume'] > curr['vol_sma'] * config.VOLUME_INSTITUTIONAL_MULT)
        
        # ATR-based Risk
        raw_sl_pct = (curr['atr'] * 1.5) / current_px
        sl_pct = min(raw_sl_pct, config.MAX_SL_PERCENT)
        tp_pct = sl_pct * config.MIN_RR_RATIO
        
        # --- LONG SETUP ---
        if macro_bullish and adx_strong and st_bullish:
            # 1. Market Structure Break (Wait for pullback then break high)
            msb = detect_msb(df, "LONG")
            
            # 2. OTE Zone Check
            ote = calculate_ote(df, "LONG")
            in_ote_zone = current_px <= ote['top'] and current_px >= ote['bottom']
            
            # 3. RSI Hook
            rsi_hook = df['rsi'].iloc[-4:-1].min() < config.RSI_OVERSOLD and curr['rsi'] > prev['rsi']
            
            # Confluence: FVG detected recently OR In OTE Zone OR MSB occurred
            professional_confirm = msb or in_ote_zone or (fvg and fvg['type'] == "BULLISH")
            
            if professional_confirm and vol_confirm and rsi_hook:
                return {
                    "setup_found": True, "direction": "LONG", "symbol": symbol,
                    "entry_price": current_px, "tp": current_px * (1 + tp_pct),
                    "sl": current_px * (1 - sl_pct),
                    "signal_id": f"LONG_{int(time.time())}_{symbol}",
                    "strategy": "PRO_SNIPER_SMC"
                }

        # --- SHORT SETUP ---
        if macro_bearish and adx_strong and st_bearish:
            # 1. Market Structure Break
            msb = detect_msb(df, "SHORT")
            
            # 2. OTE Zone Check
            ote = calculate_ote(df, "SHORT")
            in_ote_zone = current_px >= ote['top'] and current_px <= ote['bottom']
            
            # 3. RSI Hook
            rsi_hook = df['rsi'].iloc[-4:-1].max() > config.RSI_OVERBOUGHT and curr['rsi'] < prev['rsi']
            
            # Confluence
            professional_confirm = msb or in_ote_zone or (fvg and fvg['type'] == "BEARISH")
            
            if professional_confirm and vol_confirm and rsi_hook:
                return {
                    "setup_found": True, "direction": "SHORT", "symbol": symbol,
                    "entry_price": current_px, "tp": current_px * (1 - tp_pct),
                    "sl": current_px * (1 + sl_pct),
                    "signal_id": f"SHORT_{int(time.time())}_{symbol}",
                    "strategy": "PRO_SNIPER_SMC"
                }
                
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")
        pass
        
    return {"setup_found": False}

def analyze_sr_opportunity(symbol):
    """
    Analyzes asset for 4h S/R opportunities. Returns a score and setup details.
    """
    try:
        # 1. Fetch 4h Data for S/R levels
        df_4h = fetch_data(symbol, config.TIMEFRAME_SR, 100)
        if len(df_4h) < 20: return None
        
        levels = get_sr_levels(df_4h)
        current_px = df_4h.iloc[-1]['close']
        
        # 2. Find closest levels
        support_levels = [l['price'] for l in levels if l['type'] == "SUPPORT" and l['price'] < current_px]
        resistance_levels = [l['price'] for l in levels if l['type'] == "RESISTANCE" and l['price'] > current_px]
        
        nearest_support = max(support_levels) if support_levels else None
        nearest_resistance = min(resistance_levels) if resistance_levels else None
        
        # 3. Calculate Scoring
        # Scoring is based on proximity to level. Closer to level = higher score (potential bounce).
        score = 0
        setup = None
        
        if nearest_support:
            dist_pct = (current_px - nearest_support) / nearest_support
            if dist_pct < 0.02: # Within 2% of support
                score = 100 - (dist_pct * 1000) # Higher score if closer
                setup = {
                    "symbol": symbol,
                    "direction": "LONG (Support Bounce)",
                    "price": current_px,
                    "level": nearest_support,
                    "type": "SUPPORT",
                    "score": score
                }
                
        if nearest_resistance:
            dist_pct = (nearest_resistance - current_px) / current_px
            if dist_pct < 0.02: # Within 2% of resistance
                res_score = 100 - (dist_pct * 1000)
                if res_score > score: # Take the better setup
                    score = res_score
                    setup = {
                        "symbol": symbol,
                        "direction": "SHORT (Resist Rejection)",
                        "price": current_px,
                        "level": nearest_resistance,
                        "type": "RESISTANCE",
                        "score": score
                    }
        
        return setup if score > 0 else None
        
    except Exception as e:
        print(f"Error scoring {symbol}: {e}")
        return None

def analyze_1h_movement(symbol):
    """
    Analyzes asset for 1-hour volatility to find the top movers.
    Returns a score based on the high-low percentage range of the recent 1h candle.
    """
    try:
        # Fetch 1h Data
        df = fetch_data(symbol, "1h", 3)
        if len(df) < 2: return None
        
        # Use the most recently closed candle for a stable metric (or the currently forming one)
        curr = df.iloc[-1]
        
        # Calculate 1-hour volatility (High - Low range as a percentage)
        if curr['low'] > 0:
            volatility_pct = ((curr['high'] - curr['low']) / curr['low']) * 100
            change_pct = ((curr['close'] - curr['open']) / curr['open']) * 100
        else:
            return None
            
        # We only want coins that are moving
        score = volatility_pct 
        
        direction = "LONG (Uptrending)" if change_pct > 0 else "SHORT (Downtrending)"
        
        # Minimum 0.5% movement in the last hour to be considered "moving"
        if score > 0.5:
            return {
                "symbol": symbol,
                "direction": direction,
                "price": curr['close'],
                "volatility": volatility_pct,
                "change": change_pct,
                "score": score
            }
            
        return None
        
    except Exception as e:
        print(f"Error analyzing 1h movement for {symbol}: {e}")
        return None


