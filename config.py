import os

# Telegram Credentials
TELEGRAM_BOT_TOKEN = "8736079728:AAEF3i89antnk-dpo_1Bz86JHxyP8OnTBCA"
TELEGRAM_CHAT_ID = "-1003708562178"

# Scanning configuration
EXCHANGE_ID = 'mexc'
MAX_COINS = 250 # Dynamically scans the top 250 most active coins
TIMEFRAME_ENTRY = "15m"
TIMEFRAME_MACRO = "1h"

# Exclude stablecoins and low-liquidity pairs
STABLECOINS = ['USDC/USDT', 'DAI/USDT', 'USDG/USDT', 'USDE/USDT', 'PYUSD/USDT', 'FDUSD/USDT', 'TUSD/USDT', 'BUSD/USDT']

# Strategy Parameters
EMA_PERIOD = 200
RSI_PERIOD = 14
RSI_OVERSOLD = 32 
RSI_OVERBOUGHT = 68 
BB_LENGTH = 20
BB_STD = 2.2 # Sniper precision

# Risk Reward for X75 Leverage
# Goal: $2 margin -> $4 profit ($6 total)
TP_PRICE_MOVE = 0.0267 
SL_PRICE_MOVE = 0.012 # Tight SL to avoid liquidation at 75x

CHECK_INTERVAL_SECONDS = 60 
SIGNAL_COOLDOWN_MINUTES = 120 
