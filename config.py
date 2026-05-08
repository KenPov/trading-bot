import os

# Telegram Credentials
TELEGRAM_BOT_TOKEN = "8317215211:AAFR_pTgQptiT5N79Y9VzcftotceBbXLAhE"
TELEGRAM_CHAT_ID = "-1003708562178"

# Scanning configuration
EXCHANGE_ID = 'mexc'
MAX_COINS = 250 # Dynamically scans the top 250 most active coins
TIMEFRAME_ENTRY = "15m"
TIMEFRAME_MACRO = "1h"

# Exclude stablecoins and low-liquidity pairs
STABLECOINS = ['USDC/USDT', 'DAI/USDT', 'USDG/USDT', 'USDE/USDT', 'PYUSD/USDT', 'FDUSD/USDT', 'TUSD/USDT', 'BUSD/USDT']

# Strategy Parameters
EMA_50 = 50
EMA_100 = 100
EMA_200 = 200
RSI_PERIOD = 14
RSI_OVERSOLD = 30 # Stricter oversold condition
RSI_OVERBOUGHT = 70 # Stricter overbought condition
BB_LENGTH = 20
BB_STD = 2.2 # Sniper precision

# Golden Confluence Additions
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
VOL_SMA_PERIOD = 20
ATR_PERIOD = 14
ADX_PERIOD = 14
ADX_THRESHOLD = 25 # Minimum trend strength required
SUPERTREND_LENGTH = 10
SUPERTREND_MULTIPLIER = 3.0

# Risk Reward for X75 Leverage
MAX_SL_PERCENT = 0.012 # Strict SL cap at 1.2% to avoid liquidation at 75x
MIN_RR_RATIO = 2.5 # Target a 1:2.5 Risk-to-Reward Ratio

CHECK_INTERVAL_SECONDS = 60 
SIGNAL_COOLDOWN_MINUTES = 120 
