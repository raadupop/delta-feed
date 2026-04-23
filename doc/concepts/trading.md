# Trading Concepts Reference

Concepts used in INVEX position construction and decision logic, explained from first principles.

**Update log.**
- 2026-04-23 — initial file (§1: Long Straddle).

---

## 1. Long Straddle

Buying both a call and a put on the same underlying, same strike, same expiry.

**What you own.** Two options:
- A **call** — right to buy the underlying at the strike price. Profits if the underlying rises above strike.
- A **put** — right to sell the underlying at the strike price. Profits if the underlying falls below strike.

You hold both simultaneously. You paid a premium for each.

**Why you'd do this.** You believe the underlying is about to move significantly — but you don't know which direction. The call captures an upward move; the put captures a downward move. You profit if the move is large enough in *either* direction to recover the total premium paid.

**Payoff at expiry.** Let `S` = price of the underlying at expiry, `K` = strike, `C` = call premium, `P` = put premium, `Total cost = C + P`:

```
Payoff from call  = max(S − K, 0)
Payoff from put   = max(K − S, 0)
Total payoff      = max(S − K, 0) + max(K − S, 0)
                  = |S − K|

Net P&L           = |S − K| − (C + P)
```

You make money if the underlying moves more than `C + P` away from the strike in either direction.

**Breakeven points.** Two of them, symmetric around the strike:

```
Upper breakeven = K + (C + P)
Lower breakeven = K − (C + P)
```

If the underlying stays between the two breakevens at expiry, the trade loses money. If it breaks out of either side, the trade profits.

**Example.** VIX options, strike = 25, call premium = 3.0, put premium = 2.5. Total cost = 5.5.

```
Upper breakeven = 25 + 5.5 = 30.5
Lower breakeven = 25 − 5.5 = 19.5
```

If VIX expires at 35: call pays 10, put pays 0, net P&L = 10 − 5.5 = **+4.5**.
If VIX expires at 15: put pays 10, call pays 0, net P&L = 10 − 5.5 = **+4.5**.
If VIX expires at 25: both options expire worthless, net P&L = **−5.5** (maximum loss).

**Maximum loss.** Always the total premium paid (`C + P`). Occurs when the underlying expires exactly at the strike — both options are worthless. Known and bounded from entry.

**Maximum gain.** Theoretically unlimited on the upside (underlying can keep rising, call payoff grows without bound). On the downside, capped at `K` (underlying can only fall to zero) minus premium. In practice vol instruments don't go to zero, so both sides have large but finite upside.

**The enemy: theta (time decay).** Options lose value every day they are held, all else being equal. A straddle is long two options — it decays twice as fast as a single position. Every day the underlying doesn't move is a day that eats into your premium. Theta is the constant opponent of a long straddle.

```
Daily theta decay ≈ −(C_theta + P_theta)
```

The trade is only profitable if the move happens *faster* than theta erodes the position.

**The friend: vega (implied volatility).** If implied volatility rises after you buy the straddle, both options become worth more — even if the underlying hasn't moved yet. This is the core INVEX edge: if the system detects that market IV is underpriced relative to signal-implied IV (CLS-006 IV dislocation), buying a straddle before the IV repricing captures the vega gain regardless of direction.

```
Vega P&L ≈ (IV_new − IV_entry) × (call_vega + put_vega)
```

**When INVEX opens a long straddle.** The position constructor (POS-001) selects LONG_STRADDLE when:
- IV dislocation is positive (signal-implied IV > market observed IV) — market is underpricing risk.
- The event has directional uncertainty — the underlying could spike in either direction (geopolitical shocks, surprise economic prints, central bank pivots).
- The exploitability window is wide enough that theta decay does not consume expected vega gain before the move occurs.

**The Iran war example (Feb 27, 2026).** OVX = 64.68, ECDF severity = 0.85. Signal suggests crude-oil vol is being underpriced ahead of the weekend military strike. The direction is uncertain — crude could gap up (supply disruption, Hormuz closed) or gap down (demand destruction, recession pricing). LONG_STRADDLE on USO/OVX options captures either outcome. The risk: if the market has already priced in the strike by Friday close and OVX opens Monday unchanged or lower (geopolitical risk premium evaporates), both options expire worthless or near-worthless — the full premium is lost.

**Contrast with directional spreads (CALL_SPREAD, PUT_SPREAD).** A call spread profits only if the underlying rises past the lower strike. A put spread profits only if it falls past the upper strike. Both cost less than a straddle (you sell one option to partially fund the other), but you must have a directional view. A straddle is more expensive and profits from size of move regardless of direction. INVEX picks between them based on whether the triggering signal is directionally ambiguous or directionally biased.

**Liquidity note.** Not all option markets have the depth a straddle requires. VIX options are liquid enough. OVX options are substantially thinner — bid-ask spreads widen exactly during the high-vol events INVEX wants to trade. The theoretical edge from a 0.85 severity score shrinks or disappears if the fill is 2 points wide. POS-001 must account for available liquidity when sizing legs.
