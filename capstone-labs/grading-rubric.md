# Grading Rubric

| Category | Points | Criteria |
|----------|--------|----------|
| **Planning artifacts** | 15 | Requirements doc, architecture diagram, 3+ ADRs, task history |
| **Domain models** | 10 | Correct enums (LUMBER/WOOL/GRAIN, not WOOD/SHEEP/WHEAT), immutable dataclasses, complete types, correct constant values derived from the rules |
| **Game engine** | 20 | Validates all standard Catan rules; reducer is pure; resource conservation invariant holds |
| **Persistence** | 10 | Events survive server restart; time travel works; snapshots reduce load time |
| **CLI** | 5 | REPL plays a full game; invalid commands give helpful errors; `replay` validates conservation |
| **REST API** | 10 | Correct HTTP status codes (422 vs 400); WebSocket broadcasts; proper error responses |
| **Frontend** | 15 | Board renders correctly; clicking places buildings/roads; real-time updates; discard panel works |
| **Metrics** | 5 | Dice histogram, luck score, pip equity, VP timeline |
| **Test suite** | 10 | ≥80% coverage; tests for valid AND invalid cases; API tests; geometry tests |
| **README** | 5 | Stranger can run the app following only the README |
| **Live demo** | 10 | Working end-to-end; handles edge cases; explains design choices |
| **Penalty** | -5 | Per lab skipped or incomplete at grading time |
| **Total** | **115** | (15 extra credit points possible) |

## Extra Credit (up to 15 points)

| Feature | Points | Description |
|---------|--------|-------------|
| Custom board designer | 5 | Browser UI to enter your physical board tile-by-tile before starting |
| Dev mode sandbox | 3 | Per-game toggle bypassing rule enforcement; admin commands to set resources/VP |
| Historical replay scrubber | 4 | UI slider to time-travel through game history at any event sequence |
| Port enforcement | 3 | 2:1 port trading enforced; correct `PortType` validation in the bank-trade validator |

## Grading Notes

- **Domain models:** penalty if the `Resource` enum uses `WOOD`, `WHEAT`, or `SHEEP` instead of `LUMBER`, `GRAIN`, `WOOL`. Constant values (counts, pips, costs) must be correct per the rules.
- **Game engine:** Longest Road must use DFS with backtracking (not BFS). Opponent settlements must split the road.
- **Persistence:** the codec must handle `None` resources, frozensets as lists, and `Coord` tuples; `decode_board` must rebuild the topology rather than store it.
- **API:** rule violations return 422, not 400. Malformed JSON returns 400.
- **Test suite:** geometry tests (vertex/edge counts, adjacency symmetry) count toward coverage. `test_modes.py` covering strict/dev behavior is required for full points.

## Because This Is the Lab Edition

You were given specifications and acceptance criteria, not solutions. Graders will look for evidence that you *designed* the implementation: clear commit history showing test-first development, ADRs that justify your choices, and code whose structure reflects understanding rather than transcription. A working app that you can explain beats a slightly more complete app that you cannot.
