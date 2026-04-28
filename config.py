import os
from dotenv import load_dotenv

load_dotenv()

# Hardcoded Telegram credentials
TELEGRAM_BOT_TOKEN = "8736079728:AAEF3i89antnk-dpo_1Bz86JHxyP8OnTBCA"
TELEGRAM_CHAT_ID = "-1003708562178"

# Bot configuration
SCAN_ALL_COINS = True
MAX_COINS = 50 # Limit to top 50 by volume to avoid extremely slow scans
TIMEFRAMES = ["15m", "1h"]

LOOKBACK_CANDLES = 250 # Increased to ensure 200 EMA calculation has enough data
RISK_REWARD_RATIO = 2.0
CHECK_INTERVAL_SECONDS = 120 # Scans every 2 minutes

# Golden Confluence Strategy Settings
EMA_PERIOD = 200

# Bollinger Bands
BB_PERIOD = 20
BB_STD_DEV = 2.0

# RSI
RSI_PERIOD = 14
RSI_OVERSOLD = 40     # We look for RSI recovering from < 40
RSI_OVERBOUGHT = 60   # We look for RSI recovering from > 60

# MACD
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
