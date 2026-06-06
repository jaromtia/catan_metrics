# Catan Companion App — Lab Edition
## CS 499 — Senior Capstone in Software Engineering

A real-time digital companion for tracking physical Settlers of Catan games. Players sit at a real board and log every move; the app enforces rules, maintains a full event history, and computes post-game analytics.

> **This is the LAB edition.** Unlike the guided capstone, these labs do **not** give you the solution code. Each lab tells you *what* to build — the data, the behavior, the interfaces, and the acceptance criteria — and leaves *how* to build it up to you. This is how professional engineering tickets and university CS labs actually work: you are handed a specification and a set of tests, and you make them pass.

---

## How These Labs Work

Each lab is structured the same way:

1. **Background** — the concepts you need to understand before you write code.
2. **Specification** — the data, types, and behavior your code must implement. This is the *contract*: the required module layout, the function and class **signatures**, and the fields your data structures must carry. Downstream labs depend on these names, so match them exactly.
3. **Your Tasks** — a numbered checklist of the units you must implement. Each is small enough to finish in one sitting.
4. **Hints & Pitfalls** — guidance on the hard parts, without the answer.
5. **Tests First** — the behaviors you must cover with tests *before* you implement them.
6. **Checkpoint** — the acceptance criteria. You are done with a lab when every box is checked.

**What you are given:** interfaces, type contracts, required behavior, edge cases, and acceptance tests.

**What you must figure out yourself:** every algorithm, every function body, every reducer case, every component's internals.

---

## Required Working Method

You are expected to follow a test-first, atomic workflow:

1. Read the lab's **Specification** and **Tests First** sections.
2. Write the failing tests that encode the contract.
3. Implement the smallest piece that could make a test pass.
4. Run the tests. Iterate until green. **Do not delete or weaken a test to make it pass.**
5. Commit on green, then move to the next task.

If a test fails three times in a row, stop and re-read the specification — the failure usually reveals a misunderstanding of the requirement, not a bug in your code.

---

## Lab Navigation

| Lab | File | What you will build |
|-----|------|---------------------|
| 0 | [Environment Setup](lab-0-setup.md) | Toolchain, project scaffold, first commit |
| 1 | [Domain Modeling](lab-1-domain.md) | Enums, geometry, board, state, commands, events |
| 2 | [Game Engine](lab-2-engine.md) | `validate`, `reduce`, awards |
| 3 | [Persistence](lab-3-persistence.md) | SQLite event store, codec, snapshots, service |
| 4 | [CLI Interface](lab-4-cli.md) | Argument parser, REPL, text parser, renderer |
| 5 | [REST API & WebSockets](lab-5-api.md) | FastAPI routes, WebSocket hub, board layout |
| 6 | [React Frontend](lab-6-frontend.md) | Components, SVG board, live updates |
| 7 | [Metrics & Analytics](lab-7-metrics.md) | Projections, luck, pip equity, charts |
| 8 | [Testing Strategy](lab-8-testing.md) | Unit, integration, and API tests |
| 9 | [Polish & Delivery](lab-9-polish.md) | README, ADRs, demo prep |
| — | [Grading Rubric](grading-rubric.md) | How you will be evaluated |
| — | [Appendix: Catan Rules](appendix-rules.md) | Official rules reference |
| — | [Appendix: Hex Math](appendix-hex-math.md) | Coordinate-system reference |
| — | [Appendix: Reading](appendix-reading.md) | Books, articles, docs |

---

## Architecture You Must Achieve

```
┌─────────────────────────────────────────────────┐
│                  Web Browser                     │
│  React UI (SVG board, actions panel, metrics)   │
└────────────────────────┬────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼────────────────────────┐
│                   FastAPI Server                  │
│    (HTTP routes, WebSocket hub, request logic)   │
└────────────────────────┬────────────────────────┘
                         │ Python function calls
┌────────────────────────▼────────────────────────┐
│               GameService / Repository           │
│    (orchestrates engine + storage together)      │
└──────────┬─────────────────────────┬────────────┘
           │                         │
┌──────────▼──────────┐   ┌──────────▼──────────┐
│    Game Engine       │   │    Event Store       │
│  (validate, reduce)  │   │    (SQLite DB)       │
└──────────┬──────────┘   └─────────────────────-┘
           │
┌──────────▼──────────┐
│    Domain Models     │
│  (Board, GameState,  │
│   Commands, Events)  │
└─────────────────────┘
```

**The one rule you cannot break:** lower layers never import from upper layers. Domain models know nothing about HTTP. The engine knows nothing about the database. If you violate this, your code becomes untestable — and the labs are designed so that violations make later labs much harder.

---

## Final Deliverables

1. Working application (backend + frontend)
2. Test suite with ≥80% coverage on `catan/engine/` and `catan/store/`
3. `README.md` with setup instructions
4. Design document (`design/` directory): requirements, architecture, ADRs, task history
5. 15-minute live demo

---

## Learning Objectives

- **LO1** — Design a layered architecture separating domain logic from infrastructure
- **LO2** — Implement event sourcing: append-only logs, snapshots, state replay
- **LO3** — Write pure validation and reduction functions that are easy to test in isolation
- **LO4** — Build a REST API with proper HTTP semantics and WebSocket support
- **LO5** — Render interactive SVG graphics driven by API data
- **LO6** — Apply a test-first mindset: tests define behavior before implementation
- **LO7** — Use git branching and pull requests as a professional workflow
- **LO8** — Estimate, track, and reflect on project scope

---

## Time Estimate

~120–160 hours across a 16-week semester (7–10 hours/week). Each lab is roughly one week. Labs 2 (Engine) and 6 (Frontend) take the most time. Because you are deriving the implementation yourself, budget *more* time than a guided tutorial would suggest — the struggle is the point.
