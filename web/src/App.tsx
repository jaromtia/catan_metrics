import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "./api";
import {
  COLOR_CHOICES,
  loadGameColors,
  playerColor,
  saveGameColors,
  setColorOverrides,
} from "./colors";
import { canAffordBuild } from "./costs";
import { expectedActor, guidedStep } from "./guide";
import { ActionsPanel } from "./components/ActionsPanel";
import { AdminPanel } from "./components/AdminPanel";
import { Board } from "./components/Board";
import { BoardDesigner } from "./components/BoardDesigner";
import { CommandBar } from "./components/CommandBar";
import { DiscardPanel } from "./components/DiscardPanel";
import { EventLog } from "./components/EventLog";
import { Metrics } from "./components/Metrics";
import { Palette, type Piece } from "./components/Palette";
import { Players } from "./components/Players";
import { RobberPanel } from "./components/RobberPanel";
import { useGameSocket } from "./useGameSocket";
import type {
  EventDTO,
  GameStateDTO,
  GameSummary,
  LayoutDTO,
  MetricsDTO,
} from "./types";

interface Roster { players: string[]; colors: Record<string, string>; mode: string }

export default function App() {
  const [gameId, setGameId] = useState<string | null>(null);
  const [design, setDesign] = useState<Roster | null>(null);

  if (gameId) return <GameView gameId={gameId} onExit={() => setGameId(null)} />;
  if (design)
    return (
      <BoardDesigner
        players={design.players}
        colors={design.colors}
        mode={design.mode}
        onCancel={() => setDesign(null)}
        onCreated={(id) => {
          setDesign(null);
          setGameId(id);
        }}
      />
    );
  return <Lobby onOpen={setGameId} onDesign={setDesign} />;
}

interface PlayerSlot { name: string; color: string }

const DEFAULT_ROSTER: PlayerSlot[] = [
  { name: "red", color: "#e2483d" },
  { name: "blue", color: "#3b82f6" },
  { name: "white", color: "#e5e7eb" },
];

function Lobby({
  onOpen,
  onDesign,
}: {
  onOpen: (id: string) => void;
  onDesign: (r: Roster) => void;
}) {
  const [games, setGames] = useState<GameSummary[]>([]);
  const [roster, setRoster] = useState<PlayerSlot[]>(DEFAULT_ROSTER);
  const [board, setBoard] = useState("standard");
  const [seed, setSeed] = useState("");
  const [mode, setMode] = useState("strict");
  const [err, setErr] = useState<string | null>(null);

  const refresh = useCallback(() => {
    api.listGames().then(setGames).catch(() => setGames([]));
  }, []);
  useEffect(refresh, [refresh]);

  const setSlot = (i: number, patch: Partial<PlayerSlot>) =>
    setRoster((r) => r.map((s, j) => (j === i ? { ...s, ...patch } : s)));
  const addPlayer = () => {
    const used = new Set(roster.map((s) => s.color));
    const next = COLOR_CHOICES.find((c) => !used.has(c.hex)) ?? COLOR_CHOICES[0];
    setRoster((r) => [...r, { name: next.name, color: next.hex }]);
  };
  const removePlayer = (i: number) => setRoster((r) => r.filter((_, j) => j !== i));
  const movePlayer = (i: number, dir: -1 | 1) => setRoster((r) => {
    const j = i + dir;
    if (j < 0 || j >= r.length) return r;
    const next = [...r];
    [next[i], next[j]] = [next[j], next[i]];
    return next;
  });

  async function create() {
    setErr(null);
    const names = roster.map((s) => s.name.trim());
    if (names.some((n) => !n)) return setErr("every player needs a name");
    if (new Set(names).size !== names.length) return setErr("player names must be unique");
    if (names.length < 2 || names.length > 4) return setErr("base game supports 2–4 players");
    const hexes = roster.map((s) => s.color);
    if (new Set(hexes).size !== hexes.length) return setErr("each player needs a unique color");
    const colors = Object.fromEntries(roster.map((s) => [s.name.trim(), s.color]));
    if (board === "custom") {
      onDesign({ players: names, colors, mode });
      return;
    }
    const res = await api.createGame(names, board, seed ? Number(seed) : null, undefined, mode);
    saveGameColors(res.game_id, colors);
    setColorOverrides(colors);
    onOpen(res.game_id);
  }

  return (
    <div className="lobby">
      <h1>Catan Companion</h1>
      <div className="panel create">
        <h3>New game</h3>
        <div className="roster">
          <div className="row-label">Players (turn order)</div>
          {roster.map((slot, i) => (
            <div key={i} className="roster-row">
              <span className="roster-order">{i + 1}</span>
              <span className="dot" style={{ background: slot.color }} />
              <input
                className="roster-name"
                value={slot.name}
                onChange={(e) => setSlot(i, { name: e.target.value })}
                placeholder={`player ${i + 1}`}
              />
              <div className="swatches">
                {COLOR_CHOICES.map((c) => {
                  const takenByOther = roster.some((s, j) => j !== i && s.color === c.hex);
                  return (
                    <button
                      key={c.hex}
                      type="button"
                      disabled={takenByOther}
                      title={takenByOther ? `${c.name} (taken)` : c.name}
                      className={`swatch-btn ${slot.color === c.hex ? "active" : ""}`}
                      style={{ background: c.hex }}
                      onClick={() => setSlot(i, { color: c.hex })}
                    />
                  );
                })}
              </div>
              <div className="order-btns">
                <button type="button" className="order-btn" disabled={i === 0} onClick={() => movePlayer(i, -1)}>↑</button>
                <button type="button" className="order-btn" disabled={i === roster.length - 1} onClick={() => movePlayer(i, 1)}>↓</button>
              </div>
              {roster.length > 2 && (
                <button type="button" className="del" title="Remove player" onClick={() => removePlayer(i)}>✕</button>
              )}
            </div>
          ))}
          {roster.length < 4 && (
            <button type="button" className="link" onClick={addPlayer}>+ add player</button>
          )}
        </div>
        <label>Board
          <select value={board} onChange={(e) => setBoard(e.target.value)}>
            <option value="standard">standard</option>
            <option value="random">random</option>
            <option value="custom">custom (design your own)</option>
          </select>
        </label>
        {board !== "custom" && (
          <label>Seed <input value={seed} onChange={(e) => setSeed(e.target.value)} placeholder="optional" /></label>
        )}
        <label>Mode
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="strict">guided game (strict rules)</option>
            <option value="dev">sandbox (dev / free edit)</option>
          </select>
        </label>
        <p className="muted small">
          {mode === "strict"
            ? "Turn-by-turn play with full rule enforcement."
            : "Edit anything freely — no turn/phase/cost rules. Metrics still tracked."}
        </p>
        <button onClick={create}>{board === "custom" ? "Design board →" : "Create"}</button>
        {err && <div className="msg err">{err}</div>}
      </div>
      <div className="panel">
        <h3>Games</h3>
        {games.length === 0 && <p className="muted">No games yet.</p>}
        {games.map((g) => (
          <div key={g.game_id} className="game-row">
            <div className="game-open" onClick={() => onOpen(g.game_id)}>
              <code>{g.game_id.slice(0, 8)}</code>
              <span>{g.players.join(", ")}</span>
              <span className={`mode-tag ${g.mode === "dev" ? "dev" : "strict"}`}>{g.mode === "dev" ? "sandbox" : "guided"}</span>
              <span className="muted">{g.phase} · turn {g.turn}{g.winner ? ` · 🏆 ${g.winner}` : ""}</span>
            </div>
            <button
              className="del"
              title="Delete game"
              onClick={async (e) => {
                e.stopPropagation();
                if (!confirm(`Delete game ${g.game_id.slice(0, 8)}? This cannot be undone.`)) return;
                await api.deleteGame(g.game_id);
                refresh();
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

function GameView({ gameId, onExit }: { gameId: string; onExit: () => void }) {
  const [layout, setLayout] = useState<LayoutDTO | null>(null);
  const [state, setState] = useState<GameStateDTO | null>(null);
  const [events, setEvents] = useState<EventDTO[]>([]);
  const [metrics, setMetrics] = useState<MetricsDTO | null>(null);
  const [showVerts, setShowVerts] = useState(false);
  const [showEdges, setShowEdges] = useState(false);
  const [showResIcons, setShowResIcons] = useState(true);
  const [viewSeq, setViewSeq] = useState<number | null>(null); // null = live
  const [tool, setTool] = useState<Piece | null>(null);
  const [dragKind, setDragKind] = useState<Piece | null>(null);
  const [placeMsg, setPlaceMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [actor, setActor] = useState<string | null>(null);
  const [robberTarget, setRobberTarget] = useState<number[] | null>(null);
  const [rbEdges, setRbEdges] = useState<number[] | null>(null); // Road Building picks
  const [navOpen, setNavOpen] = useState(false); // mobile: expand collapsed header
  const live = viewSeq === null;

  const refreshDerived = useCallback(() => {
    api.getEvents(gameId).then(setEvents).catch(() => { });
    api.getMetrics(gameId).then(setMetrics).catch(() => { });
  }, [gameId]);

  const applyText = useCallback(
    async (line: string) => {
      const res = await api.sendCommandText(gameId, line);
      setState(res.state); // reliable update from the response (not just the socket)
      refreshDerived();
      return res;
    },
    [gameId, refreshDerived],
  );

  const applyCommand = useCallback(
    async (command: Record<string, unknown>) => {
      const res = await api.sendCommand(gameId, command);
      setState(res.state);
      refreshDerived();
      return res;
    },
    [gameId, refreshDerived],
  );

  const reloadState = useCallback(() => {
    api.getState(gameId).then(setState).catch(() => { });
  }, [gameId]);

  const toggleMode = useCallback(async () => {
    const next = state?.mode === "dev" ? "strict" : "dev";
    await api.setMode(gameId, next);
    reloadState();
  }, [gameId, state, reloadState]);

  // Esc cancels the active placement tool.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { setTool(null); setRbEdges(null); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // The acting player follows whoever the engine expects next; selecting a
  // player overrides until the expected player changes again.
  const expected = state ? expectedActor(state) : null;
  useEffect(() => {
    if (expected) setActor(expected);
  }, [expected]);

  // After a 7, the robber must move first — drop into robber mode automatically.
  const pendingRobber = state?.robber_pending ?? false;
  useEffect(() => {
    if (pendingRobber && live) setTool("robber");
  }, [pendingRobber, live]);

  // In guided (strict) mode, auto-select the single legal piece for the step so
  // the player just clicks the board; clear the tool when nothing is placeable.
  useEffect(() => {
    if (!state || !live || state.mode === "dev") return;
    const step = guidedStep(state);
    if (step.pieces.length === 1) setTool(step.pieces[0] as Piece);
    else if (step.pieces.length === 0) setTool(null);
  }, [state, live]);

  // Drop a selected build piece when the player can no longer afford it.
  useEffect(() => {
    if (!state || !live || state.mode === "dev" || state.phase === "setup" || !tool || tool === "robber") return;
    const actor = guidedStep(state).player ?? state.player_order[state.current_index];
    const p = state.players[actor];
    if (!p) return;
    const built = { settlements: p.settlements.length, cities: p.cities.length, roads: p.roads.length };
    if (!canAffordBuild(p.resources, tool, built)) setTool(null);
  }, [state, live, tool]);

  useEffect(() => {
    setColorOverrides(loadGameColors(gameId));
    api.getLayout(gameId).then(setLayout).catch(() => { });
    api.getState(gameId).then(setState).catch(() => { });
    refreshDerived();
  }, [gameId, refreshDerived]);

  useGameSocket(gameId, live, (s) => {
    setState(s);
    refreshDerived();
  });

  useEffect(() => {
    if (viewSeq != null) {
      api.getState(gameId, viewSeq).then(setState).catch(() => { });
    } else {
      api.getState(gameId).then(setState).catch(() => { });
    }
  }, [viewSeq, gameId]);

  if (!layout || !state) return <div className="loading">Loading…</div>;

  const maxSeq = events.length ? events[events.length - 1].seq : 0;
  const current = state.player_order[state.current_index];
  const guided = state.mode !== "dev";
  const step = guidedStep(state);
  const effActor = guided ? (step.player ?? expected ?? current) : (actor ?? expected ?? current);
  const allowedPieces = guided ? step.pieces : undefined;
  const buildAffordability =
    guided && state.phase !== "setup"
      ? (() => {
          const p = state.players[effActor];
          if (!p) return undefined;
          const built = { settlements: p.settlements.length, cities: p.cities.length, roads: p.roads.length };
          return {
            settlement: canAffordBuild(p.resources, "settlement", built),
            city: canAffordBuild(p.resources, "city", built),
            road: canAffordBuild(p.resources, "road", built),
            robber: true,
          };
        })()
      : undefined;
  const hasDiscards = Object.keys(state.pending_discards).length > 0;
  const showPalette = live && !robberTarget && (!guided || (allowedPieces?.length ?? 0) > 0);
  const bannerColor = playerColor(step.player ?? current, state.player_order);

  const startRoadBuilding = () => {
    setRbEdges([]);
    setTool("road");
    setPlaceMsg({ ok: true, text: "Road Building: click 2 road spots on the board" });
  };

  const submitRoadBuilding = async (edges: number[]) => {
    try {
      const res = await applyCommand({ type: "PlayRoadBuilding", player: effActor, edges });
      setPlaceMsg({ ok: true, text: `✓ ${effActor}: road building → ${res.events.join(", ")}` });
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : String(err);
      setPlaceMsg({ ok: false, text: `✗ road building: ${typeof detail === "string" ? detail : JSON.stringify(detail)}` });
    }
    setRbEdges(null);
    setTool(null);
  };

  const onPlace = async (kind: Piece, id: number) => {
    if (rbEdges && kind === "road") {
      if (rbEdges.includes(id)) return;
      const next = [...rbEdges, id];
      if (next.length >= 2) await submitRoadBuilding(next);
      else {
        setRbEdges(next);
        setPlaceMsg({ ok: true, text: "Road Building: 1 selected — pick 1 more (or finish with 1)" });
      }
      return;
    }
    const setup = state.phase === "setup";
    const command: Record<string, unknown> =
      kind === "city"
        ? { type: "BuildCity", player: effActor, vertex: id }
        : kind === "settlement"
          ? { type: setup ? "PlaceSetupSettlement" : "BuildSettlement", player: effActor, vertex: id }
          : { type: setup ? "PlaceSetupRoad" : "BuildRoad", player: effActor, edge: id };
    try {
      const res = await applyCommand(command);
      setPlaceMsg({ ok: true, text: `✓ ${effActor}: ${kind} ${id} → ${res.events.join(", ")}` });
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : String(err);
      setPlaceMsg({
        ok: false,
        text: `✗ ${effActor} ${kind} ${id}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`,
      });
    }
  };

  const mover = state.player_order[state.current_index];
  const robberMode: "seven" | "knight" = state.robber_pending ? "seven" : "knight";

  const confirmRobber = async (victim: string | null, resource: string | null) => {
    if (!robberTarget) return;
    const command = {
      type: robberMode === "seven" ? "MoveRobber" : "PlayKnight",
      player: mover,
      hex: robberTarget,
      victim,
      resource,
    };
    try {
      const res = await applyCommand(command);
      setPlaceMsg({ ok: true, text: `✓ ${mover}: ${command.type} → ${res.events.join(", ")}` });
      setRobberTarget(null);
      setTool(null);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : String(err);
      setPlaceMsg({
        ok: false,
        text: `✗ ${command.type}: ${typeof detail === "string" ? detail : JSON.stringify(detail)}`,
      });
    }
  };

  return (
    <div className="game">
      <header className={navOpen ? "open" : ""}>
        <button className="link" onClick={onExit}>← games</button>
        <span>current: <b>{current}</b></span>
        {state.dice && <span>🎲 {state.dice[0]}+{state.dice[1]}={state.dice[0] + state.dice[1]}</span>}
        {state.robber_pending && <span className="warn">move robber</span>}
        {hasDiscards && <span className="warn">discards pending</span>}
        {state.winner && <span className="win">🏆 {state.winner} wins</span>}
        <span className={`mode-tag hdr-extra ${guided ? "strict" : "dev"}`}>{guided ? "guided" : "sandbox"}</span>
        <button className="link hdr-extra" onClick={toggleMode} title="Switch rule enforcement for this game">
          {guided ? "→ sandbox" : "→ guided"}
        </button>
        <span className="phase hdr-extra">{state.phase}</span>
        <span className="hdr-extra">turn {state.turn_number}</span>
        <button
          type="button"
          className="nav-toggle"
          aria-label="Toggle game details"
          aria-expanded={navOpen}
          onClick={() => setNavOpen((o) => !o)}
        >
          {navOpen ? "✕" : "⋯"}
        </button>
      </header>

      <div className="layout">
        <div className="board-stage">
          {guided ? (
            <div
              className={`panel guide-banner ${step.key}`}
              style={{ "--player-color": bannerColor } as React.CSSProperties}
            >
              <div className="guide-title">{step.title}</div>
              <div className="guide-hint">{step.hint}</div>
            </div>
          ) : (
            <div className="panel actor-bar">
              <h3>Acting player (sandbox)</h3>
              <div className="actor-row">
                {state.player_order.map((pid) => (
                  <button
                    key={pid}
                    className={`actor-chip ${effActor === pid ? "active" : ""}`}
                    style={{ "--c": playerColor(pid, state.player_order) } as React.CSSProperties}
                    onClick={() => setActor(pid)}
                  >
                    <span className="dot" style={{ background: playerColor(pid, state.player_order) }} />
                    {pid}
                    {expected === pid && <span className="muted"> (next)</span>}
                  </button>
                ))}
              </div>
            </div>
          )}
          {live && hasDiscards && (
            <div className="board-sheet">
              <DiscardPanel state={state} apply={applyCommand} />
            </div>
          )}
          <div className="board-wrap">
            <div className="board-toggles">
              <label><input type="checkbox" checked={showResIcons} onChange={(e) => setShowResIcons(e.target.checked)} /> resources</label>
              <label><input type="checkbox" checked={showVerts} onChange={(e) => setShowVerts(e.target.checked)} /> vertices</label>
              <label><input type="checkbox" checked={showEdges} onChange={(e) => setShowEdges(e.target.checked)} /> edges</label>
            </div>
            <Board
              layout={layout}
              state={state}
              showVertexIds={showVerts}
              showEdgeIds={showEdges}
              showResIcons={showResIcons}
              actor={effActor}
              tool={tool}
              dragKind={dragKind}
              disabled={!live}
              onPlace={onPlace}
              onRobberHex={(coord) => setRobberTarget(coord)}
            />
          </div>
          <div className="board-dock">
            {placeMsg && <div className={placeMsg.ok ? "msg ok place dock-toast" : "msg err place dock-toast"}>{placeMsg.text}</div>}
            {live && rbEdges && (
              <div className="panel rb-banner">
                <span>Road Building · {rbEdges.length}/2 roads picked</span>
                {rbEdges.length >= 1 && (
                  <button onClick={() => submitRoadBuilding(rbEdges)}>Finish with {rbEdges.length}</button>
                )}
                <button className="link" onClick={() => { setRbEdges(null); setTool(null); }}>Cancel</button>
              </div>
            )}
            {showPalette && (
              <Palette tool={tool} setTool={setTool} setDragKind={setDragKind} disabled={!live} allowed={allowedPieces} canBuild={buildAffordability} />
            )}
            {live && robberTarget ? (
              <RobberPanel
                state={state}
                layout={layout}
                target={robberTarget}
                mover={mover}
                mode={robberMode}
                onConfirm={confirmRobber}
                onCancel={() => setRobberTarget(null)}
              />
            ) : live && (state.robber_pending || tool === "robber") ? (
              <div className="panel robber-hint">
                <h3>{state.robber_pending ? "Move robber (rolled 7)" : "Play knight"}</h3>
                <p>Tap a hex on the board to place the robber.</p>
              </div>
            ) : guided ? (
              <>
                {step.key === "roll" && <ActionsPanel state={state} apply={applyCommand} disabled={!live} variant="roll" player={current} enforce />}
                {step.key === "build" && <ActionsPanel state={state} apply={applyCommand} disabled={!live} variant="actions" player={current} enforce onRoadBuilding={startRoadBuilding} />}
              </>
            ) : (
              <ActionsPanel state={state} apply={applyCommand} disabled={!live} variant="all" player={effActor} onRoadBuilding={startRoadBuilding} />
            )}
          </div>
        </div>
        <div className="side-panels">
          <Players state={state} />
          {!guided && (
            <>
              <AdminPanel state={state} apply={applyCommand} />
              <CommandBar disabled={!live} apply={applyText} />
            </>
          )}
          <EventLog events={events} />
        </div>
        <div className="panel scrubber">
          <input
            type="range" min={0} max={maxSeq} value={viewSeq ?? maxSeq}
            onChange={(e) => {
              const v = Number(e.target.value);
              setViewSeq(v >= maxSeq ? null : v);
            }}
          />
          <span>{live ? `live (seq ${maxSeq})` : `history @ seq ${viewSeq}`}</span>
          {!live && <button className="link" onClick={() => setViewSeq(null)}>jump to live</button>}
        </div>
      </div>

      {metrics && <Metrics m={metrics} />}
    </div>
  );
}
