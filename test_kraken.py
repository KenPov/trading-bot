import ccxt
import config

def test():
    print("Testing Kraken...")
    exchange = ccxt.kraken()
    print("Loading markets...")
    markets = exchange.load_markets()
    usdt_pairs = [symbol for symbol in markets if '/USDT' in symbol]
    print(f"Found {len(usdt_pairs)} USDT pairs.")
    if len(usdt_pairs) > 0:
        print(f"Top 5: {usdt_pairs[:5]}")

if __name__ == "__main__":
    test()
