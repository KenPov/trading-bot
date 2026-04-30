import os
from dotenv import load_dotenv

load_dotenv()

# Hardcoded Telegram credentials
TELEGRAM_BOT_TOKEN = "8736079728:AAEF3i89antnk-dpo_1Bz86JHxyP8OnTBCA"
TELEGRAM_CHAT_ID = "-1003708562178"

# Bot configuration
SCAN_ALL_COINS = True
MAX_COINS = 30 # Limit to top 30 highest volume to avoid scam/low-liquidity coins
TIMEFRAMES = ["15m", "1h"]

STABLECOINS = ['USDC/USDT', 'DAI/USDT', 'USDG/USDT', 'USDE/USDT', 'PYUSD/USDT', 'FDUSD/USDT']

LOOKBACK_CANDLES = 250 # Increased to ensure 200 EMA calculation has enough data
RISK_REWARD_RATIO = 3.0
CHECK_INTERVAL_SECONDS = 100 # Scans every 100 seconds

# Supertrend Momentum Strategy Settings
EMA_PERIOD = 200

# Supertrend
SUPERTREND_LENGTH = 10
SUPERTREND_MULTIPLIER = 3.0

# RSI
RSI_PERIOD = 14
RSI_BULL_MOMENTUM = 50   # RSI > 50 for Longs
RSI_BEAR_MOMENTUM = 50   # RSI < 50 for Shorts
