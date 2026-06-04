# Engine

The `catan/engine/` package is the brain: it decides what is legal, evolves the
game state, computes the two awards, and derives metrics. Every function here is
**pure** — given the same inputs it returns the same outputs and performs no
I/O.

| Module | Responsibility |
| --- | --- |
| `validate.py` | `validate(state, command) -> Result`: legality + expansion to events |
| `reduce.py` | `reduce(state, event) -> new_state`: the only place state changes |
| `awards.py` | Longest Road and Largest Army holders |
| `projections.py` | `compute_metrics(events) -> GameMetrics`: analytics |

## Validation (`validate.py`)

`validate` is the rules engine. It returns a `Result`:

```python
@dataclass
class Result:
    ok: bool
    events: list[Event] = []      # populated on success
    errors: list[str] = []        # human-readable, populated on failure
```

On success the `Result` carries the events the command expands into; on failure
it carries error strings and no events. `execute(state, command)` is a
convenience that validates then folds, raising `ValueError` if illegal.

The validator owns **all** legality:

- **Phase / turn ordering** — setup vs. play vs. finished; whose turn it is;
  whether the dice have been rolled.
- **Setup snake draft** — `setup_expectation(state)` returns what placement is
  expected next (`("settlement"|"road", player)`) following the
  `order + reversed(order)` snake. Setup roads must touch the just-placed
  settlement.
- **The distance rule** — a settlement vertex and all its neighbors must be
  empty.
- **Road connectivity** — a road must connect to your network, and an
  opponent's settlement/city **blocks** connecting *through* that vertex.
- **Costs & limits** — affordability, pieces remaining, bank stock, dev-deck
  stock.
- **The 7 sequence** — players over 7 cards discard half, then the robber must
  move before any other action; a victim with an adjacent building and cards
  must be robbed.
- **Development cards** — at most one dev card per turn, and not the card you
  bought this turn (`dev_bought_this_turn` vs. `dev_cards`).
- **Trades** — domestic trades need a non-empty bundle on both sides and
  sufficient resources; maritime trades derive the **best ratio** from the ports
  you occupy (resource port 2:1 > generic 3:1 > none 4:1) and require the
  give/receive amounts to match it.

Gating helpers keep this consistent:

- `_gate_play_action` — the common gate for build/buy/trade (your turn, rolled,
  no pending 7).
- `_gate_play_dev` — the gate for playing a dev card (allowed before rolling,
  one per turn, not the freshly bought one).

Errors **accumulate**: a single illegal command often returns several reasons at
once (e.g. "no roads left; cannot afford a road"), which is friendlier than
failing on the first.

A command can expand to multiple events — e.g. `MoveRobber` →
`[RobberMoved, ResourceStolen]` when a victim is named.

## The reducer (`reduce.py`)

`reduce(state, event) -> new_state` is the **only** place game state changes. It:

1. Clones the input state (never mutates it).
2. Dispatches on the event type via a `match` and applies its effect.
3. Applies **deterministic consequences** that are *not* stored on the event:
   - **Production** — on a non-7 roll, each producing hex matching the roll (and
     not under the robber) grants its resource to adjacent buildings
     (settlement ×1, city ×2), honoring the **bank-shortage rule**: if the bank
     can't cover everyone, a sole claimant gets what's left, but if multiple
     players would draw the scarce resource, *none* is produced.
   - **Bank movements**, monopoly transfers, year-of-plenty draws.
   - **Award recomputation** after road/settlement/knight changes.
4. **Win detection** — after applying the event, if the acting player is in the
   PLAY phase and has ≥ 10 VP (including hidden cards), they win and the phase
   becomes `FINISHED`. Only the acting player can win, and only on their turn.

`apply_all(events)` folds an entire log into a final state. `GameCreated` is the
only event that can start from `None` state.

The setup phase auto-completes (`_maybe_finish_setup`) once every player has
placed 2 settlements and 2 roads, flipping to PLAY at turn 1.

## Awards (`awards.py`)

Both awards are pure functions of `GameState`.

**Longest Road** (`longest_road_length`, `recompute_longest_road`): the genuinely
tricky one. It is the longest *trail* (no edge reused) through a player's road
network, where an opponent's settlement/city **blocks passing through** that
vertex (it may still be a trail endpoint). Computed by DFS over the player's
edges. The award:

- needs a road of length ≥ 5 (`LONGEST_ROAD_MIN`);
- the current holder keeps it until someone **strictly** surpasses them;
- a broken road can drop the holder below the minimum and vacate the card;
- a tie for a new maximum leaves an unheld card unheld.

**Largest Army** (`update_largest_army`): held by the player with the most
knights played, minimum 3. Knights only ever increase, so the holder keeps the
card until someone strictly exceeds their knight count.

## Metric projections (`projections.py`)

`compute_metrics(events)` replays the log through the reducer once and, at each
step, records both event-level detail and state snapshots. Because it is derived
purely from the log, it is reproducible and can be recomputed anytime.

**Pip equity** — `pip_equity(state, pid)` sums the probability pips on a
player's hexes (settlements ×1, cities ×2). Each pip is a 1/36 chance to draw a
card on a single two-dice roll, so a player's expected income per roll is
`pip_equity / 36`.

**Luck** — the headline metric. For every non-7 roll, the projection adds each
player's `pip_equity(prev) / 36` to their *expected* production and the resources
they actually drew to their *actual* production. `luck = actual − expected` tells
you whether the dice ran hot or cold for them.

`GameMetrics` / `PlayerMetrics` capture, per player:

- `production` per resource and `production_total`, `expected_production`, `luck`
- `cards_discarded`, `steals_made`, `cards_stolen_from_me`, `knights_played`
- `dev_bought` / `dev_played` by card, `trades_domestic` / `trades_maritime`,
  `trade_net` per resource
- timelines: `builds` (seq, turn, kind), `vp_timeline` (true & public VP),
  `hand_timeline`, `pip_timeline`

and game-wide: `dice_histogram` (2–12), `num_turns`, `winner`. `to_dict()`
produces the JSON the CLI (`metrics --json`) and API return.

## See also

- The data types these operate on: [domain-model.md](domain-model.md)
- How events are persisted and replayed: [persistence.md](persistence.md)
