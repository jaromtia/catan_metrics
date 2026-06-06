# Lab 8 — Testing Strategy

> **Goal:** Consolidate your tests into a suite that verifies correctness and catches regressions, reaching ≥80% coverage on the engine and store.
>
> **Branch:** `git checkout -b lab-8-tests`

If you followed the "Tests First" sections in earlier labs, much of this work is already done. This lab is about *completeness and structure*: filling gaps, organizing files, and proving coverage.

---

## Background

The testing pyramid:

```
        /\
       /E2E\         ← Few, slow, full user flows
      /------\
     /Integr. \      ← Some, multiple components together
    /----------\
   /   Unit     \    ← Many, fast, one function at a time
  /--------------\
```

For this project:
- **Unit** — `validate()`, `reduce()`, `awards.py`, `projections.py`, geometry, in isolation.
- **Integration** — `GameService` against a real in-memory SQLite database.
- **API** — the FastAPI app via `httpx` / `TestClient`.

---

## Specification

### `tests/fixtures.py`

Provide reusable builders so tests don't repeat setup. At minimum:

```python
def make_player(pid: str) -> PlayerState:
    """A fresh player: zeroed resources/dev cards, empty structures."""

def make_game_state(players=None, phase=Phase.SETUP, has_rolled=False,
                    current_index=0) -> GameState:
    """A minimal but fully valid GameState (standard board, full bank and
    dev deck, robber on the desert)."""
```

### Required test files

Organize your suite into these files. Each must cover the behaviors listed.

| File | Must cover |
|------|-----------|
| `test_geometry.py` | `standard_hexes` count; topology vertex/edge counts (54/72); adjacency symmetry; every hex has 6 vertices; handshake lemma |
| `test_board.py` | Board generators; terrain distribution counts; port count; no adjacent 6/8 on `random_board` |
| `test_validate.py` | Every validation rule — **both** the passing and the failing case; strict vs dev differences |
| `test_reduce.py` | Every event type; resource conservation; reducer immutability |
| `test_awards.py` | Longest Road DFS (single, chain, cycle, opponent split); Largest Army claim and tie handling |
| `test_store.py` | Codec round-trips for all events; snapshot creation; replay; time travel |
| `test_modes.py` | Strict vs dev behavior; admin commands rejected in strict, allowed in dev |
| `test_projections.py` | Dice histogram; luck score sign; VP timeline length |
| `test_cli.py` | Parser synonyms; a parse→command round trip |
| `test_api.py` | All endpoints; status codes (201/200/204/400/404/422); layout topology |

---

## Your Tasks

1. Write `tests/fixtures.py` (`make_player`, `make_game_state`, and any helpers like finding the desert coordinate).
2. Write a conservation helper (`assert_conserved(state)`) and reuse it across reducer/integration tests.
3. Fill in each required test file so its listed behaviors are covered, with at least one passing and one failing case per validation rule.
4. Run coverage and close gaps until `catan/engine/` and `catan/store/` are ≥80%.

---

## Hints & Pitfalls

- A pure engine is easy to test: construct a `GameState` with fixtures, call `validate`/`reduce`, assert on the result. No DB or HTTP needed for unit tests.
- For reducer immutability, assert both that a new object is returned **and** that the original is unchanged.
- For the API, build a `TestClient` over an app wired to an in-memory `EventStore`; create games in `dev` mode when you need to act out of turn.
- Coverage measures executed lines, not behavior. Chase missing branches, but optimize for *meaningful* assertions over raw percentage.

```bash
uv run pytest                                   # all tests
uv run pytest --cov=catan --cov-report=term-missing
uv run pytest tests/test_validate.py -v         # one file
```

---

## Checkpoint

- [ ] `uv run pytest` passes with 0 failures
- [ ] Coverage ≥ 80% across `catan/engine/` and `catan/store/`
- [ ] Every validation rule has both a passing and a failing test
- [ ] Resource conservation covered for: roll, build, bank trade, discard
- [ ] API tests cover create, fetch, valid command, invalid command, 404, 422
- [ ] `test_geometry.py` verifies vertex/edge counts and adjacency symmetry
- [ ] `test_modes.py` verifies strict/dev behavior and admin commands
- [ ] Commit: `"Lab 8: Comprehensive test suite with 80%+ coverage"`
