import os
from dotenv import load_dotenv

load_dotenv()

# These will now be pulled safely from GitHub Actions Secrets
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Bot configuration
# Using XAUT/USDT (Tether Gold) because crypto exchanges track Gold using this token
ASSETS = ["BTC/USDT", "BNB/USDT", "ETH/USDT", "XAUT/USDT"]
TIMEFRAMES = ["15m", "1h"]

LOOKBACK_CANDLES = 200 # Enough data for structure/indicators
RISK_REWARD_RATIO = 2.0
CHECK_INTERVAL_SECONDS = 300 # Scans every 5 minutes

# RSI settings for Divergence Filter
RSI_PERIOD = 14
DIVERGENCE_LOOKBACK = 3 # Number of swing points to check for divergence
