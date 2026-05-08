import config
from strategy import analyze_trend_pullback

print("Testing Golden Confluence Strategy on BTC/USDT...")
result = analyze_trend_pullback("BTC/USDT")
print("Result:")
print(result)
print("Test completed successfully!")
