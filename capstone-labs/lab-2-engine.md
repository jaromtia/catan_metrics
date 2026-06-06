# Lab 2 — Game Engine

> **Goal:** Implement the pure functions that enforce Catan rules: `validate`, `reduce`, and the award calculations.
>
> **Branch:** `git checkout -b lab-2-game-engine`

This is the largest and most important lab. The engine is the heart of the application — every other layer is plumbing around it. Take it one command at a time and lean hard on tests.

---

## Background

### Functional core, imperative shell

The engine is a **pure functional core**: functions that take data and return data, with no side effects.

```
validate(state, command) → Result
reduce(state, event)      → GameState
```

No database access. No HTTP. No randomness. This makes the engine trivially testable — call it with data you constructed and inspect the output. The "imperative shell" (database, HTTP, CLI) comes in later labs and wraps this core.

### Commands vs. events, revisited

`validate` takes a **command** (intent) and either rejects it or returns the **events** (facts) it produces. `reduce` takes a single event and applies it to state. The flow is always: validate → get events → reduce each event → new state. Events are what gets stored; state is always reconstructable by replaying events.

---

## Specification

All work lives in `catan/engine/`.

### `catan/engine/validate.py`

Define a `Result` dataclass with: `ok: bool`, `events: list[Event]` (default empty), `errors: list[str]` (default empty). Provide two constructors:

```python
@classmethod
def success(cls, events: list[Event]) -> "Result": ...
@classmethod
def failure(cls, *errors: str) -> "Result": ...
```

Implement the dispatcher and `execute`:

```python
def validate(state: GameState, command: Command, *, strict: bool = True) -> Result:
    """Check whether `command` is legal given `state`. Returns Result.success(events)
    or Result.failure(reason). Dispatch on the command type (use match/case) to a
    per-command validator helper."""

def execute(state: GameState, command: Command, *, strict: bool = True
           ) -> tuple[GameState, list[Event]]:
    """Validate, then reduce each resulting event. Raise ValueError (joining the
    error strings) if invalid. Return (new_state, events)."""
```

**Strict vs. dev mode.** Every validator takes the `strict` flag:
- `strict=True` — enforce *all* Catan rules (turn order, resource costs, sequence, sufficiency).
- `strict=False` (dev mode) — enforce only *structural* rules (vertex/edge exists, dice in 1–6). Admin commands (`SetResources`, `SetVictoryPoints`) are allowed only when `strict=False`.

You must write one validator per command type. Each returns a `Result`. A validator's job: reject illegal intent with a clear message, or return the list of events that the intent produces.

### `catan/engine/reduce.py`

```python
def reduce(state: GameState, event: Event) -> GameState:
    """Apply a single event, returning a NEW state. Must never mutate the input and
    never raise (validation already happened). Clone, mutate the clone, return it.
    After applying, detect whether the acting player has now won."""

def apply_all(events: list[Event]) -> GameState:
    """Replay a full event list from the GameCreated event into a final state.
    Used by persistence replay and the CLI `replay` command."""
```

Internally you will want a private `_apply(state, event)` that mutates a *fresh clone* via `match`/`case`, one case per event type, plus a `_check_win` helper.

### `catan/engine/awards.py`

```python
def update_largest_army(state: GameState, player: str) -> str | None:
    """Return the new Largest Army holder (or the current holder if unchanged)."""

def longest_road_length(state: GameState, pid: str) -> int:
    """Return the length of the longest continuous road for `pid`."""
```

---

## Your Tasks

1. **`Result` + dispatcher.** Implement `Result`, then `validate` dispatching by command type, then `execute`.
2. **Setup-phase validators.** Implement `PlaceSetupSettlement` and `PlaceSetupRoad`. Setup follows a **snake draft**: order `1→2→3` then reversed `3→2→1`, each player placing one settlement then one adjacent road. You must compute, from current placements, *whose* turn it is and *which* action (settlement or road) is expected next, and reject anything else in strict mode.
3. **Build validators.** Implement `BuildRoad`, `BuildSettlement`, `BuildCity`. Enforce: the target exists; not already occupied; the settlement **distance rule** (no building on an adjacent vertex); in strict play, it is the player's turn, they have a road connection, and they can afford the cost. Produce the build event plus a resource-spend effect where appropriate.
4. **Turn flow.** Implement `RollDice` and `EndTurn`. (See the roll rules below.)
5. **Robber & discards.** Implement `MoveRobber` and `Discard`.
6. **Dev cards.** Implement `BuyDevCard`, `PlayKnight`, `PlayRoadBuilding`, `PlayYearOfPlenty`, `PlayMonopoly`. Enforce one dev card per turn and that a card bought this turn cannot be played this turn.
7. **Trades.** Implement `TradeWithBank` (respect port ratios) and `TradeWithPlayer`.
8. **Admin commands.** Implement `SetResources`/`SetVictoryPoints`, allowed only in dev mode.
9. **The reducer.** Implement `reduce`, `_apply` (one case per event), production granting, and win detection. Implement `apply_all`.
10. **Awards.** Implement `update_largest_army` and `longest_road_length`.

### The `RollDice` rules (you implement the validator)

A roll is valid when: the player exists; (strict) it is their turn; (strict) they have not already rolled this turn; (strict) there are no pending discards; each die is 1–6; and `total == d1 + d2`.

What events does a successful roll produce?
- Always `DiceRolled(pid, d1, d2)`.
- If `total == 7` and any player holds more than the discard threshold: a `DiscardRequired` event per such player.
- If `total != 7`: **do not** emit separate production events. Production is *derived in the reducer* from `DiceRolled`.

### Production (in the reducer)

When a non-7 `DiceRolled` is reduced, every player with a settlement or city adjacent to a hex whose number matches the roll collects resources (city = double), **unless** the robber sits on that hex. You must also implement the **bank shortage rule**: if total demand for a resource exceeds the bank supply and more than one player wants it, *nobody* gets that resource; if exactly one player wants it, they get `min(demand, available)`.

---

## Hints & Pitfalls

- **`reduce` purity.** Always clone first, mutate the clone, return it. A simple test (`id(state) != id(reduce(state, e))` and the original is unchanged) catches accidental mutation.
- **Resource conservation.** After any reduce, `sum(all players' resources) + bank == BANK_RESOURCE_COUNT` for every resource. Write a helper that asserts this and call it in many tests.
- **Longest Road is a *trail*, not a path.** Each *edge* may be used once; vertices may repeat (so cycles count every edge once). This means a backtracking **DFS over edges** — start a DFS from every vertex of the player's road network and take the maximum. A plain BFS or longest-*path* algorithm gives wrong answers.
- **Opponent buildings split roads.** When traversing, an opponent's settlement/city sitting on a vertex blocks passage *through* that vertex.
- **Largest Army transfer.** First to the minimum (3) claims it; a challenger must play *strictly more* knights to take it; ties keep the current holder.
- **Setup production.** Only the *second* settlement each player places triggers immediate resource collection.

---

## Tests First

- A valid setup settlement succeeds; one that violates the distance rule fails with a "distance" error.
- Rolling twice in one turn fails (strict); rolling out of turn fails (strict) but succeeds (dev).
- Dice values outside 1–6 are rejected.
- Admin commands are rejected in strict mode, accepted in dev mode.
- `reduce` does not mutate its input.
- Resource totals are conserved across: a roll that produces, a build that spends, a bank trade, and a discard.
- Longest Road: single road = 1; two connected = 2; a loop counts each edge once; an opponent settlement mid-chain splits it into two shorter trails.

---

## Checkpoint

- [ ] `validate` returns a failure `Result` for each illegal move you test
- [ ] `reduce` never mutates input
- [ ] `strict=False` skips turn-order and resource checks but keeps structural checks
- [ ] Resource conservation holds across 10+ simulated turns
- [ ] Longest Road DFS handles cycles and opponent-building splits
- [ ] At least 20 unit tests covering validation rules
- [ ] Commit: `"Lab 2: Game engine with validate and reduce"`
