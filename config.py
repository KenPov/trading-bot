import os

# Telegram Credentials
TELEGRAM_BOT_TOKEN = "8736079728:AAEF3i89antnk-dpo_1Bz86JHxyP8OnTBCA"
TELEGRAM_CHAT_ID = "-1003708562178"

# Scanning configuration
MAX_COINS = 30
TIMEFRAME_ENTRY = "15m"
TIMEFRAME_MACRO = "1h"

# Exclude stablecoins
STABLECOINS = ['USDC/USDT', 'DAI/USDT', 'USDG/USDT', 'USDE/USDT', 'PYUSD/USDT', 'FDUSD/USDT']

# Strategy Parameters
EMA_PERIOD = 200
RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
BB_LENGTH = 20
BB_STD = 2.0

# Risk Reward for X75 Leverage
# Target: $2 -> $6 (300% ROE = 4.0% price move)
# Risk: Lose 90% of $2 (1.2% price move max to avoid liquidation)
TP_PRICE_MOVE = 0.040 
SL_PRICE_MOVE = 0.012 

CHECK_INTERVAL_SECONDS = 100
SIGNAL_COOLDOWN_MINUTES = 60
