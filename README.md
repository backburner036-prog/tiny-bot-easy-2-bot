# Tiny Bot, Easy $2 — Beat Buy-and-Hold on Solana

Cross-sectional momentum rotation bot for the make.fun bounty
`u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1` (harness
`agent-fun/bars-replay/v1`, hourly bars, 7 Solana assets).

## Strategy

- **Universe:** FARTCOIN, JITOSOL, POPCAT, RAY, SOL, WETH, WIF.
- **Ranking:** trailing 24-bar return (close now vs 24 bars ago), compared
  exactly (cross-multiplied integers, no floats, no lookahead).
- **Enter:** 24-bar return > +0.5% **and** 6-bar return > 0.
- **Exit:** 24-bar return < 0% (hysteresis: a held symbol stays while its
  24-bar return is ≥ 0%, even if it no longer passes the entry filter).
- **Hold:** at most the top 4 qualifying assets, equal weight, capped at
  25% of equity each; the rest stays in cash. Zero qualifiers → 100% cash.
- **Rebalance:** every 6 bars. Sells go out in one batch, buys in the next
  (a sell's proceeds never fund a buy in the same reply).
- **Costs:** round trip is 30 bps (10 fee + 5 slippage each way), so the
  6-bar rebalance cadence and trade-only-on-target-change keep churn low.
- **Determinism:** no clock, no randomness, no network, no files, no
  environment reads. Python standard library only.

## Files

- `main.py` — the bot (entrypoint).
- `vendor/makefun_bars.py` — byte copy of the kit SDK
  (`sdk/makefun_bars.py`), not authored code.

## Local grading

```sh
KIT=~/workspace/makefun/tiny-bot-easy-2/u-gorun-gadget-tiny-bot-easy-2-beat-a48f3ce1-kit
node "$KIT/cli/makefun.mjs" grade-local --kit "$KIT" \
  --bot ~/workspace/makefun/tiny-bot-easy-2-bot --driver process --json
```

Dev window (136 bars, 28 Oct–3 Nov 2026) is a sanity check only — the
final window (27–30 Nov 2026) is unseen. Parameters: 24-bar lookback
chosen after the 12-bar design lost ~60% more on dev and the house
24-bar momentum baseline agreed; 6-bar rebalance, top 4, +0.5% entry
kept as mid-range choices, not dev-optimised.

Dev grade-local (136 bars): Net PnL −312.473.088 micro-USDC (−3,12%),
16 trades, max drawdown 3,12% — beats buy-and-hold (−869.338.396) by
+556.865.308 micro-USDC. Guardrails pass (≥8 trades, DD ≤25%).
Deterministic: grade-local runs the bot twice, action logs identical.

## Licence

MIT — see `LICENSE`.
