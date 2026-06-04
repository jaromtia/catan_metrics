import { useEffect, useState } from "react";
import { ApiError } from "../api";
import { playerColor } from "../colors";
import { ResIcon } from "../icons";
import type { GameStateDTO } from "../types";

const RES = ["brick", "lumber", "wool", "grain", "ore"] as const;
type Res = (typeof RES)[number];
type Apply = (cmd: Record<string, unknown>) => Promise<{ events: string[] }>;

/** Dev-only direct state edits: set a player's hand and manual VP adjustment. */
export function AdminPanel({ state, apply }: { state: GameStateDTO; apply: Apply }) {
  const order = state.player_order;
  const [pid, setPid] = useState(order[0]);
  const [res, setRes] = useState<Record<Res, number>>({ brick: 0, lumber: 0, wool: 0, grain: 0, ore: 0 });
  const [vp, setVp] = useState(0);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  // Load the selected player's current hand / VP bonus into the editors.
  useEffect(() => {
    const p = state.players[pid];
    if (!p) return;
    setRes({
      brick: p.resources.brick ?? 0,
      lumber: p.resources.lumber ?? 0,
      wool: p.resources.wool ?? 0,
      grain: p.resources.grain ?? 0,
      ore: p.resources.ore ?? 0,
    });
    setVp(p.bonus_vp ?? 0);
  }, [pid, state]);

  async function run(cmd: Record<string, unknown>, label: string) {
    try {
      const r = await apply(cmd);
      setMsg({ ok: true, text: `✓ ${label} → ${r.events.join(", ")}` });
    } catch (err) {
      const d = err instanceof ApiError ? err.detail : String(err);
      setMsg({ ok: false, text: `✗ ${label}: ${typeof d === "string" ? d : JSON.stringify(d)}` });
    }
  }

  return (
    <div className="panel admin-panel">
      <h3>Sandbox tools</h3>
      <div className="action-row">
        <span className="dot" style={{ background: playerColor(pid, order) }} />
        <select value={pid} onChange={(e) => setPid(e.target.value)}>
          {order.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>

      <div className="row-label">Set hand (exact counts)</div>
      <div className="action-row">
        {RES.map((r) => (
          <label key={r} className="res-step"><ResIcon r={r} />
            <input type="number" min={0} value={res[r]} className="mini"
              onChange={(e) => setRes({ ...res, [r]: Math.max(0, +e.target.value) })} />
          </label>
        ))}
        <button onClick={() => run({ type: "SetResources", player: pid, resources: res }, `set ${pid} hand`)}>
          Apply hand
        </button>
      </div>

      <div className="row-label">Victory-point adjustment</div>
      <div className="action-row">
        bonus VP
        <input type="number" value={vp} className="mini" onChange={(e) => setVp(+e.target.value)} />
        <button onClick={() => run({ type: "SetVictoryPoints", player: pid, bonus: vp }, `set ${pid} VP +${vp}`)}>
          Apply VP
        </button>
        <span className="muted small">added to derived score</span>
      </div>

      {msg && <div className={msg.ok ? "msg ok" : "msg err"}>{msg.text}</div>}
    </div>
  );
}
