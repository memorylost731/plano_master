#!/usr/bin/env python3
"""
C4ISR Trading Backtester — test strategies on historical data.

Strategies: mean reversion, momentum scalping, grid trading, arb simulation.
Correlates with OSINT signals for enhanced entries.
All decisions go through Cael DAO vote before live execution.

Usage:
    python3 backtester.py run --strategy mean_reversion --pair BTCUSDT
    python3 backtester.py compare                # compare all strategies
    python3 backtester.py correlation            # OSINT signal correlation
    python3 backtester.py dao-proposal           # generate DAO vote for best strategy
"""

import json, math, os, sys
from pathlib import Path
from datetime import datetime

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "trading" / "historical"
RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "trading" / "backtest_results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)


def load_candles(pair: str, interval: str = "1h") -> list:
    f = DATA_DIR / f"{pair}_{interval}_{'30d' if interval == '1h' else '3d'}.json"
    if not f.exists():
        print(f"No data for {pair} {interval}")
        return []
    return json.loads(f.read_text())


# ═══ STRATEGY 1: Mean Reversion (Bollinger Bands) ═══
def strategy_mean_reversion(candles: list, period: int = 20, std_mult: float = 2.0) -> dict:
    """Buy when price touches lower band, sell at middle band."""
    if len(candles) < period:
        return {"error": "insufficient data"}
    
    trades = []
    position = None
    wins = 0; losses = 0; total_pnl = 0
    
    for i in range(period, len(candles)):
        window = [c["close"] for c in candles[i-period:i]]
        mean = sum(window) / len(window)
        std = math.sqrt(sum((x - mean)**2 for x in window) / len(window))
        upper = mean + std_mult * std
        lower = mean - std_mult * std
        price = candles[i]["close"]
        
        if position is None and price <= lower:
            position = {"entry": price, "time": candles[i]["time"]}
        elif position and price >= mean:
            pnl_pct = (price - position["entry"]) / position["entry"] * 100
            fee = 0.2  # 0.1% each side
            net = pnl_pct - fee
            if net > 0: wins += 1
            else: losses += 1
            total_pnl += net
            trades.append({"entry": position["entry"], "exit": price, "pnl_pct": round(net, 3)})
            position = None
    
    total = wins + losses
    return {
        "strategy": "mean_reversion",
        "trades": len(trades),
        "wins": wins, "losses": losses,
        "win_rate": round(wins / max(total, 1) * 100, 1),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_per_trade": round(total_pnl / max(len(trades), 1), 3),
        "sharpe_approx": round(total_pnl / max(math.sqrt(sum(t["pnl_pct"]**2 for t in trades) / max(len(trades),1)), 0.01), 2) if trades else 0,
    }


# ═══ STRATEGY 2: Momentum Scalping (RSI) ═══
def strategy_momentum_scalp(candles: list, rsi_period: int = 14, oversold: int = 30, overbought: int = 70) -> dict:
    """Buy on RSI oversold, sell on RSI overbought. 5min or 1h timeframe."""
    if len(candles) < rsi_period + 1:
        return {"error": "insufficient data"}
    
    # Compute RSI
    def compute_rsi(data, period):
        gains = []; losses_list = []
        for i in range(1, len(data)):
            delta = data[i]["close"] - data[i-1]["close"]
            gains.append(max(delta, 0))
            losses_list.append(max(-delta, 0))
        
        rsi_values = [None] * (period + 1)
        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses_list[:period]) / period
        
        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses_list[i]) / period
            rs = avg_gain / max(avg_loss, 0.0001)
            rsi_values.append(100 - 100 / (1 + rs))
        
        return rsi_values
    
    rsi = compute_rsi(candles, rsi_period)
    trades = []
    position = None
    wins = 0; losses = 0; total_pnl = 0
    
    for i in range(len(candles)):
        if i >= len(rsi) or rsi[i] is None:
            continue
        price = candles[i]["close"]
        
        if position is None and rsi[i] < oversold:
            position = {"entry": price, "time": candles[i]["time"]}
        elif position and rsi[i] > overbought:
            pnl_pct = (price - position["entry"]) / position["entry"] * 100
            net = pnl_pct - 0.2
            if net > 0: wins += 1
            else: losses += 1
            total_pnl += net
            trades.append({"entry": position["entry"], "exit": price, "pnl_pct": round(net, 3)})
            position = None
    
    total = wins + losses
    return {
        "strategy": "momentum_scalp_rsi",
        "trades": len(trades),
        "wins": wins, "losses": losses,
        "win_rate": round(wins / max(total, 1) * 100, 1),
        "total_pnl_pct": round(total_pnl, 2),
        "avg_pnl_per_trade": round(total_pnl / max(len(trades), 1), 3),
    }


# ═══ STRATEGY 3: Grid Trading ═══
def strategy_grid(candles: list, grid_size_pct: float = 1.0, num_grids: int = 10) -> dict:
    """Place buy/sell orders at fixed intervals. Profit from range-bound markets."""
    prices = [c["close"] for c in candles]
    mid = sum(prices) / len(prices)
    grid_step = mid * grid_size_pct / 100
    
    # Create grid levels
    grids = []
    for i in range(-num_grids // 2, num_grids // 2 + 1):
        grids.append(mid + i * grid_step)
    
    trades = []
    holdings = 0
    total_pnl = 0
    
    for i in range(1, len(candles)):
        price = candles[i]["close"]
        prev = candles[i-1]["close"]
        
        # Check if price crossed any grid level
        for level in grids:
            if prev < level <= price and holdings > 0:  # price crossed UP → sell
                pnl = (price - level + grid_step) / level * 100 - 0.2
                total_pnl += pnl
                trades.append({"type": "sell", "price": price, "pnl": round(pnl, 3)})
                holdings -= 1
            elif prev > level >= price:  # price crossed DOWN → buy
                holdings += 1
                trades.append({"type": "buy", "price": price})
    
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    losses = sum(1 for t in trades if t.get("pnl", 0) < 0)
    
    return {
        "strategy": "grid_trading",
        "trades": len(trades),
        "wins": wins, "losses": losses,
        "win_rate": round(wins / max(wins + losses, 1) * 100, 1),
        "total_pnl_pct": round(total_pnl, 2),
        "grid_size": f"{grid_size_pct}%",
        "num_grids": num_grids,
    }


# ═══ DAO VOTE PROPOSAL ═══
def generate_dao_proposal(results: dict) -> dict:
    """Generate a Cael DAO vote proposal for the best strategy."""
    best = max(results.items(), key=lambda x: x[1].get("total_pnl_pct", -999))
    return {
        "proposal_type": "TRADING_STRATEGY_ACTIVATION",
        "proposed_by": "backtester.py (automated)",
        "requires": "Cael DAO majority vote",
        "strategy": best[0],
        "backtest_results": best[1],
        "capital_requested": "10 BTC (€670,000)",
        "risk_parameters": {
            "max_position_pct": 75,  # 25% margin
            "stop_loss_pct": 2,
            "daily_loss_limit_pct": 5,
            "auto_shutdown_drawdown_pct": 10,
        },
        "human_approval_required": True,
        "note": "No live trading without Hadrien's explicit approval",
    }


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "compare"
    
    if cmd == "compare":
        pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "AAVEUSDT", "LRCUSDT"]
        all_results = {}
        
        print("=" * 75)
        print("  BACKTEST RESULTS — 30 days, 1h candles")
        print("=" * 75)
        
        for pair in pairs:
            candles = load_candles(pair, "1h")
            if not candles: continue
            
            mr = strategy_mean_reversion(candles)
            ms = strategy_momentum_scalp(candles)
            gr = strategy_grid(candles)
            
            print(f"\n  [{pair}]")
            for name, r in [("Mean Reversion", mr), ("Momentum RSI", ms), ("Grid Trading", gr)]:
                if "error" in r: continue
                flag = " ★" if r.get("total_pnl_pct", 0) > 2 else ""
                print(f"    {name:20} trades:{r['trades']:>4} win:{r['win_rate']:>5.1f}% pnl:{r['total_pnl_pct']:>+7.2f}%{flag}")
            
            all_results[pair] = {"mean_reversion": mr, "momentum": ms, "grid": gr}
        
        # Save results
        with open(RESULTS_DIR / "comparison.json", "w") as f:
            json.dump(all_results, f, indent=2)
        
        # Best overall
        print(f"\n{'='*75}")
        best_pair = None; best_strat = None; best_pnl = -999
        for pair, strats in all_results.items():
            for sname, r in strats.items():
                pnl = r.get("total_pnl_pct", -999)
                if pnl > best_pnl:
                    best_pnl = pnl; best_pair = pair; best_strat = sname
        print(f"  BEST: {best_pair} {best_strat} at {best_pnl:+.2f}%")
        print(f"  On 10 BTC (€670K): €{670000 * best_pnl / 100:,.0f} in 30 days")
        
        # DAO proposal
        proposal = generate_dao_proposal({f"{best_pair}_{best_strat}": all_results[best_pair][best_strat]})
        print(f"\n  DAO VOTE REQUIRED: Activate {best_strat} on {best_pair}")
        print(f"  Cael DAO must approve before any live trading.")
    
    elif cmd == "dao-proposal":
        # Load latest comparison
        comp = json.loads((RESULTS_DIR / "comparison.json").read_text())
        best_pair = None; best_strat = None; best_pnl = -999
        for pair, strats in comp.items():
            for sname, r in strats.items():
                pnl = r.get("total_pnl_pct", -999)
                if pnl > best_pnl:
                    best_pnl = pnl; best_pair = pair; best_strat = sname
        
        proposal = generate_dao_proposal({f"{best_pair}_{best_strat}": comp[best_pair][best_strat]})
        print(json.dumps(proposal, indent=2))
    
    elif cmd == "correlation":
        print("OSINT correlation analysis — connecting market data to signals")
        print("(Requires: on-chain data, social sentiment, macro feeds)")
        print("Build in next iteration — wire to C4ISR OSINT pipelines")
    
    else:
        print(__doc__)
