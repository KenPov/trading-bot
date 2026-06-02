import os
from dotenv import load_dotenv

# Load environment variables if present (useful for local development or CI)
load_dotenv()

# Telegram Credentials
# Fallback to the user's hardcoded credentials, but prioritize environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8736079728:AAG-lenOZTBEaYN6VzV8YIGipDgtFwgq-G8")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1003708562178")

# Scanning Configuration
EXCHANGE_ID = 'mexc'
ACTIVE_COINS_TO_SCAN = 100     # Dynamically scan the top 100 most active moving coins
MIN_24H_VOLUME = 1000000       # Only scan coins with > $1,000,000 24h volume (ensures basic futures liquidity)
SCAN_TIMEFRAMES = ["1h", "4h"] # Timeframes to scan for S&R opportunities

# Exclude stablecoins and non-volatile index assets
STABLECOINS = [
    'USDC/USDT', 'DAI/USDT', 'USDG/USDT', 'USDE/USDT', 
    'PYUSD/USDT', 'FDUSD/USDT', 'TUSD/USDT', 'BUSD/USDT'
]

# Hardcoded exclude list for coins that are not on Binance or highly manipulative index tokens
EXCLUDED_COINS = [
    'USDGO/USDT', 'MX/USDT', 'RAIN/USDT', 'XP/USDT', 'USD1/USDT'
]


# Whale Pump & Dump / Flash Manipulation Filter
# Compares current candle range and volume against the statistical average of recent history
WHALE_RANGE_MULTIPLIER = 3.5  # Reject if candle price range is > 3.5x standard deviation of the last 20 candles
WHALE_VOLUME_MULTIPLIER = 4.0 # Reject if candle volume is > 4.0x standard deviation of the last 20 candles
WHALE_WICK_THRESHOLD = 0.65   # Reject if wick length represents > 65% of the total high-low range (flash rejection)

# Technical Indicator Parameters
RSI_PERIOD = 14
ATR_PERIOD = 14

# Support & Resistance Strategy Parameters
SR_WINDOW = 5                  # Left and right candle lookback to confirm pivot highs/lows (fractals)
SR_PROXIMITY_PCT = 0.015       # Price must be within 1.5% of Support or Resistance to trigger a setup
SR_MIN_RRR = 2.0               # Minimum Risk-to-Reward Ratio (e.g. profit target is at least 2.0x of the stop loss)
LEVERAGE = 20                  # Recommended leverage level for futures signals (20x)

# Signal Tracking and Cooldown
SIGNAL_COOLDOWN_MINUTES = 1440 # Wait 24 hours before sending another signal for the same coin/timeframe
SIGNAL_TRACKER_FILE = "last_signals.json"

