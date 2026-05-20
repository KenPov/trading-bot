import config
from strategy import get_active_usdt_markets, analyze_futures_strategy, fetch_data, is_whale_pump_dump

print("==================================================")
print("[TEST] RUNNING FUTURES STRATEGY SANITY TESTS")
print("==================================================\n")

# Test 1: Fetch active movers
print("[STEP 1] Testing: get_active_usdt_markets()...")
try:
    active_movers = get_active_usdt_markets()
    print(f"Success! Retrieved {len(active_movers)} active movers.")
    print(f"Sample movers: {active_movers[:5]}\n")
except Exception as e:
    print(f"Error in get_active_usdt_markets: {e}\n")
    active_movers = ['BTC/USDT', 'ETH/USDT']

# Test 2: Test fetch_data and whale pump check on BTC/USDT
print("[STEP 2] Testing: fetch_data() and is_whale_pump_dump() on BTC/USDT...")
try:
    df_btc = fetch_data("BTC/USDT", config.TIMEFRAME_ENTRY, limit=50)
    if not df_btc.empty:
        print(f"Success! Fetched {len(df_btc)} candles of 5m data for BTC/USDT.")
        is_whale = is_whale_pump_dump(df_btc)
        print(f"Anti-Whale analysis: Is BTC/USDT under whale manipulation? -> {'YES (Flagged)' if is_whale else 'NO (Safe)'}\n")
    else:
        print("Error: Fetched dataframe is empty!\n")
except Exception as e:
    print(f"Error in fetch/whale check: {e}\n")

# Test 3: Test futures strategy analysis on BTC/USDT
print("[STEP 3] Testing: analyze_futures_strategy() on BTC/USDT...")
try:
    result = analyze_futures_strategy("BTC/USDT")
    print("Success! Strategy run completed.")
    print("BTC Strategy Output details:")
    for k, v in result.items():
        print(f"  - {k}: {v}")
    print()
except Exception as e:
    print(f"Error in analyze_futures_strategy for BTC: {e}\n")

# Test 4: Run strategy on the top active mover
if active_movers:
    top_coin = active_movers[0]
    print(f"[STEP 4] Testing: analyze_futures_strategy() on Top Mover ({top_coin})...")
    try:
        result_mover = analyze_futures_strategy(top_coin)
        print("Success! Strategy run completed.")
        print(f"{top_coin} Strategy Output details:")
        for k, v in result_mover.items():
            print(f"  - {k}: {v}")
        print()
    except Exception as e:
        print(f"Error in analyze_futures_strategy for {top_coin}: {e}\n")

print("==================================================")
print("[TEST] SANITY TESTS COMPLETED")
print("==================================================")
