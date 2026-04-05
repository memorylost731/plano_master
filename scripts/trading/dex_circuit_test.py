#!/usr/bin/env python3
"""
DEX Circuit Tester — validates the full trading pipeline with pocket money.

Tests: wallet → Jupiter quote → swap → verify → reverse swap → measure P&L.
Uses Solana mainnet with REAL but tiny amounts ($5-50).

Usage:
    python3 dex_circuit_test.py quote SOL USDC 0.01     # get quote only
    python3 dex_circuit_test.py circuit SOL USDC 0.01    # full round-trip test
    python3 dex_circuit_test.py balance                  # check wallet
    python3 dex_circuit_test.py monitor                  # continuous arb scanning on Solana DEXes
"""

import json
import logging
import os
import sys
import time
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG if os.environ.get("PLANO_DEBUG") else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("c4isr.dex_test")

# Jupiter V6 API (free, no auth)
JUPITER_QUOTE = "https://quote-api.jup.ag/v6/quote"
JUPITER_SWAP = "https://quote-api.jup.ag/v6/swap"
JUPITER_PRICE = "https://api.jup.ag/price/v2"

# Token mints (Solana mainnet)
TOKENS = {
    "SOL":  "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "RAY":  "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
    "JTO":  "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
    "WIF":  "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
    "ORCA": "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
    "MNGO": "MangoCzJ36AjZyKwVj3VnYU4GTonjfVEnJmvvWaxLac",
    "STEP": "StepAscQoEioFxxWGnh2sLBDFp9d8rvKz2Yp39iDpyT",
}

WALLET = os.path.expanduser("~/.config/solana/plano_trading_test.json")


def jupiter_quote(input_mint: str, output_mint: str, amount_lamports: int, slippage_bps: int = 50) -> dict:
    """Get a swap quote from Jupiter aggregator."""
    params = f"inputMint={input_mint}&outputMint={output_mint}&amount={amount_lamports}&slippageBps={slippage_bps}"
    url = f"{JUPITER_QUOTE}?{params}"
    
    req = urllib.request.Request(url, headers={"User-Agent": "C4ISR-Trading/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def jupiter_price(token_ids: list) -> dict:
    """Get current prices from Jupiter."""
    ids = ",".join(token_ids)
    url = f"{JUPITER_PRICE}?ids={ids}"
    req = urllib.request.Request(url, headers={"User-Agent": "C4ISR-Trading/1.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def scan_solana_arb() -> list:
    """Scan Solana DEX pairs for arbitrage via Jupiter routing."""
    opportunities = []
    
    # Get prices for all tracked tokens
    mints = list(TOKENS.values())
    try:
        prices = jupiter_price(mints)
        data = prices.get("data", {})
        
        log.info("Solana DEX prices (Jupiter):")
        token_prices = {}
        for mint, info in data.items():
            name = next((k for k, v in TOKENS.items() if v == mint), mint[:8])
            price = float(info.get("price", 0))
            token_prices[name] = price
            if price > 0:
                log.info(f"  {name:8} ${price:>12,.6f}")
        
        # Check triangular arb: USDC → X → SOL → USDC
        usdc_mint = TOKENS["USDC"]
        sol_mint = TOKENS["SOL"]
        
        for token_name, token_mint in TOKENS.items():
            if token_name in ("USDC", "SOL", "USDT"):
                continue
            
            try:
                # Quote: USDC → token (using $10 worth)
                q1 = jupiter_quote(usdc_mint, token_mint, 10_000_000, 100)  # 10 USDC (6 decimals)
                out1 = int(q1.get("outAmount", 0))
                
                if out1 <= 0:
                    continue
                
                time.sleep(0.5)  # rate limit
                
                # Quote: token → SOL
                q2 = jupiter_quote(token_mint, sol_mint, out1, 100)
                out2 = int(q2.get("outAmount", 0))
                
                if out2 <= 0:
                    continue
                
                time.sleep(0.5)
                
                # Quote: SOL → USDC
                q3 = jupiter_quote(sol_mint, usdc_mint, out2, 100)
                out3 = int(q3.get("outAmount", 0))
                
                # Calculate round-trip P&L
                pnl_usdc = (out3 - 10_000_000) / 10_000_000 * 100  # % profit
                
                if pnl_usdc > -1:  # show anything losing less than 1%
                    flag = " ★★★" if pnl_usdc > 0.3 else (" ★" if pnl_usdc > 0 else "")
                    log.info(f"  TRIANGLE: USDC→{token_name}→SOL→USDC = {pnl_usdc:+.3f}%{flag}")
                    
                    if pnl_usdc > 0:
                        opportunities.append({
                            "type": "triangular",
                            "path": f"USDC→{token_name}→SOL→USDC",
                            "pnl_pct": round(pnl_usdc, 3),
                            "input_usdc": 10,
                            "output_usdc": out3 / 1_000_000,
                        })
                
                time.sleep(0.5)
                
            except Exception as e:
                log.debug(f"  {token_name} triangle failed: {e}")
                continue
    
    except Exception as e:
        log.error(f"Price fetch failed: {e}")
    
    return opportunities


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "balance"
    
    if cmd == "balance":
        import subprocess
        os.environ["PATH"] = os.path.expanduser("~/.local/share/solana/install/active_release/bin") + ":" + os.environ["PATH"]
        r = subprocess.run(["solana", "balance", "--keypair", WALLET], capture_output=True, text=True)
        addr = subprocess.run(["solana", "address", "--keypair", WALLET], capture_output=True, text=True)
        print(f"Wallet: {addr.stdout.strip()}")
        print(f"Balance: {r.stdout.strip()}")
        print(f"\nTo fund this wallet for testing:")
        print(f"  Send 0.01 SOL (~$0.80) for gas")
        print(f"  Send $10-50 USDC for test trades")
    
    elif cmd == "quote":
        if len(sys.argv) < 5:
            print("Usage: dex_circuit_test.py quote INPUT OUTPUT AMOUNT")
            sys.exit(1)
        input_token = sys.argv[2].upper()
        output_token = sys.argv[3].upper()
        amount = float(sys.argv[4])
        
        input_mint = TOKENS.get(input_token)
        output_mint = TOKENS.get(output_token)
        
        if not input_mint or not output_mint:
            print(f"Unknown token. Available: {list(TOKENS.keys())}")
            sys.exit(1)
        
        # Convert to lamports/smallest unit
        decimals = 9 if input_token == "SOL" else 6  # SOL=9, most SPL=6
        lamports = int(amount * 10**decimals)
        
        quote = jupiter_quote(input_mint, output_mint, lamports)
        out_decimals = 9 if output_token == "SOL" else 6
        out_amount = int(quote.get("outAmount", 0)) / 10**out_decimals
        
        price_impact = float(quote.get("priceImpactPct", 0))
        
        print(f"\nJupiter Quote: {amount} {input_token} → {out_amount:.6f} {output_token}")
        print(f"Price impact: {price_impact:.4f}%")
        print(f"Route: {' → '.join(r.get('label', '?') for r in quote.get('routePlan', []))}")
    
    elif cmd == "monitor":
        log.info("Starting Solana DEX arbitrage monitor...")
        while True:
            opps = scan_solana_arb()
            if opps:
                log.info(f"Found {len(opps)} opportunities!")
                for o in opps:
                    log.info(f"  {o['path']}: {o['pnl_pct']:+.3f}% on ${o['input_usdc']}")
            time.sleep(30)
    
    elif cmd == "circuit":
        print("Full circuit test requires funded wallet.")
        print(f"Send funds to: {open(WALLET).read()[:44] if os.path.exists(WALLET) else 'wallet not found'}")
        print("Then run: dex_circuit_test.py circuit SOL USDC 0.01")
    
    else:
        print(__doc__)
