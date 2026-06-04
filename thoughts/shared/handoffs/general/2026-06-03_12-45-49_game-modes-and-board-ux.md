---
date: 2026-06-03T12:45:49-06:00
researcher: jtia
git_commit: n/a (workspace is not a git repository)
branch: n/a
repository: catan_metrics
topic: "Catan Companion — custom board ports, game modes (strict/dev), and board/trade/dev-card UX"
tags: [implementation, catan, react, fastapi, game-modes, board-designer, ui]
status: complete
last_updated: 2026-06-03
last_updated_by: jtia
type: implementation_strategy
---

# Handoff: Catan Companion — game modes + board/UX features

## Task(s)
A multi-feature UI/engine session on the Catan companion app (workspace `/Users/jtia/Documents/local-dev/catan_metrics`). All tasks below are **completed** and verified (backend `uv run --no-sync pytest -q` = 100 passing; frontend `npm run build` type-checks + bundles clean):

1. **Custom board designer** — make the "custom (design your own)" board option functional: drag/click terrains + number tokens onto an empty board with live count limits, then create the game → normal game view. (Completed earlier; foundation for #2.)
2. **Sea-port placement + clearer ports** — place ports on perimeter edges during the design phase (standard distribution enforced); render ports offset into the sea with dock lines + colored badges, both in the designer and the live game board. (Completed.)
3. **Two game modes: strict ("guided") and dev ("sandbox")** — chosen at creation, **togglable mid-game**. Strict = full rule enforcement + step-by-step guided UI. Dev = lenient validation (bypasses turn/phase/cost/placement rules), keeps structural integrity, plus admin commands. Both track metrics. (Completed.)
4. **Dev/sandbox admin actions** — `SetResources` (set a player's hand) and `SetVictoryPoints` (manual VP bonus). Robber can be freely placed via lenient `MoveRobber`. (Completed.)
5. **Board view toggles** — overlay on the board (top-right) toggling resource icons / vertex ids / edge ids. (Completed.)
6. **Resource picture icons** — emoji icons for brick/lumber/wool/grain/ore everywhere resources appear, plus terrain icons on hexes. (Completed.)
7. **Per-player name + color at creation** — roster editor with unique-name + unique-color enforcement; colors persisted per game in `localStorage`. (Completed.)
8. **Trade resource gating (guided mode)** — disable/gray give-side resources you don't hold and get-side resources the partner doesn't hold; clamp amounts; warnings are fallback only. (Completed.)
9. **Dev-card buy menu + Road Building on map** — per-card buy buttons enabled only when affordable; Road Building is played by clicking road spots on the board. (Completed.)

## Critical References
- `/var/folders/40/w8564zsd19zc_xx97khctpbc0000gn/T/catan_metrics_handoff.md` — original architecture handoff (event-sourced; rules live only in `validate.py` + `reduce.py`; CLI/API/UI are thin shells through `GameService`). **Key invariant to preserve.**
- Engine purity: `compute_metrics` is a pure projection over the event log, so any new event type with a `case _: pass` in `projections.py::_record` keeps metrics working.

## Recent changes
Backend (Python):
- `catan/store/event_store.py` — added `mode` column to `games` (+ idempotent `_migrate()` via PRAGMA), `create_game(game_id, mode)`, `get_mode`, `set_mode`; `VALID_MODES`/`DEFAULT_MODE`.
- `catan/store/repository.py` — `create_game(cmd, mode)`, `get_mode`/`set_mode`, and `apply`/`try_apply` read mode → pass `strict=(mode!="dev")` to `validate`.
- `catan/engine/validate.py` — `validate(state, cmd, *, strict=True)`; gates (`_gate_play_action`, `_gate_play_dev`) return `[]` when lenient; every `_v_*` guards rule checks behind `if strict:` while keeping structural checks (valid ids, dice 1-6, victim→resource for reduce safety); added `_v_set_resources`/`_v_set_vp` (reject in strict mode).
- `catan/domain/commands.py` + `events.py` — added `SetResources`/`SetVictoryPoints` commands and `ResourcesSet`/`VictoryPointsSet` events (+ unions).
- `catan/domain/state.py` — `PlayerState.bonus_vp` (in clone + `victory_points()`).
- `catan/engine/reduce.py` — handle `ResourcesSet` (absolute set) and `VictoryPointsSet`.
- `catan/store/codec.py` — encode/decode new events, `decode_command` for new commands, player `bonus_vp`.
- `catan/domain/board.py` — `custom_board(..., port_edges=...)` + `_ports_on_edges()` (validates standard distribution, distinct edges, perimeter-only).
- `catan/api/app.py` — `_offset_outward()` for port positions; `_board_template` adds `perimeter_edges`, `default_ports`, `port_counts`; `GET /api/board_template`; `POST /api/games/{id}/mode`; `CreateGameRequest.mode`; `_encode_with_mode()` so every state payload (REST + WS + command responses) carries `mode`; custom create uses `port_edges`.

Frontend (React/TS, `web/src/`):
- `App.tsx` — routes Lobby → BoardDesigner/GameView; Lobby roster editor (name + color swatches, unique enforcement, 2–4 players, mode select); GameView branches on `state.mode` (guided vs sandbox), mode badge + toggle button, board-toggles overlay, guided `GuideBanner`, `DiscardPanel`, Road Building map mode (`rbEdges` state, `startRoadBuilding`/`submitRoadBuilding`, `onPlace` intercept, banner), loads per-game colors.
- `guide.ts` (new) — `setupExpected`, `expectedActor`, `guidedStep(state)` (drives guided UI step + allowed pieces).
- `components/BoardDesigner.tsx` (new) — terrain/number/port palettes with counts, perimeter port slots, drag+click, submit custom layout, persists colors.
- `components/ActionsPanel.tsx` — `variant` ("all"/"roll"/"actions"), `player`, `enforce`, `onRoadBuilding` props; trade give/get gating; dev-card **buy menu** + simplified play (YoP/Mono shown only if owned in guided) + Road-Building-on-map button.
- `components/AdminPanel.tsx` (new, dev only) — set hand + VP bonus.
- `components/DiscardPanel.tsx` (new) — per-player 7-discard forms.
- `components/Board.tsx` — `showVertexIds`/`showEdgeIds`/`showResIcons` props; offset port badges + dock lines; terrain resource icons; viewBox includes ports.
- `components/Palette.tsx` — optional `allowed` pieces filter (guided steps).
- `colors.ts` — `COLOR_CHOICES`, color-override registry (`setColorOverrides`/`playerColor`), `saveGameColors`/`loadGameColors`, `PORT_FILL`/`portText`.
- `icons.tsx` (new) — `RESOURCE_ICON`, `TERRAIN_ICON`, `ResIcon`.
- `types.ts`, `api.ts` — `mode`/`bonus_vp`/port template types; `createGame(..., mode)`, `setMode`, `getBoardTemplate`.
- `styles.css` — mode tags, guide banner, admin/discard/rb banners, board-toggles overlay, roster/swatches, dev-buy menu, port styling, `.res-step.off`.

Tests: `tests/test_modes.py` (new), additions to `tests/test_api.py` and `tests/test_board.py`.

## Learnings
- **Backend does NOT auto-reload.** After editing anything under `catan/`, you MUST restart `python -m catan --db game.db serve` or the UI hits stale routes / missing fields. This bit us repeatedly: "sandbox always defaults to guided" was simply the *old* backend running — `state.mode` came back undefined so the frontend defaulted to strict. Frontend hot-reloads via Vite automatically.
- **Restart recipe:** `lsof -ti tcp:8000 | xargs kill -9` (needs `required_permissions:["all"]` in sandbox; plain sandboxed lsof-kill silently no-ops), then `uv run --no-sync python -m catan --db game.db serve` (needs `full_network`). Confirm with the curl smoke check; wait for "Application startup complete".
- **pytest:** `cd` explicitly into `catan_metrics` (the `working_directory` tool param did not stick in this shell); run `uv run --no-sync pytest -q`. The outer `venv` causes a harmless VIRTUAL_ENV-mismatch warning.
- **Mode semantics:** strict = current engine unchanged. Dev leniency is implemented by neutralizing gate/rule checks in `validate` while keeping the SINGLE event-derivation code path (so maritime ratios, robber-steal expansion, etc. stay correct). Structural checks that prevent `reduce` crashes are always kept.
- **`enforce` prop** in `ActionsPanel` = guided mode only; sandbox passes it falsy so all trade/dev controls stay fully usable (preserves "edit anything freely").
- **Colors are client-side only** (localStorage `catan-colors:<gameId>` + a module registry consulted first by `playerColor`). Backend identifies players by name string. Colors won't transfer across browsers — acceptable for a local tool.
- **Custom board spiral order:** `/api/board_template` returns hexes in spiral order (index == position `custom_board` consumes). Ports are placed on perimeter edge ids; designer prefills `default_ports` and enforces the 4-generic + 1-each distribution.

## Artifacts
- This handoff: `thoughts/shared/handoffs/general/2026-06-03_12-45-49_game-modes-and-board-ux.md`
- Original architecture handoff: `/var/folders/40/w8564zsd19zc_xx97khctpbc0000gn/T/catan_metrics_handoff.md`
- Key engine files: `catan/engine/validate.py`, `catan/engine/reduce.py`, `catan/store/event_store.py`, `catan/store/repository.py`, `catan/api/app.py`, `catan/domain/board.py`
- Key UI files: `web/src/App.tsx`, `web/src/guide.ts`, `web/src/components/{BoardDesigner,ActionsPanel,Board,AdminPanel,DiscardPanel,Palette}.tsx`, `web/src/{colors.ts,icons.tsx,types.ts,api.ts,styles.css}`
- Tests: `tests/test_modes.py`, `tests/test_api.py`, `tests/test_board.py`

## Action Items & Next Steps
- **Nothing outstanding/blocking.** All requested features are implemented and building/passing.
- Run servers to use it (two terminals): backend `uv run --no-sync python -m catan --db game.db serve`; frontend `cd web && npm run dev` → http://localhost:5173/.
- Possible follow-ups the user may request next (not started): raw VP "set to absolute" (currently a +/- bonus); relax the port distribution to a 9-port cap for non-standard physical boards; Vitest frontend tests; CSV metrics export; a `--reload` flag for `catan serve`.

## Other Notes
- **Likely-running processes:** backend on :8000 (last started successfully this session, PID ~18291), Vite on :5173. The system also kept emitting stale "task error exit 137" notifications for OLD backend PIDs I intentionally killed during restarts — those are expected, not failures.
- **No `humanlayer`/`thoughts` tooling exists in this workspace** (no `humanlayer` binary, no `scripts/spec_metadata.sh`, not a git repo), so the standard `humanlayer thoughts sync` step was skipped — this doc was written directly to disk under `thoughts/shared/handoffs/general/`.
- Dev-card "buy menu" intentionally kept compact YoP/Monopoly play controls (they need resource selection that can't be a map click); Knight is still played via the Robber piece.
