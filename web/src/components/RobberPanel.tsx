import { useState } from "react";
import { playerColor } from "../colors";
import { ResIcon } from "../icons";
import type { GameStateDTO, LayoutDTO } from "../types";

const RES = ["brick", "lumber", "wool", "grain", "ore"] as const;

const handSize = (p: GameStateDTO["players"][string]) =>
  Object.values(p.resources).reduce((a, b) => a + b, 0);

interface Props {
  state: GameStateDTO;
  layout: LayoutDTO;
  target: number[]; // [q, r]
  mover: string;
  mode: "seven" | "knight";
  onConfirm: (victim: string | null, resource: string | null) => void;
  onCancel: () => void;
}

export function RobberPanel({ state, layout, target, mover, mode, onConfirm, onCancel }: Props) {
  const [victim, setVictim] = useState<string | null>(null);
  const [resource, setResource] = useState<string | null>(null);

  const hex = layout.hexes.find((h) => h.coord[0] === target[0] && h.coord[1] === target[1]);

  const victims: string[] = [];
  if (hex) {
    for (const pid of state.player_order) {
      if (pid === mover) continue;
      const p = state.players[pid];
      const adjacent = hex.vertices.some((v) => p.settlements.includes(v) || p.cities.includes(v));
      if (adjacent && handSize(p) > 0 && !victims.includes(pid)) victims.push(pid);
    }
  }

  const canConfirm = victims.length === 0 || (victim != null && resource != null);

  return (
    <div className="panel robber-panel">
      <h3>{mode === "seven" ? "Move robber (rolled 7)" : "Play knight"}</h3>
      <div className="robber-target">
        target hex <b>{target.join(",")}</b>
        {hex && <span className="muted"> · {hex.terrain}{hex.number ? ` ${hex.number}` : ""}</span>}
      </div>

      {victims.length === 0 ? (
        <p className="muted">No adjacent player with cards — robber moves with no steal.</p>
      ) : (
        <>
          <div className="row-label">Rob from</div>
          <div className="chip-row">
            {victims.map((pid) => (
              <button
                key={pid}
                className={`actor-chip ${victim === pid ? "active" : ""}`}
                style={{ "--c": playerColor(pid, state.player_order) } as React.CSSProperties}
                onClick={() => { setVictim(pid); setResource(null); }}
              >
                <span className="dot" style={{ background: playerColor(pid, state.player_order) }} />
                {pid} <span className="muted">({handSize(state.players[pid])})</span>
              </button>
            ))}
          </div>

          {victim && (
            <>
              <div className="row-label">Resource stolen</div>
              <div className="chip-row">
                {RES.map((r) => {
                  const have = state.players[victim].resources[r] ?? 0;
                  return (
                    <button
                      key={r}
                      disabled={have === 0}
                      className={`res-chip ${resource === r ? "active" : ""}`}
                      onClick={() => setResource(r)}
                    >
                      <ResIcon r={r} /> <span className="muted">{have}</span>
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </>
      )}

      <div className="robber-actions">
        <button
          disabled={!canConfirm}
          onClick={() =>
            onConfirm(victims.length ? victim : null, victims.length ? resource : null)
          }
        >
          Confirm
        </button>
        <button className="link" onClick={onCancel}>Cancel</button>
      </div>
    </div>
  );
}
