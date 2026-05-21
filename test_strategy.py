import config
from strategy import get_active_usdt_markets, analyze_futures_strategy, fetch_data, is_whale_pump_dump, calculate_sr_levels, cluster_levels

print("==================================================")
print("[TEST] RUNNING SUPPORT & RESISTANCE STRATEGY SANITY TESTS")
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

# Test 2: Test fetch_data and S&R Pivot detection on BTC/USDT
print("[STEP 2] Testing: fetch_data() and S&R calculations on BTC/USDT (1h)...")
try:
    df_btc = fetch_data("BTC/USDT", "1h", limit=100)
    if not df_btc.empty:
        print(f"Success! Fetched {len(df_btc)} candles of 1h data for BTC/USDT.")
        
        # Test Pivot Calculation
        raw_sup, raw_res = calculate_sr_levels(df_btc, window=config.SR_WINDOW)
        print(f"Detected {len(raw_sup)} raw Support levels and {len(raw_res)} raw Resistance levels.")
        
        # Test Clustering
        clustered_sup = cluster_levels(raw_sup, threshold_pct=0.01)
        clustered_res = cluster_levels(raw_res, threshold_pct=0.01)
        print(f"Clustered down to {len(clustered_sup)} Support zones and {len(clustered_res)} Resistance zones.")
        print(f"Key Support zones: {[f'{s:.2f}' for s in clustered_sup[-3:]] if clustered_sup else []}")
        print(f"Key Resistance zones: {[f'{r:.2f}' for r in clustered_res[:3]] if clustered_res else []}\n")
    else:
        print("Error: Fetched BTC dataframe is empty!\n")
except Exception as e:
    print(f"Error in fetch/S&R calculation: {e}\n")

# Test 3: Test S&R strategy analysis on BTC/USDT (1h and 4h)
print("[STEP 3] Testing: analyze_futures_strategy() on BTC/USDT...")
for tf in ["1h", "4h"]:
    try:
        result = analyze_futures_strategy("BTC/USDT", timeframe=tf)
        print(f"Success! BTC/USDT {tf} scan completed.")
        print(f"Result details for {tf}:")
        for k, v in result.items():
            print(f"  - {k}: {v}")
        print()
    except Exception as e:
        print(f"Error in analyze_futures_strategy for BTC on {tf}: {e}\n")

# Test 4: Run strategy on a few top active movers to find any setups
if active_movers:
    print("[STEP 4] Scanning top 5 active movers for S&R setups...")
    setups_found = []
    for coin in active_movers[:5]:
        for tf in ["1h", "4h"]:
            try:
                res = analyze_futures_strategy(coin, timeframe=tf)
                if res.get('setup_found'):
                    setups_found.append(res)
                    print(f"  [FOUND] {res['direction']} setup on {coin} ({tf})!")
            except Exception as e:
                print(f"  Error analyzing {coin} on {tf}: {e}")
    print(f"Scan complete. Found {len(setups_found)} total setups from top 5 coins.")

print("==================================================")
print("[TEST] SANITY TESTS COMPLETED")
print("==================================================")
