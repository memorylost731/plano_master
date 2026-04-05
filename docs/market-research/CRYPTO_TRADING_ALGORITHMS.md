

# Crypto Scalping & Arbitrage: Production System Reference

## 1. ARBITRAGE STRATEGIES

### Spatial Arbitrage (Cross-Exchange)

Buy on exchange A, sell on exchange B where price_A < price_B.

**Formula:** `profit = (price_B - price_A) - fee_A - fee_B - withdrawal_fee - slippage`

Typical spread on BTC across major CEXs: 0.01-0.05% (was 1-3% pre-2022). After fees (~0.1% maker/taker each), most spatial arb on major pairs is **negative EV** unless you pre-fund both sides (no withdrawal delay). Required latency: <100ms. Capital: $50K+ on each exchange to justify infrastructure.

**Risk:** Withdrawal delays (minutes to hours) can kill the trade. Exchange insolvency (FTX). Transfer fees eat profits.

**Open source:** Hummingbot's `cross_exchange_market_making` strategy; Blackbird (C++, archived but instructive): `github.com/butor/blackbird`.

### Triangular Arbitrage

Exploit pricing inconsistency across three pairs on one exchange: BTC→ETH→USDT→BTC.

**Formula:**
```
rate_effective = (1/ask_BTC_ETH) * bid_ETH_USDT * (1/ask_USDT_BTC)
profit = rate_effective - 1 - (3 * fee_rate)
```

With 0.1% taker fee per leg, you need >0.3% triangular discrepancy. These appear for ~50-200ms on liquid exchanges. Typical profit per cycle: 0.01-0.05%. Sharpe: 3-8 (high frequency, small per-trade). Daily return: 0.1-0.5% on capital deployed.

**Speed:** <10ms decision + execution. Requires co-located servers or exchange websocket feeds.

**Open source:** `github.com/bmino/binance-triangle-arbitrage` (Node.js, Binance-specific). `github.com/wardbradt/peregrine` (Python, multi-exchange, graph-based path detection using Bellman-Ford for negative cycles).

### Statistical Arbitrage (Pairs Trading)

Find cointegrated pairs (e.g., ETH/BTC), trade the z-score of the spread.

**Entry:** z-score > 2.0 (short the outperformer, long the underperformer). **Exit:** z-score reverts to 0. **Stop:** z-score > 3.5.

```python
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint

# Cointegration test
score, pvalue, _ = coint(series_a, series_b)
if pvalue < 0.05:
    # Fit hedge ratio
    model = sm.OLS(series_a, sm.add_constant(series_b)).fit()
    hedge_ratio = model.params[1]
    spread = series_a - hedge_ratio * series_b
    z = (spread - spread.mean()) / spread.std()
```

Win rate: 55-65%. Sharpe: 1.5-3.0. Typical holding period: hours to days. Risk: regime change breaks cointegration (the "pairs diverge permanently" scenario). Capital: $10K+.

### DEX-CEX Arbitrage

DEX prices lag CEX by 1-12 seconds (block time). Buy cheap on DEX, sell on CEX (or vice versa).

**Formula:** `profit = |price_CEX - price_DEX| - gas_fee - cex_fee - slippage_dex`

On Ethereum mainnet, gas cost of a Uniswap swap: $2-50 depending on congestion. On Solana: $0.001. This makes Solana DEX-CEX arb viable at much smaller spreads.

Typical profit: 0.1-0.5% per trade on less liquid pairs. Major pairs are heavily competed by MEV bots. Daily return: 0.2-1% with automation. **Risk:** MEV frontrunning (sandwich attacks), failed transactions still cost gas.

### DEX-DEX Arbitrage

Price differences between Uniswap, SushiSwap, Curve, Balancer for the same pair.

Most profitable on stablecoin pools (Curve vs Uniswap) and long-tail tokens. Bots monitor all pools via multicall contracts.

```solidity
// Simplified flash loan arb pattern
function executeArb(
    address tokenA, address tokenB,
    address pool1, address pool2,
    uint256 amountIn
) external {
    // Borrow from pool1
    uint256 amountOut = IPool(pool1).swap(tokenA, tokenB, amountIn);
    // Sell on pool2
    uint256 finalAmount = IPool(pool2).swap(tokenB, tokenA, amountOut);
    require(finalAmount > amountIn, "no profit");
}
```

**Open source:** `github.com/flashbots/simple-arbitrage` (reference implementation). `github.com/Jeiwan/uniswapv3-book` for understanding AMM math.

### Flash Loan Arbitrage

Borrow millions with zero capital, arb, repay in one atomic transaction. If the arb fails, the entire tx reverts (you only lose gas).

**Typical profit:** $10-500 per successful execution. Competition is extreme — you're competing with professional MEV searchers using Flashbots. Gas optimization is critical; every opcode counts.

**Platforms:** Aave (0.05% flash loan fee), dYdX (0% fee), Balancer (0% fee).

**Open source:** `github.com/Uniswap/v3-periphery` examples; `github.com/aave/flashloan-box`.

### Funding Rate Arbitrage

When perpetual futures funding rate is positive (longs pay shorts): long spot + short perp = delta-neutral, collect funding every 8h.

**Formula:** `daily_yield = funding_rate * 3` (3 payments/day on most exchanges)

Typical funding rates: 0.01-0.1% per 8h = 0.03-0.3% daily = 11-109% APR. During mania, funding can spike to 0.3%+ per 8h.

**Risk:** Funding flips negative (you pay instead of collect), liquidation on the perp leg if margin insufficient, exchange risk.

Capital: $5K+ for meaningful returns. Sharpe: 2-5 during trending markets. This is one of the most reliable strategies.

### Latency Arbitrage

Co-locate at exchange data centers, use raw websocket feeds instead of REST, FPGA for order routing. Institutional-grade: $10K-100K/month infrastructure.

Retail cannot compete here. Skip this unless you have sub-millisecond infrastructure.

---

## 2. SCALPING STRATEGIES

### Order Book Scalping

Read Level 2 depth. Look for imbalances: `bid_volume / ask_volume > 1.5` suggests upward pressure.

**Entry:** Buy when bid imbalance detected + price at support. **Exit:** 0.05-0.2% profit target. **Stop:** 0.1% below entry.

Win rate: 55-65%. Frequency: 20-100 trades/day. Daily return: 0.3-1%. Requires Level 2 data feeds and sub-second execution.

**Spoofing detection:** Large orders that appear/disappear within 100ms are likely spoofed — ignore them. Track persistent orders only.

### Momentum Scalping

Use 1-5 minute candles. Indicators: RSI(7) crossing 30/70, MACD histogram sign change, volume spike (>2x 20-period average).

**Entry:** RSI crosses above 30 + volume spike + MACD turning positive. **Exit:** RSI hits 70 or 0.3% profit. **Stop:** 0.15% trailing.

Win rate: 50-55%. Risk-reward: 1:1.5-2. Sharpe: 1.0-2.0.

### Grid Trading

Place buy orders every X% below current price, sell orders every X% above. Profits from oscillation.

```python
def create_grid(center_price: float, levels: int, spacing_pct: float) -> list[dict]:
    orders = []
    for i in range(-levels, levels + 1):
        price = center_price * (1 + i * spacing_pct / 100)
        side = "buy" if i < 0 else "sell"
        orders.append({"side": side, "price": round(price, 2)})
    return orders
```

Works in ranging markets. Gets destroyed in trends (accumulates losing side). Typical: 10-20 levels, 0.3-1% spacing. Daily return in range: 0.2-0.5%. Open source: Hummingbot's `pure_market_making`, freqtrade grid strategy plugins.

### Market Making

Provide liquidity on both sides, earn the spread. This is a serious strategy requiring inventory management.

**Core formula:** `spread = 2 * (fee + risk_premium + inventory_skew)`

Inventory skew: shift your quotes away from the side you're overexposed to. If you're long, lower your ask.

Daily return: 0.1-0.5% on deployed capital. Sharpe: 2-4. Risk: adverse selection (informed traders pick you off), inventory risk in trending markets.

**Open source:** Hummingbot is the gold standard here. Also `github.com/CryptoFacilities/REST-v2-Python` for examples.

### VWAP Scalping

Calculate rolling VWAP. Buy when price < VWAP by >0.1%, sell when price > VWAP by >0.1%.

```python
def vwap(prices: list[float], volumes: list[float]) -> float:
    return sum(p * v for p, v in zip(prices, volumes)) / sum(volumes)
```

Win rate: 52-58%. Works best on liquid pairs with mean-reverting intraday behavior.

---

## 3. CORRELATION & OSINT SIGNALS

| Signal | Lead Time | Correlation | Source |
|--------|-----------|-------------|--------|
| Exchange inflows (BTC) | 1-4 hours | -0.3 to -0.5 (bearish) | Glassnode, CryptoQuant |
| Whale transactions (>$10M) | 15-60 min | ±0.2-0.4 | Whale Alert API |
| Social sentiment (Twitter) | 0-30 min | 0.15-0.3 (noisy) | LunarCrush, Santiment |
| Funding rate extremes | 4-24 hours | -0.3 (mean-reversion) | Exchange APIs |
| Open interest spike | 1-6 hours | 0.2-0.4 (volatility predictor) | Coinalyze |
| USDT minting (>$100M) | 1-7 days | 0.3-0.5 (bullish) | Tether transparency, Etherscan |
| DXY (dollar index) | Same-day | -0.6 to -0.8 vs BTC | TradingView |
| GitHub commits | Weeks-months | Weak (0.1-0.2), better for altcoins | GitHub API |
| Stablecoin exchange reserves | 1-3 days | 0.3-0.5 (buying power signal) | DefiLlama |

**Most actionable:** Funding rate extremes (mean-reversion signal) and exchange inflows (sell pressure signal) have the strongest risk-adjusted alpha for automated systems.

---

## 4. RISK MANAGEMENT

### Kelly Criterion
```python
def kelly_fraction(win_rate: float, win_loss_ratio: float) -> float:
    """Optimal fraction of bankroll to risk per trade."""
    return win_rate - (1 - win_rate) / win_loss_ratio

# Example: 55% win rate, 1.5:1 reward:risk
f = kelly_fraction(0.55, 1.5)  # = 0.25
# Use half-Kelly (0.125) in practice for safety
```

### Slippage Model (AMM)
```python
def amm_slippage(trade_size: float, pool_liquidity: float) -> float:
    """Price impact for constant-product AMM (Uniswap v2)."""
    return trade_size / (pool_liquidity + trade_size)

# $10K trade on $1M pool = ~1% slippage
```

### Gas Optimization
- **Ethereum L1:** $5-50/swap. Only viable for >$5K trades.
- **Arbitrum/Optimism:** $0.10-0.50/swap. Viable for >$100 trades.
- **Solana:** $0.001/swap. Viable for any size. Preferred for high-frequency.
- **Base:** $0.01-0.10/swap. Good middle ground.

### MEV Protection
- Use **Flashbots Protect** RPC (`rpc.flashbots.net`) — transactions go to private mempool, no frontrunning.
- Set tight slippage tolerance (0.5% max).
- On Solana, use Jito bundles for MEV protection.

### Maximum Drawdown
Hard-stop the system at 5-10% daily drawdown. Kill switch is non-negotiable.

---

## 5. OPEN SOURCE IMPLEMENTATIONS

| Tool | Language | Status | Best For |
|------|----------|--------|----------|
| **freqtrade** | Python | Active, mature | Scalping, backtesting, live CEX trading. 50+ exchanges via ccxt. Hyperopt for parameter optimization. |
| **Hummingbot** | Python | Active | Market making, cross-exchange arb, DEX support (Uniswap, dYdX). Most complete for arb. |
| **ccxt** | Python/JS | Active, essential | Exchange abstraction. 100+ exchanges, unified API. Every bot depends on it. |
| **Jesse** | Python | Active | Backtesting + live. Clean API, good for strategy research. |
| **Gekko** | JS | **DEAD** (archived 2020) | Do not use. |
| **Superalgos** | JS | Semi-active | Visual, steep learning curve. Not production-grade. |
| **freqtrade** hyperopt | Python | Built-in | Walk-forward optimization, Sharpe/profit/drawdown objectives. |

**Solana-specific:** `github.com/jup-ag/jupiter-core` (Jupiter aggregator SDK), `github.com/ellipsis-labs/phoenix-v1` (order book DEX). For arb: `github.com/ARBProtocol/solana-arb` and various Jito-integrated MEV bots.

---

## 6. BACKTESTING

### Arbitrage Backtesting

Standard OHLCV data is insufficient — you need **tick-level order book data** (Level 2) or at minimum **trade-level data**.

**Sources:**
- Tardis.dev — historical order book snapshots, trades, liquidations (paid, best quality)
- Kaiko — institutional-grade tick data
- Binance data downloads — free trade data
- TheGraph / Dune Analytics — historical DEX swap data

### Realistic Cost Modeling
```python
def realistic_pnl(
    gross_profit: float,
    gas_cost: float,
    slippage_pct: float,
    trade_size: float,
    exchange_fee_pct: float = 0.1,
    num_legs: int = 2
) -> float:
    fees = trade_size * exchange_fee_pct / 100 * num_legs
    slippage = trade_size * slippage_pct / 100
    return gross_profit - fees - slippage - gas_cost
```

### Walk-Forward Optimization

Split data into in-sample (optimize) and out-of-sample (validate) windows. Roll forward. If out-of-sample Sharpe < 0.5, the strategy is overfit.

freqtrade's `freqtrade hyperopt --timerange` + `freqtrade backtesting` supports this natively.

### Monte Carlo
Reshuffle trade sequence 1000+ times, measure drawdown distribution. If 95th percentile max drawdown exceeds your tolerance, reduce position size.

---

## Summary: Strategy Viability Rankings

| Strategy | Retail Viable? | Typical Sharpe | Daily Return | Capital Needed |
|----------|---------------|----------------|--------------|----------------|
| Funding rate arb | Yes | 2-5 | 0.03-0.3% | $5K+ |
| Stat arb (pairs) | Yes | 1.5-3 | 0.1-0.5% | $10K+ |
| Grid trading | Yes (ranging market) | 1-2 | 0.2-0.5% | $2K+ |
| Triangular arb | Marginal | 3-8 | 0.1-0.5% | $20K+ |
| DEX-CEX arb | Yes (Solana/L2) | 2-4 | 0.2-1% | $5K+ |
| Flash loan arb | Yes (zero capital) | N/A | $10-500/day | Gas only |
| Market making | Yes (Hummingbot) | 2-4 | 0.1-0.5% | $10K+ |
| Spatial arb | No (competed away) | <1 | ~0% | $100K+ |
| Latency arb | No (institutional) | 5+ | 0.5-2% | $100K+/mo infra |

**Recommended starting stack:** freqtrade (scalping strategies) + ccxt (exchange abstraction) + Hummingbot (market making / arb) + Flashbots Protect or Jito (MEV protection). Backtest with at least 6 months of data, walk-forward validated, before going live with real capital. Start on Solana or L2 for DEX strategies due to gas economics.
