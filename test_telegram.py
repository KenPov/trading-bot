import asyncio
from telegram_notifier import send_signal

# Create a mock/dummy signal to test the formatting and connection
mock_signal = {
    "symbol": "TEST/USDT",
    "timeframe": "1h",
    "setup_type": "Bot Connection Test",
    "direction": "LONG",
    "entry_price": 60000.00,
    "tp": 62000.00,
    "sl": 55555.00
}

print("Attempting to send test message to Telegram...")
try:
    asyncio.run(send_signal(mock_signal))
    print("Test command completed! Check your Telegram group: KH TP Alert.")
except Exception as e:
    print(f"Error occurred: {e}")