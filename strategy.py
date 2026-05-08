import ccxt
import pandas as pd
import pandas_ta_classic as ta
import config
import time

# Create global exchange instances
exchange = ccxt.mexc({'enableRateLimit': True})

# Static Whitelist of Binance USDT-M Futures Symbols
# This ensures validation without needing an API connection to Binance
BINANCE_FUTURES_WHITELIST = [
    'BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'DOT/USDT', 
    'MATIC/USDT', 'LINK/USDT', 'LTC/USDT', 'TRX/USDT', 'BCH/USDT', 'SHIB/USDT', 'AVAX/USDT', 'ATOM/USDT', 
    'UNI/USDT', 'ETC/USDT', 'FIL/USDT', 'ALGO/USDT', 'NEAR/USDT', 'ICP/USDT', 'VET/USDT', 'FTM/USDT', 
    'SAND/USDT', 'MANA/USDT', 'AXS/USDT', 'EGLD/USDT', 'THETA/USDT', 'HBAR/USDT', 'GRT/USDT', 'AAVE/USDT', 
    'EOS/USDT', 'FLOW/USDT', 'KSM/USDT', 'ZEC/USDT', 'NEO/USDT', 'MKR/USDT', 'DASH/USDT', 'WAVES/USDT', 
    'SNX/USDT', 'CHZ/USDT', 'ENJ/USDT', 'CRV/USDT', 'LRC/USDT', 'ONE/USDT', 'GALA/USDT', 'ANKR/USDT', 
    'REEF/USDT', 'KAVA/USDT', 'BAND/USDT', 'IOST/USDT', 'OMG/USDT', 'ZIL/USDT', 'REN/USDT', 'LINA/USDT', 
    'SFP/USDT', 'RAY/USDT', 'SRM/USDT', 'DYDX/USDT', 'GTC/USDT', 'ENS/USDT', 'PEOPLE/USDT', 'APE/USDT', 
    'GMT/USDT', 'OP/USDT', 'LDO/USDT', 'APT/USDT', 'ARB/USDT', 'SUI/USDT', 'PEPE/USDT', 'ORDI/USDT', 
    'TIA/USDT', 'PYTH/USDT', 'JUP/USDT', 'STRK/USDT', 'ENA/USDT', 'W/USDT', 'TNSR/USDT', 'SAGA/USDT', 
    'OMNI/USDT', 'REZ/USDT', 'NOT/USDT', 'IO/USDT', 'ZK/USDT', 'LISTA/USDT', 'ZRO/USDT', 'RENDER/USDT',
    'WIF/USDT', 'BONK/USDT', 'FLOKI/USDT', 'TURBO/USDT', '1000SATS/USDT', '1000RATS/USDT', 'PIXEL/USDT',
    'PORTAL/USDT', 'AEVO/USDT', 'ETHFI/USDT', 'BOME/USDT', 'TAO/USDT', 'BANANA/USDT', 'DOGS/USDT',
    'HMSTR/USDT', 'CATI/USDT', 'EIGEN/USDT', 'SCR/USDT', 'GRASS/USDT', 'DRIFT/USDT', 'PENGU/USDT',
    'MOVE/USDT', 'ME/USDT', 'VIRTUE/USDT', 'UXLINK/USDT', 'POPOCAT/USDT', 'POPCAT/USDT', 'BRETT/USDT',
    'ZRO/USDT', 'BLAST/USDT', 'ZK/USDT', 'LISTA/USDT', 'ZRO/USDT', 'RENDER/USDT', 'TAO/USDT'
]

def get_active_usdt_markets():
    """Finds high-volume MEXC markets that are also in the static Binance Futures whitelist."""
    try:
        # Fetch MEXC tickers for volume data
        tickers = exchange.fetch_tickers()
        
        usdt_pairs = []
        for symbol, data in tickers.items():
            # Filter: Must be USDT, not a stablecoin, AND must be in our Static Whitelist
            if '/USDT' in symbol and symbol not in config.STABLECOINS:
                if symbol in BINANCE_FUTURES_WHITELIST:
                    quote_volume = data.get('quoteVolume', 0)
                    if quote_volume and quote_volume > 100000: 
                        usdt_pairs.append((symbol, quote_volume))
        
        # Sort by volume (highest first)
        usdt_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Take the top MAX_COINS
        final_list = [pair[0] for pair in usdt_pairs[:config.MAX_COINS]]
        
        if not final_list:
            print("⚠️ No matching coins found. Check whitelist or volume.")
            return BINANCE_FUTURES_WHITELIST[:10] # Fallback to top of whitelist
            
        return final_list
        
    except Exception as e:
        print(f"Error fetching MEXC markets: {e}")
        return BINANCE_FUTURES_WHITELIST[:10] # Fallback to top of whitelist if MEXC fails

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
        
        df_1h['ema_50'] = ta.ema(df_1h['close'], length=config.EMA_50)
        df_1h['ema_100'] = ta.ema(df_1h['close'], length=config.EMA_100)
        df_1h['ema_200'] = ta.ema(df_1h['close'], length=config.EMA_200)
        current_1h_close = df_1h.iloc[-1]['close']
        
        macro_bullish = (df_1h.iloc[-1]['ema_50'] > df_1h.iloc[-1]['ema_100']) and (df_1h.iloc[-1]['ema_100'] > df_1h.iloc[-1]['ema_200']) and (current_1h_close > df_1h.iloc[-1]['ema_50'])
        macro_bearish = (df_1h.iloc[-1]['ema_50'] < df_1h.iloc[-1]['ema_100']) and (df_1h.iloc[-1]['ema_100'] < df_1h.iloc[-1]['ema_200']) and (current_1h_close < df_1h.iloc[-1]['ema_50'])

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
        
        # ADX
        adx_df = ta.adx(df['high'], df['low'], df['close'], length=config.ADX_PERIOD)
        df['adx'] = adx_df[f'ADX_{config.ADX_PERIOD}']
        
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
        current_ema_200 = curr['ema_200']
        current_ema_50 = curr['ema_50']
        current_ema_100 = curr['ema_100']
        
        entry_bullish = (current_ema_50 > current_ema_100) and (current_ema_100 > current_ema_200)
        entry_bearish = (current_ema_50 < current_ema_100) and (current_ema_100 < current_ema_200)
        
        adx_strong = curr['adx'] > config.ADX_THRESHOLD
        st_bullish = curr['supertrend_dir'] == 1
        st_bearish = curr['supertrend_dir'] == -1
        
        # ATR-based Risk Calculation (Capped at MAX_SL_PERCENT)
        raw_sl_pct = (curr['atr'] * 1.5) / current_px
        sl_pct = min(raw_sl_pct, config.MAX_SL_PERCENT)
        tp_pct = sl_pct * config.MIN_RR_RATIO
        
        # --- LONG SETUP ---
        if macro_bullish and entry_bullish and adx_strong and st_bullish and current_px > current_ema_50:
            # 1. Pullback Zone: Price dipped near lower BB or EMA 50 recently
            dip_detected = recent_low < prev['bb_lower'] or recent_low < prev['ema_50'] * 1.002
            
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
        if macro_bearish and entry_bearish and adx_strong and st_bearish and current_px < current_ema_50:
            # 1. Pullback Zone: Price spiked near upper BB or EMA 50 recently
            peak_detected = recent_high > prev['bb_upper'] or recent_high > prev['ema_50'] * 0.998
            
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
