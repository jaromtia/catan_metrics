# Capstone: Catan Companion App
## CS 499 — Senior Capstone in Software Engineering

A real-time digital companion for tracking physical Settlers of Catan games. Players sit at a real board and log every move; the app enforces rules, maintains a full event history, and computes post-game analytics.

---

## Quick Navigation

| Phase | File | Goal |
|-------|------|------|
| 0 | [Environment Setup](phase-0-setup.md) | Python, Node, uv, project scaffolding |
| 1 | [Domain Modeling](phase-1-domain.md) | Enums, geometry, board, state, commands, events |
| 2 | [Game Engine](phase-2-engine.md) | Validate, reduce, awards |
| 3 | [Persistence](phase-3-persistence.md) | SQLite event store, codec, snapshots |
| 4 | [CLI Interface](phase-4-cli.md) | Argument parser, REPL, text renderer |
| 5 | [REST API & WebSockets](phase-5-api.md) | FastAPI, WebSocket broadcast, board layout |
| 6 | [React Frontend](phase-6-frontend.md) | Components, SVG board, WebSocket hook |
| 7 | [Metrics & Analytics](phase-7-metrics.md) | Projections, luck scores, charts |
| 8 | [Testing Strategy](phase-8-testing.md) | Unit, integration, API tests |
| 9 | [Polish & Delivery](phase-9-polish.md) | README, ADRs, demo prep |
| — | [Grading Rubric](grading-rubric.md) | How you will be evaluated |
| — | [Appendix: Catan Rules](appendix-rules.md) | Official rules reference |
| — | [Appendix: Hex Math](appendix-hex-math.md) | Axial coordinates, vertex/edge identity |
| — | [Appendix: Reading](appendix-reading.md) | Books, articles, docs |

---

## What You Are Building

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

**Lower layers never import from upper layers.** Domain models know nothing about HTTP. The engine knows nothing about the database.

---

## Final Deliverables

1. Working application (backend + frontend)
2. Test suite with ≥80% coverage
3. `README.md` with setup instructions
4. Design document (`design/` directory)
5. 15-minute live demo

---

## Learning Objectives

- **LO1** — Layered architecture separating domain logic from infrastructure
- **LO2** — Event sourcing: append-only logs, snapshots, state replay
- **LO3** — Pure validation and reduction functions (easy to test in isolation)
- **LO4** — REST API with proper HTTP semantics and WebSocket support
- **LO5** — Interactive SVG graphics driven by API data
- **LO6** — Test-first mindset: tests define behavior before implementation
- **LO7** — Git branching and pull requests as professional workflow
- **LO8** — Estimate, track, and reflect on project scope

---

## Reference Implementation

This guide was written against a working reference implementation. For each phase, the `docs/` directory contains implementation notes:

- [`docs/architecture.md`](../docs/architecture.md)
- [`docs/domain-model.md`](../docs/domain-model.md)
- [`docs/engine.md`](../docs/engine.md)
- [`docs/persistence.md`](../docs/persistence.md)
- [`docs/cli.md`](../docs/cli.md)
- [`docs/api.md`](../docs/api.md)
- [`docs/web.md`](../docs/web.md)

These describe the finished system; the capstone guides walk you through building it.

---

## Time Estimate

~120–160 hours across a 16-week semester (7–10 hours/week).

Each phase is designed to fit in one week of work. Phases 2 (Engine) and 6 (Frontend) typically take the most time.
