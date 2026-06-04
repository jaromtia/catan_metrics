# Grading Rubric

| Category | Points | Criteria |
|----------|--------|----------|
| **Planning artifacts** | 15 | Requirements doc, architecture diagram, 3+ ADRs, task history |
| **Domain models** | 10 | Correct enums (LUMBER/WOOL/GRAIN, not WOOD/SHEEP/WHEAT), immutable dataclasses, complete types |
| **Game engine** | 20 | Validates all standard Catan rules; reducer is pure; resource conservation invariant holds |
| **Persistence** | 10 | Events survive server restart; time travel works; snapshots reduce load time |
| **CLI** | 5 | REPL plays a full game; invalid commands give helpful errors; `replay` validates conservation |
| **REST API** | 10 | Correct HTTP status codes (422 vs 400); WebSocket broadcasts; proper error responses |
| **Frontend** | 15 | Board renders correctly; clicking places buildings/roads; real-time updates; discard panel works |
| **Metrics** | 5 | Dice histogram, luck score, pip equity, VP timeline |
| **Test suite** | 10 | ≥80% coverage; tests for valid AND invalid cases; API tests; geometry tests |
| **README** | 5 | Stranger can run the app following only the README |
| **Live demo** | 10 | Working end-to-end; handles edge cases; explains design choices |
| **Penalty** | -5 | Per phase skipped or incomplete at grading time |
| **Total** | **115** | (15 extra credit points possible) |

## Extra Credit (up to 15 points)

| Feature | Points | Description |
|---------|--------|-------------|
| Custom board designer | 5 | Browser UI to enter your physical board tile-by-tile before starting |
| Dev mode sandbox | 3 | Per-game toggle bypassing rule enforcement; admin commands to set resources/VP |
| Historical replay scrubber | 4 | UI slider to time-travel through game history at any event sequence |
| Port enforcement | 3 | 2:1 port trading enforced; correct `PortType` validation in `_v_trade_bank` |

## Grading Notes

- **Domain models:** Penalty if Resource enum uses `WOOD`, `WHEAT`, or `SHEEP` instead of `LUMBER`, `GRAIN`, `WOOL`.
- **Game engine:** Longest Road must use DFS with backtracking (not BFS). Opponent settlements must split the road.
- **Persistence:** Codec must handle `None` resources (stolen from player with empty hand), frozen sets as lists, and Coord tuples.
- **API:** Rule violations return 422, not 400. Malformed JSON returns 400.
- **Test suite:** Geometry tests (vertex/edge counts, adjacency symmetry) count toward coverage. `test_modes.py` covering strict/dev behavior is required for full points.
