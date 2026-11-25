"""Tiny Bot, Easy $2: Beat Buy-and-Hold on Solana.

Cross-sectional momentum rotation over the 7-asset Solana universe,
rebalanced every 6 hourly bars. Ranking by trailing 24-bar return
(compared exactly, cross-multiplied, no lookahead). Enter only when the
24-bar return beats +0.5% AND the 6-bar return is positive; exit when the
24-bar return turns negative (hysteresis). Hold at most the top 4
qualifying assets, equal weight, capped at 25% of equity each; the rest
stays in cash. Sells go out in one batch, buys in the next (a sell's
proceeds never fund a buy in the same reply).

Fully deterministic: no clock, no randomness, no network, no files,
no environment reads. Python standard library only.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# --- Parameters (chosen mid-range for robustness; the final window is unseen) ---
LOOKBACK_BARS = 24        # momentum lookback, bars (24h)
CONFIRM_BARS = 6          # short-term confirmation lookback, bars (6h)
ENTER_BPS = 50            # enter only if 24-bar return > +0.5%
REBALANCE_BARS = 6        # rebalance every 6 bars
TOP_N = 4                 # max assets held
MAX_SLIPPAGE_BPS = 500    # slippage bound on every order

# Each universe symbol's latest close as of every batch so far
# (None before its first bar), indexed by batch seq.
history = {}
# The next rebalance bar; set from hello: max(LOOKBACK_BARS, warm-up bars).
next_rebalance = LOOKBACK_BARS
# Symbols to buy on this batch, chosen on the rebalance bar before it
# (whose sells have now filled).
entering = None


def slots(state):
    """How many symbols we hold at most: TOP_N unless a cap is tighter."""
    caps = state.hello["caps"]
    return min(TOP_N, caps["max_open_positions"], caps["max_orders_per_bar"])


from functools import cmp_to_key


def _rank_cmp(a, b):
    """Compare two (symbol, now, then) by now/then, exactly, descending.
    Cross-multiplied, no floats; ties keep universe order (sort is stable)."""
    left = a[1] * b[2]
    right = b[1] * a[2]
    if left > right:
        return -1
    if left < right:
        return 1
    return 0


def target(state, seq):
    """Top ranked symbols to hold, best first. A symbol without both closes
    is not ranked. A symbol enters only when its 24-bar return beats
    +0.5% (now * 10000 > then * 10050, exact) and its 6-bar return is
    positive; a symbol already held stays while its 24-bar return is
    >= 0% (hysteresis: exit only when it turns negative)."""
    ranked = []
    for entry in state.hello["symbols"]:
        symbol = entry["symbol"]
        closes = history.get(symbol, [])
        now = closes[seq] if seq < len(closes) else None
        then = closes[seq - LOOKBACK_BARS] if 0 <= seq - LOOKBACK_BARS < len(closes) else None
        conf = closes[seq - CONFIRM_BARS] if 0 <= seq - CONFIRM_BARS < len(closes) else None
        if now is None or then is None or conf is None:
            continue
        enters = now * 10000 > then * (10000 + ENTER_BPS) and now > conf
        stays = symbol in state.positions and now >= then
        if enters or stays:
            ranked.append((symbol, now, then))
    ranked.sort(key=cmp_to_key(_rank_cmp))
    return [r[0] for r in ranked[: slots(state)]]


def buys(state, symbols):
    """Buy the target symbols we do not already hold, cash split evenly,
    each capped at 25% of equity. Kept positions are never resized."""
    caps = state.hello["caps"]
    fees = state.hello["fees"]
    room = slots(state) - len(state.positions)
    coming = [s for s in symbols if s not in state.positions and state.close(s) is not None][: max(room, 0)]
    if not coming:
        return []
    orders = []
    even = state.cash // len(coming)
    for symbol in coming:
        slice_amt = min(even, state.weight_room(symbol))
        if slice_amt <= 0 or slice_amt < int(fees["min_notional_quote_units"]):
            continue
        orders.append({
            "side": "buy",
            "symbol": symbol,
            "notional_quote_units": slice_amt,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        })
    return orders


def on_hello(state):
    global next_rebalance
    next_rebalance = max(LOOKBACK_BARS, state.warmup_bars)


def on_batch(state, batch):
    global next_rebalance, entering
    for entry in state.hello["symbols"]:
        symbol = entry["symbol"]
        closes = history.setdefault(symbol, [])
        closes.append(state.close(symbol))
    # No trading while warming up: orders on warm-up batches are rejected.
    if state.warming_up:
        return []
    # Buys queued after the previous batch's sells have now filled.
    if entering is not None:
        orders = buys(state, entering)
        entering = None
        return orders
    if batch["seq"] < next_rebalance:
        return []
    next_rebalance = batch["seq"] + REBALANCE_BARS
    want = target(state, batch["seq"])
    # Exit: a held symbol leaves the target when its 24-bar return turns
    # negative (it no longer passes the entry filter) or it drops out of
    # the top 4.
    sells = [
        {"side": "sell", "symbol": symbol, "qty": holding.qty, "max_slippage_bps": MAX_SLIPPAGE_BPS}
        for symbol, holding in state.positions.items()
        if symbol not in want
    ]
    if not sells:
        return buys(state, want)
    # A sell's proceeds land at the next open and never fund a buy of the
    # same reply: send the buys on the next batch.
    entering = want
    return sells


makefun_bars.run(on_batch, on_hello=on_hello)
