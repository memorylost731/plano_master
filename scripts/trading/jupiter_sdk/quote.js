const { createJupiterApiClient } = require("@jup-ag/api");

const TOKENS = {
  SOL:  "So11111111111111111111111111111111111111112",
  USDC: "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
  USDT: "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
  RAY:  "4k3Dyjzvzp8eMZWUXbBCjEvwSkkk59S5iCNLY3QrkX6R",
  BONK: "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
  WIF:  "EKpQGSJtjMFqKZ9KQanSqYXRcF8fBopzLHYxdM65zcjm",
  JTO:  "jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
  ORCA: "orcaEKTdK7LKz57vaAYr9QeNsVEPfiu6QeMU1kektZE",
};

async function main() {
  const cmd = process.argv[2] || "quote";
  const jupiterApi = createJupiterApiClient();

  if (cmd === "quote") {
    const inputToken = (process.argv[3] || "SOL").toUpperCase();
    const outputToken = (process.argv[4] || "USDC").toUpperCase();
    const amount = parseFloat(process.argv[5] || "0.1");

    const inputMint = TOKENS[inputToken];
    const outputMint = TOKENS[outputToken];
    if (!inputMint || !outputMint) {
      console.log("Unknown token. Available:", Object.keys(TOKENS).join(", "));
      return;
    }

    const decimals = inputToken === "SOL" ? 9 : 6;
    const lamports = Math.floor(amount * Math.pow(10, decimals));

    try {
      const quote = await jupiterApi.quoteGet({
        inputMint, outputMint,
        amount: lamports,
        slippageBps: 50,
      });

      const outDecimals = outputToken === "SOL" ? 9 : 6;
      const outAmount = parseInt(quote.outAmount) / Math.pow(10, outDecimals);
      const impact = quote.priceImpactPct || "0";

      console.log(JSON.stringify({
        input: `${amount} ${inputToken}`,
        output: `${outAmount.toFixed(6)} ${outputToken}`,
        priceImpact: `${impact}%`,
        routes: quote.routePlan ? quote.routePlan.length : 0,
        routeLabels: quote.routePlan ? quote.routePlan.map(r => r.swapInfo?.label || "?").join(" → ") : "",
      }));
    } catch (e) {
      console.error("Quote error:", e.message || e);
    }
  }

  else if (cmd === "scan") {
    // Triangular arb scan: USDC → X → SOL → USDC
    const results = [];
    for (const [name, mint] of Object.entries(TOKENS)) {
      if (["USDC", "SOL", "USDT"].includes(name)) continue;
      try {
        // USDC → token
        const q1 = await jupiterApi.quoteGet({
          inputMint: TOKENS.USDC, outputMint: mint,
          amount: 10_000_000, slippageBps: 100,
        });
        const out1 = parseInt(q1.outAmount);

        // token → SOL
        const q2 = await jupiterApi.quoteGet({
          inputMint: mint, outputMint: TOKENS.SOL,
          amount: out1, slippageBps: 100,
        });
        const out2 = parseInt(q2.outAmount);

        // SOL → USDC
        const q3 = await jupiterApi.quoteGet({
          inputMint: TOKENS.SOL, outputMint: TOKENS.USDC,
          amount: out2, slippageBps: 100,
        });
        const out3 = parseInt(q3.outAmount);

        const pnl = ((out3 - 10_000_000) / 10_000_000 * 100).toFixed(3);
        const flag = parseFloat(pnl) > 0 ? " ★" : "";
        console.log(`USDC→${name}→SOL→USDC: ${pnl}%${flag}`);

        if (parseFloat(pnl) > 0) {
          results.push({ path: `USDC→${name}→SOL→USDC`, pnl: parseFloat(pnl) });
        }

        await new Promise(r => setTimeout(r, 500)); // rate limit
      } catch (e) {
        // skip
      }
    }

    if (results.length > 0) {
      console.log(`\n${results.length} PROFITABLE OPPORTUNITIES:`);
      results.sort((a, b) => b.pnl - a.pnl);
      results.forEach(r => console.log(`  ${r.path}: +${r.pnl}%`));
    } else {
      console.log("\nNo profitable triangular arb found right now.");
    }
  }
}

main().catch(console.error);
