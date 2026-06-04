# Phase 9 — Polish & Delivery

> **Goal:** Production-ready application and final submission artifacts.
>
> **Branch:** `git checkout -b phase-9-polish`

---

## 9.1 README.md

Your README is the front door. A stranger who has never seen your repo should be able to run the app in under 10 minutes.

```markdown
# Catan Companion

A digital companion for tracking physical Settlers of Catan games.
Players log every move; the app enforces rules, persists history, and computes analytics.

## Features
- Real-time board state with full rule enforcement
- WebSocket live sync across all connected browsers
- Post-game metrics: luck scores, dice histograms, production analytics
- Time-travel: replay any historical game state
- Dev mode for testing and board setup

## Requirements
- Python 3.12+
- Node.js 20+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Setup

### Backend
\`\`\`bash
uv sync
\`\`\`

### Frontend
\`\`\`bash
cd web && npm install
\`\`\`

## Running

\`\`\`bash
# Terminal 1: Backend (default port 8000)
uv run catan serve

# Terminal 2: Frontend (default port 5173)
cd web && npm run dev
\`\`\`

Open http://localhost:5173

### Environment Variables
| Variable | Default | Purpose |
|----------|---------|---------|
| `CATAN_DB` | `catan.db` | SQLite database path. Use `:memory:` for ephemeral. |

## Running Tests
\`\`\`bash
uv run pytest --cov=catan
\`\`\`

## Architecture
See [docs/architecture.md](docs/architecture.md) for the full system diagram.
```

---

## 9.2 Design Document

Your `design/` directory must contain:

| File | Contents |
|------|----------|
| `requirements.md` | Problem statement and user stories |
| `architecture.md` | System diagram and component descriptions |
| `decisions.md` | Architecture Decision Records (ADRs) |
| `tasks.md` | Your project task history |

### Writing an ADR

An **Architecture Decision Record** explains WHY you made a design choice. Template:

```markdown
# ADR-001: Use Event Sourcing for Game Persistence

## Context
We need to store game state across server restarts.

## Options Considered
1. Store current state only: simple, no history
2. Store all events (append-only): more complex, enables time travel and analytics
3. Store current state + events: redundant but fast reads

## Decision
Option 2 — event sourcing only, with periodic snapshots for read performance.

## Consequences
- State replay required after restart (mitigated by snapshots at interval 25)
- Any bug in the reducer affects historical replay
- Post-game analytics computed from event stream without touching live state
```

Write an ADR for each significant design choice:
- ADR-001: Event sourcing vs. mutable state storage
- ADR-002: Axial hex coordinates vs. offset coordinates
- ADR-003: Companion-app model (observer records reality) vs. digital-game model (engine controls)
- ADR-004: Strict vs. dev mode toggle per game

---

## 9.3 Error Handling Review

Walk through the code and check:
- No Python tracebacks reach the browser — API catches all exceptions
- Use specific exception types, not `except Exception:`
- Database errors log internally; return generic 500 to API
- `422` for rule violations with human-readable error strings in the response body
- All 404s have descriptive messages ("Game not found", not "Not Found")

---

## 9.4 Performance Notes

- **Snapshot interval** ≤ 25: loading state after 500 events should take < 100ms
- **Topology is recomputed** on every `decode_board()` call. This is acceptable because boards change rarely. If it becomes a bottleneck, cache by hex-list hash.
- **WebSocket broadcasts** on every successful command. Fine for typical game sizes (< 200 events). For production scale, you'd use a message queue.

---

## 9.5 Security Notes

- The API does not authenticate users. Anyone who knows a `game_id` can submit commands for any player. Acceptable for local-network companion use.
- SQLite is file-local — no network exposure.
- FastAPI validates JSON structure; the game engine validates rules. An attacker cannot corrupt state by sending malformed JSON — FastAPI rejects it before it reaches the engine.
- The `CATAN_DB` env var controls which database file is used. Don't expose the API on a public network without adding authentication.

---

## 9.6 Pre-Demo Checklist

Run through these before your 15-minute demo:

- [ ] `uv run pytest` passes (0 failures)
- [ ] `cd web && npm run build` succeeds (no TypeScript errors)
- [ ] Start fresh: `uv run catan serve` with a new `CATAN_DB`
- [ ] Create a 3-player game in the browser
- [ ] Complete setup phase (6 settlements + 6 roads)
- [ ] Play 3 turns: roll, collect, build something
- [ ] Open a second browser tab — both update in sync
- [ ] Show metrics screen after a full game
- [ ] Show history scrubber
- [ ] Be ready to explain the architecture diagram

---

## 9.7 Demo Script (15 minutes)

1. **(2 min)** Architecture diagram — explain the 4 layers, why lower layers don't import from upper
2. **(3 min)** Create a new game; complete setup phase (two settlements + roads each)
3. **(3 min)** Main game: roll dice, collect resources, build a settlement, end turn
4. **(2 min)** Open two browser tabs — show both updating in real time
5. **(2 min)** Show metrics screen — dice histogram, luck scores
6. **(3 min)** Questions

**Practice at least twice before the demo.** The most common failure mode is "it worked on my laptop."

---

## Phase 9 Checkpoint

- [ ] `README.md` lets a classmate run the app from scratch in under 10 minutes
- [ ] `design/` has all four files (`requirements.md`, `architecture.md`, `decisions.md`, `tasks.md`)
- [ ] At least 3 ADRs written
- [ ] No Python tracebacks appear in browser network tab
- [ ] `uv run catan replay <id>` passes for a full game
- [ ] Final test run: `uv run pytest` passes with ≥80% coverage
- [ ] Final commit: `"Phase 9: Documentation and polish for final submission"`
- [ ] Create a git tag: `git tag v1.0.0 && git push origin v1.0.0`
