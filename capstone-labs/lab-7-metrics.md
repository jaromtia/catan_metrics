# Lab 7 — Metrics & Analytics

> **Goal:** Compute post-game statistics from the event stream and display them in the UI.
>
> **Branch:** `git checkout -b lab-7-metrics`

---

## Background

A **projection** is a read-only function over the event log that computes a derived view. Unlike the reducer (which maintains live state), a projection can be recomputed at any time from the full history. Metrics are projections: replay the events, accumulate statistics, and produce a report.

The flagship metric is the **luck score** — how much a player's *actual* resource production diverged from what probability says they *should* have produced, given the pip values of the hexes their buildings touch.

---

## Specification

### `catan/engine/projections.py`

Define two dataclasses:

`PlayerMetrics` (per player), carrying at least:
- Dice/production: `dice_roll_counts: dict[int,int]`, `actual_production: dict[Resource,int]`, `expected_production: float`, `luck: float`.
- Robber: `steals_made`, `cards_stolen_from_me`, `robber_blocked`, `knights_played`.
- Trades: `trades_maritime`, `trades_domestic`, `trade_net: dict[Resource,int]`.
- Dev cards: `dev_bought: dict[DevCard,int]`, `dev_played: dict[DevCard,int]`, `cards_discarded`.
- Timelines for charts: `build_timeline: list[tuple[int,int,str]]` (seq, turn, structure) and `vp_timeline: list[tuple[int,int,int]]` (seq, true_vp, public_vp).

`GameMetrics` (whole game), carrying `players: dict[str, PlayerMetrics]`, `dice_histogram: dict[int,int]`, `num_turns: int`, `winner: str | None`, and a `to_dict()` that serializes everything to plain JSON-safe dicts for the API.

Implement:

```python
def pip_equity(state: GameState, pid: str) -> int:
    """Sum of PIPS[number] over every hex adjacent to the player's settlements
    (×1) and cities (×2). Measures how well-positioned a player is."""

def compute_metrics(events: list[Event]) -> GameMetrics:
    """Replay the full log, recording metrics at each step, and return the report."""
```

### How the three derived metrics work (you implement them)

- **Pip equity** — the positional measure above.
- **Expected production** — on each *non-7* roll, add `pip_equity(pre_roll_state, pid) / 36` to that player's `expected_production`. Use the state *before* the roll so later buildings don't retroactively inflate earlier expectations.
- **Luck** — after replaying everything, `luck = sum(actual_production) - expected_production`. Positive = luckier than the statistical average; negative = unluckier.

### API endpoint

`GET /api/games/{id}/metrics` (added in Lab 5's app): load the events, call `compute_metrics`, return `to_dict()`. 404 on unknown game.

### Frontend (`web/src/components/Metrics.tsx`)

A metrics view that renders, with no charting library:
- A **dice histogram** as an SVG bar chart over totals 2–12 (highlight 6 and 8).
- Per-player: actual vs. expected production, luck score, end-game pip equity, build timeline, VP timeline, trade counts, robber steals given/received.
- Game-level: total turns and winner.

---

## Your Tasks

1. Implement `PlayerMetrics` and `GameMetrics` (with `to_dict`).
2. Implement `pip_equity`.
3. Implement `compute_metrics`: replay events, recording per-event metrics (dice counts, production, steals, trades, dev cards, discards) and per-step snapshots (timelines), then finalize luck.
4. Wire the metrics endpoint in the API and the `getMetrics` client call (if not already).
5. Build the `Metrics.tsx` component: the SVG dice histogram and the per-player panels.

---

## Hints & Pitfalls

- Drive `compute_metrics` off your reducer: hold a `state`, a `prev_state`, and `reduce` forward one event at a time so each metric step can see both the before and after.
- Production attribution: a `DiceRolled` event implies production, but the robber blocks one hex — mirror exactly what your reducer does so `actual_production` matches reality.
- Expected production must use the *pre-roll* state; getting this wrong makes luck scores drift.
- `to_dict` must convert enum keys to strings and tuples to lists, just like the codec.

---

## Tests First

- After a scripted game, `compute_metrics` returns a histogram whose counts equal the number of each `DiceRolled` total.
- A player sitting on 6/8 hexes who rolled those numbers often shows a positive luck score.
- VP timeline has entries spanning setup through the winning turn.
- `to_dict()` output is JSON-serializable (`json.dumps` succeeds).

---

## Checkpoint

- [ ] `GET /api/games/{id}/metrics` returns valid JSON after a complete game
- [ ] Dice histogram counts match the actual rolls
- [ ] Luck score reflects favorable/unfavorable dice given board position
- [ ] VP timeline spans setup → win
- [ ] `Metrics` component renders the histogram and per-player stats
- [ ] Commit: `"Lab 7: Game metrics and analytics projections"`
