# Phase 7 — Metrics & Analytics

> **Goal:** Compute and display post-game statistics.
>
> **Branch:** `git checkout -b phase-7-metrics`

---

## 7.1 Projections Over Event Streams

A **projection** is a read-only function over the event log that computes a derived view. Unlike the reducer (which tracks live state), projections can be recomputed at any time from the full history.

**`catan/engine/projections.py`**

```python
from dataclasses import dataclass, field
from catan.domain.constants import Resource, DevCard, PIPS

@dataclass
class PlayerMetrics:
    pid: str
    # Dice / production
    dice_roll_counts:    dict[int, int]    = field(default_factory=dict)
    actual_production:   dict[Resource, int] = field(default_factory=dict)
    expected_production: float             = 0.0   # sum over all rolls
    luck:                float             = 0.0   # actual - expected

    # Robber
    steals_made:         int = 0    # times this player stole
    cards_stolen_from_me: int = 0   # times stolen from
    robber_blocked:      int = 0    # resource cards blocked by robber
    knights_played:      int = 0

    # Trades
    trades_maritime:     int = 0
    trades_domestic:     int = 0
    trade_net:           dict[Resource, int] = field(default_factory=dict)

    # Dev cards
    dev_bought:  dict[DevCard, int] = field(default_factory=dict)
    dev_played:  dict[DevCard, int] = field(default_factory=dict)
    cards_discarded: int = 0

    # Timelines (for charts)
    build_timeline:  list[tuple[int, int, str]]   = field(default_factory=list)
    # (seq, turn_number, "road"|"settlement"|"city")
    vp_timeline:     list[tuple[int, int, int]]   = field(default_factory=list)
    # (seq, true_vp, public_vp)


@dataclass
class GameMetrics:
    players:       dict[str, PlayerMetrics]
    dice_histogram: dict[int, int]   # {total: count}
    num_turns:     int
    winner:        str | None

    def to_dict(self) -> dict:
        """Serialize to plain dicts (for API response)."""
        ...
```

---

## 7.2 Pip Equity

**Pip equity** is the total number of dice-distribution "pips" on hexes adjacent to a player's buildings. It measures how well-positioned a player is:

```python
def pip_equity(state: GameState, pid: str) -> int:
    """
    Sum of PIPS[number] for all hexes adjacent to the player's settlements
    and cities (cities count double).
    """
    p = state.players[pid]
    topology = state.board.topology
    total = 0
    for vid in p.settlements:
        for coord in topology.vertex_hexes[vid]:
            n = state.board.numbers.get(coord)
            if n:
                total += PIPS[n]
    for vid in p.cities:
        for coord in topology.vertex_hexes[vid]:
            n = state.board.numbers.get(coord)
            if n:
                total += PIPS[n] * 2   # cities produce double
    return total
```

---

## 7.3 Expected Production

On every non-7 dice roll, add `pip_equity(pre_roll_state, pid) / 36` to each player's `expected_production`. This accumulates the *statistical expectation* of resources over the entire game.

```python
# Pseudocode — called for each DiceRolled event
prev_state = state_before_this_event   # use pre-roll state so new buildings don't
                                        # retroactively affect earlier expectations
for pid in state.player_order:
    expected_delta = pip_equity(prev_state, pid) / 36.0
    metrics[pid].expected_production += expected_delta
```

---

## 7.4 Luck Score

```python
# After accumulating all events:
for pm in metrics.players.values():
    actual   = sum(pm.actual_production.values())
    pm.luck  = actual - pm.expected_production
    # Positive = luckier than expected (more resources than statistical average)
    # Negative = unluckier than expected
```

---

## 7.5 Computing Metrics

```python
def compute_metrics(events: list[Event]) -> GameMetrics:
    """
    Replay the full event log, recording metrics at each step.
    """
    from catan.engine.reduce import reduce

    # Initialize state from the GameCreated event.
    state   = _initial_state_from_events(events)
    metrics = {pid: PlayerMetrics(pid) for pid in state.player_order}
    dice_histogram: dict[int, int] = {}
    num_turns  = 0
    winner     = None
    prev_state = state

    for seq, event in enumerate(events):
        _record(metrics, dice_histogram, state, prev_state, event, seq)
        prev_state = state
        state = reduce(state, event)
        _snapshot(metrics, state, seq)

    for pm in metrics.values():
        pm.luck = sum(pm.actual_production.values()) - pm.expected_production

    return GameMetrics(
        players=metrics,
        dice_histogram=dice_histogram,
        num_turns=num_turns,
        winner=state.winner,
    )
```

---

## 7.6 API Endpoint

```python
@app.get("/api/games/{game_id}/metrics")
def get_metrics(game_id: str):
    try:
        events = service.load_events(game_id)
    except UnknownGame:
        raise HTTPException(404, "Game not found")
    metrics = compute_metrics(events)
    return metrics.to_dict()
```

---

## 7.7 Dice Histogram (SVG Chart)

Build a simple bar chart in React with no external library:

**`web/src/components/Metrics.tsx`** (excerpt)

```tsx
function DiceHistogram({ histogram }: { histogram: Record<number, number> }) {
  const rolls = [2,3,4,5,6,7,8,9,10,11,12]
  const max   = Math.max(1, ...Object.values(histogram))

  return (
    <svg width={420} height={200}>
      {rolls.map((n, i) => {
        const count     = histogram[n] ?? 0
        const barHeight = (count / max) * 150
        const x         = i * 36 + 10
        const y         = 160 - barHeight
        const isRed     = n === 6 || n === 8
        return (
          <g key={n}>
            <rect x={x} y={y} width={28} height={barHeight}
                  fill={isRed ? "#e55" : "#5a8"}/>
            <text x={x+14} y={178} textAnchor="middle" fontSize={12}>{n}</text>
            {count > 0 && (
              <text x={x+14} y={y-4} textAnchor="middle" fontSize={11}>{count}</text>
            )}
          </g>
        )
      })}
    </svg>
  )
}
```

---

## 7.8 Metrics the Frontend Should Show

For each player:
- Total resources produced vs. expected
- Luck score (±N cards)
- Pip equity at end of game
- Build timeline: when they placed each road/settlement/city
- VP timeline: public and true VP over time
- Trade counts (maritime / domestic)
- Robber steals given/received

For the game overall:
- Dice histogram (observed vs. expected distribution)
- Total turns
- Winner

---

## Phase 7 Checkpoint

- [ ] After a complete game, `GET /api/games/{id}/metrics` returns valid JSON
- [ ] Dice histogram counts match what was actually rolled
- [ ] Luck score: player on 6/8 with many settlements shows positive luck if dice were kind
- [ ] VP timeline has entries from setup through the winning turn
- [ ] Frontend `Metrics` component renders dice histogram and per-player stats
- [ ] Commit: `"Phase 7: Game metrics and analytics projections"`
