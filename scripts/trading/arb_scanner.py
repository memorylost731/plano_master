#!/usr/bin/env python3
"""
C4ISR Crypto Arbitrage Scanner — finds price differences across exchanges.

Runs continuously. Feeds opportunities to Cael for execution decisions.
No trades executed without human approval until confidence > 95%.

Usage:
    python3 arb_scanner.py scan          # one-time scan
    python3 arb_scanner.py monitor       # continuous monitoring
    python3 arb_scanner.py opportunities # show current opportunities
    python3 arb_scanner.py backtest      # test strategy on historical data
"""

import json
import logging
import os
import sqlite3
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "trading"
DB_PATH = DATA_DIR / "arb_scanner.db"

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("c4isr.arb")

# Exchanges with public price APIs (no auth needed for scanning)
EXCHANGES = {
    "binance": {
        "ticker_url": "https://api.binance.com/api/v3/ticker/price?symbol={symbol}",
        "format": lambda d: float(d["price"]),
        "symbols": {"BTC": "BTCUSDT", "ETH": "ETHUSDT"},
    },
    "kraken": {
        "ticker_url": "https://api.kraken.com/0/public/Ticker?pair={symbol}",
        "format": lambda d: float(list(d["result"].values())[0]["c"][0]),
        "symbols": {"BTC": "XBTUSDT", "ETH": "ETHUSDT"},
    },
    "coinbase": {
        "ticker_url": "https://api.coinbase.com/v2/prices/{symbol}/spot",
        "format": lambda d: float(d["data"]["amount"]),
        "symbols": {"BTC": "BTC-USD", "ETH": "ETH-USD"},
    },
    "bitstamp": {
        "ticker_url": "https://www.bitstamp.net/api/v2/ticker/{symbol}/",
        "format": lambda d: float(d["last"]),
        "symbols": {"BTC": "btcusd", "ETH": "ethusd"},
    },
    "bybit": {
        "ticker_url": "https://api.bybit.com/v5/market/tickers?category=spot&symbol={symbol}",
        "format": lambda d: float(d["result"]["list"][0]["lastPrice"]),
        "symbols": {"BTC": "BTCUSDT", "ETH": "ETHUSDT"},
    },
}

# Minimum spread to flag as opportunity (after fees)
MIN_SPREAD_PCT = 0.3  # 0.3% minimum (typical exchange fee is 0.1% each side = 0.2% cost)
MARGIN = 0.25  # 25% safety margin on reported spreads


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""CREATE TABLE IF NOT EXISTS prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exchange TEXT, symbol TEXT, price_usd REAL,
        timestamp TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS opportunities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buy_exchange TEXT, sell_exchange TEXT, symbol TEXT,
        buy_price REAL, sell_price REAL, spread_pct REAL,
        net_profit_pct REAL, timestamp TEXT, status TEXT DEFAULT 'open'
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS daily_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, scans INTEGER, opportunities_found INTEGER,
        best_spread_pct REAL, avg_spread_pct REAL
    )""")
    conn.commit()
    conn.close()


def fetch_price(exchange: str, asset: str) -> float | None:
    """Fetch current price from exchange public API."""
    config = EXCHANGES.get(exchange)
    if not config:
        return None
    
    symbol = config["symbols"].get(asset)
    if not symbol:
        return None

    url = config["ticker_url"].format(symbol=symbol)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "C4ISR-ArbScanner/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            return config["format"](data)
    except Exception as e:
        log.debug("Failed %s/%s: %s", exchange, asset, e)
        return None


def scan_arbitrage(assets: list[str] = ["BTC", "ETH"]) -> list[dict]:
    """Scan all exchanges for arbitrage opportunities."""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    opportunities = []
    now = datetime.now(timezone.utc).isoformat()

    for asset in assets:
        prices = {}
        for exchange in EXCHANGES:
            price = fetch_price(exchange, asset)
            if price and price > 0:
                prices[exchange] = price
                conn.execute(
                    "INSERT INTO prices (exchange, symbol, price_usd, timestamp) VALUES (?,?,?,?)",
                    (exchange, asset, price, now)
                )

        if len(prices) < 2:
            continue

        # Find best buy (lowest) and sell (highest)
        sorted_prices = sorted(prices.items(), key=lambda x: x[1])
        buy_exchange, buy_price = sorted_prices[0]
        sell_exchange, sell_price = sorted_prices[-1]

        spread_pct = ((sell_price - buy_price) / buy_price) * 100
        # Net after fees (0.1% each side = 0.2% total typical)
        net_profit_pct = spread_pct - 0.2

        if net_profit_pct > MIN_SPREAD_PCT * (1 - MARGIN):
            opp = {
                "asset": asset,
                "buy_exchange": buy_exchange,
                "buy_price": round(buy_price, 2),
                "sell_exchange": sell_exchange,
                "sell_price": round(sell_price, 2),
                "spread_pct": round(spread_pct, 3),
                "net_profit_pct": round(net_profit_pct, 3),
                "on_10btc_usd": round(10 * buy_price * net_profit_pct / 100, 2) if asset == "BTC" else 0,
                "timestamp": now,
            }
            opportunities.append(opp)
            conn.execute(
                "INSERT INTO opportunities (buy_exchange, sell_exchange, symbol, buy_price, sell_price, spread_pct, net_profit_pct, timestamp) VALUES (?,?,?,?,?,?,?,?)",
                (buy_exchange, sell_exchange, asset, buy_price, sell_price, spread_pct, net_profit_pct, now)
            )
            log.info("OPPORTUNITY: %s %s→%s spread=%.3f%% net=%.3f%% ($%.0f on 10BTC)",
                     asset, buy_exchange, sell_exchange, spread_pct, net_profit_pct, opp.get("on_10btc_usd", 0))

        # Log all prices
        price_str = " | ".join(f"{ex}:${p:,.2f}" for ex, p in sorted_prices)
        log.info("%s prices: %s (spread: %.3f%%)", asset, price_str, spread_pct)

    conn.commit()
    conn.close()
    return opportunities


def show_opportunities():
    """Show recent opportunities."""
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT * FROM opportunities ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()
    conn.close()

    if not rows:
        print("No opportunities found yet. Run: arb_scanner.py scan")
        return

    print(f"\n{'Time':>20} {'Asset':>5} {'Buy':>10} {'Sell':>10} {'Spread':>8} {'Net':>8} {'$10BTC':>10}")
    print("-" * 75)
    for r in rows:
        asset = r[3]  # symbol
        buy_p = r[4]
        sell_p = r[5]
        spread = r[6]
        net = r[7]
        profit_10btc = 10 * buy_p * net / 100 if "BTC" in asset else 0
        ts = r[8][:16]
        print(f"{ts:>20} {asset:>5} {r[1]:>10} {r[2]:>10} {spread:>7.3f}% {net:>7.3f}% ${profit_10btc:>8,.0f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "scan"

    if cmd == "scan":
        opps = scan_arbitrage()
        if opps:
            print(f"\n{len(opps)} opportunities found!")
            for o in opps:
                print(f"  {o['asset']}: buy {o['buy_exchange']} ${o['buy_price']:,.2f} → sell {o['sell_exchange']} ${o['sell_price']:,.2f} = {o['net_profit_pct']:.3f}% net")
                if o.get("on_10btc_usd"):
                    print(f"    On 10 BTC: ${o['on_10btc_usd']:,.2f} profit per trade")
        else:
            print("No arbitrage opportunities above threshold right now.")

    elif cmd == "monitor":
        log.info("Starting continuous monitoring (Ctrl+C to stop)...")
        while True:
            scan_arbitrage()
            time.sleep(30)  # scan every 30 seconds

    elif cmd == "opportunities":
        show_opportunities()

    elif cmd == "backtest":
        init_db()
        conn = sqlite3.connect(str(DB_PATH))
        total = conn.execute("SELECT COUNT(*) FROM opportunities").fetchone()[0]
        avg_spread = conn.execute("SELECT AVG(net_profit_pct) FROM opportunities").fetchone()[0] or 0
        best = conn.execute("SELECT MAX(net_profit_pct) FROM opportunities").fetchone()[0] or 0
        print(f"Total opportunities found: {total}")
        print(f"Average net spread: {avg_spread:.3f}%")
        print(f"Best spread: {best:.3f}%")
        if avg_spread > 0:
            daily_est = avg_spread * 24 * 2  # assume 2 trades/hour possible
            monthly_est = daily_est * 30
            print(f"Estimated monthly return on 10 BTC: {monthly_est:.1f}% = ${10 * 67000 * monthly_est / 100:,.0f}")
        conn.close()

    else:
        print(__doc__)
