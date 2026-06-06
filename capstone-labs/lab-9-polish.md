# Lab 9 — Polish & Delivery

> **Goal:** Make the application production-ready and assemble your final submission artifacts.
>
> **Branch:** `git checkout -b lab-9-polish`

---

## Background

The code working on your laptop is not the deliverable — a *runnable, documented, defensible* project is. This lab produces the artifacts a grader (and a future maintainer) needs: a README a stranger can follow, a design document that explains your decisions, and a clean, rehearsed demo.

---

## Specification

### 1. `README.md`

Write a root README so that a classmate who has never seen the repo can run the app in under 10 minutes. It must contain:

- A one-paragraph description of what the app is.
- A **Features** list.
- **Requirements** (Python 3.12+, Node 20+, uv).
- **Setup** for backend (`uv sync`) and frontend (`cd web && npm install`).
- **Running** instructions (backend `uv run catan serve`, frontend `npm run dev`, the URL to open).
- An **Environment Variables** table documenting `CATAN_DB`.
- A **Running Tests** section.
- A link to the architecture document.

### 2. `design/` directory

| File | Contents |
|------|----------|
| `requirements.md` | Problem statement and user stories |
| `architecture.md` | System diagram + component responsibilities |
| `decisions.md` | Architecture Decision Records (ADRs) |
| `tasks.md` | Your project task history |

Write at least **3 ADRs**. An ADR explains *why* you made a choice, using this structure: **Context → Options Considered → Decision → Consequences**. Suggested topics:
- Event sourcing vs. mutable state storage.
- Axial hex coordinates vs. offset coordinates.
- Companion-app model (recorder observes reality) vs. digital-game model (engine controls the deck).
- Strict vs. dev mode toggle per game.

### 3. Hardening passes

- **Error handling:** no Python traceback ever reaches the browser; catch specific exceptions; rule violations return 422 with human-readable messages; 404s have descriptive text.
- **Performance:** keep the snapshot interval ≤ 25; note (and optionally cache) the topology recomputation in `decode_board`; understand the broadcast-per-command cost.
- **Security:** document that the API is unauthenticated (acceptable for local companion use), that SQLite is file-local, and that the engine validates all rules regardless of input.

---

## Your Tasks

1. Write the root `README.md` per the specification.
2. Write the four `design/` documents, including ≥3 ADRs.
3. Do the error-handling review and fix anything that leaks tracebacks or returns the wrong status code.
4. Write `design/architecture.md` with the layered diagram and a one-line responsibility for each layer.
5. Rehearse the demo (below) at least twice.

---

## Pre-Demo Checklist

- [ ] `uv run pytest` passes (0 failures)
- [ ] `cd web && npm run build` succeeds (no TypeScript errors)
- [ ] Fresh start: `uv run catan serve` against a brand-new `CATAN_DB`
- [ ] Create a 3-player game in the browser
- [ ] Complete the setup phase (6 settlements + 6 roads)
- [ ] Play 3 turns: roll, collect, build
- [ ] Open a second tab — both stay in sync
- [ ] Show the metrics screen
- [ ] Show the history scrubber
- [ ] Be ready to explain the architecture diagram

## Demo Script (15 minutes)

1. **(2 min)** Architecture diagram — the four layers and why lower layers don't import upper ones.
2. **(3 min)** Create a game; complete setup.
3. **(3 min)** Main game: roll, collect, build, end turn.
4. **(2 min)** Two tabs updating in real time.
5. **(2 min)** Metrics screen — dice histogram, luck.
6. **(3 min)** Questions.

> The most common demo failure is "it worked on my laptop." Practice on a clean checkout.

---

## Checkpoint

- [ ] `README.md` lets a classmate run the app from scratch in under 10 minutes
- [ ] `design/` has all four files
- [ ] At least 3 ADRs written
- [ ] No Python tracebacks appear in the browser network tab
- [ ] `uv run catan replay <id>` passes for a full game
- [ ] Final test run passes with ≥80% coverage
- [ ] Final commit: `"Lab 9: Documentation and polish for final submission"`
- [ ] Tag the release: `git tag v1.0.0 && git push origin v1.0.0`
