import os
from dotenv import load_dotenv

# Load environment variables if present (useful for local development or CI)
load_dotenv()

# Telegram Credentials
# Fallback to the user's hardcoded credentials, but prioritize environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8317215211:AAFR_pTgQptiT5N79Y9VzcftotceBbXLAhE")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003708562178")

# Scanning Configuration
EXCHANGE_ID = 'mexc'
CHECK_INTERVAL_SECONDS = 60   # Scan every 1 minute
ACTIVE_COINS_TO_SCAN = 100     # Dynamically scan the top 100 most active moving coins
MIN_24H_VOLUME = 1000000       # Only scan coins with > $1,000,000 24h volume (ensures basic futures liquidity)
TIMEFRAME_ENTRY = "5m"        # Entry signal timeframe (ultra-responsive 5-minute candles)
TIMEFRAME_TREND = "15m"       # Macro trend alignment timeframe

# Exclude stablecoins and non-volatile index assets
STABLECOINS = [
    'USDC/USDT', 'DAI/USDT', 'USDG/USDT', 'USDE/USDT', 
    'PYUSD/USDT', 'FDUSD/USDT', 'TUSD/USDT', 'BUSD/USDT'
]

# Whale Pump & Dump / Flash Manipulation Filter
# Compares current candle range and volume against the statistical average of recent history
WHALE_RANGE_MULTIPLIER = 3.5  # Reject if candle price range is > 3.5x standard deviation of the last 20 candles
WHALE_VOLUME_MULTIPLIER = 4.0 # Reject if candle volume is > 4.0x standard deviation of the last 20 candles
WHALE_WICK_THRESHOLD = 0.65   # Reject if wick length represents > 65% of the total high-low range (flash rejection)

# Technical Indicator Parameters
EMA_FAST = 20                 # Fast trend EMA
EMA_SLOW = 50                 # Slow trend EMA
RSI_PERIOD = 14
# RSI bounds to ensure we enter inside a strong moving trend but NOT overbought/oversold (leaves room to run)
RSI_LONG_MIN = 50
RSI_LONG_MAX = 68
RSI_SHORT_MIN = 32
RSI_SHORT_MAX = 50

# MACD Settings
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

# ADX Trend Strength Filter
ADX_PERIOD = 14
ADX_MIN = 20                  # Minimum ADX value ensuring a strong active trend (not ranging/silent)

# ATR & Risk Management Parameters
ATR_PERIOD = 14
RISK_REWARD_RATIO = 1.5       # Target a clean 1:1.5 Risk-to-Reward ratio
MAX_SL_PERCENT = 0.015        # Strict stop loss cap at 1.5% to protect margin
LEVERAGE = 20                 # Recommended leverage level for futures signals (20x)

# Signal Tracking and Cooldown
SIGNAL_COOLDOWN_MINUTES = 30  # Wait at least 30 minutes before sending another signal for the same coin
SIGNAL_TRACKER_FILE = "last_signals.json"
