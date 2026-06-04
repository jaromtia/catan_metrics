import { useState } from "react";
import { ApiError } from "../api";
import { ResIcon } from "../icons";
import type { GameStateDTO } from "../types";

const RES = ["brick", "lumber", "wool", "grain", "ore"] as const;
type Res = (typeof RES)[number];
type Apply = (cmd: Record<string, unknown>) => Promise<{ events: string[] }>;

function DiscardForm({ pid, need, hand, apply }: {
  pid: string; need: number; hand: Record<string, number>; apply: Apply;
}) {
  const [pick, setPick] = useState<Record<Res, number>>({ brick: 0, lumber: 0, wool: 0, grain: 0, ore: 0 });
  const [msg, setMsg] = useState<string | null>(null);
  const total = RES.reduce((a, r) => a + pick[r], 0);

  const submit = async () => {
    try {
      const res = await apply({
        type: "Discard",
        player: pid,
        resources: Object.fromEntries(RES.filter((r) => pick[r] > 0).map((r) => [r, pick[r]])),
      });
      setMsg(`✓ ${res.events.join(", ")}`);
    } catch (err) {
      const d = err instanceof ApiError ? err.detail : String(err);
      setMsg(`✗ ${typeof d === "string" ? d : JSON.stringify(d)}`);
    }
  };

  return (
    <div className="discard-form">
      <div className="discard-head">
        <b>{pid}</b> must discard <b>{need}</b> · selected {total}/{need}
      </div>
      <div className="action-row">
        {RES.map((r) => (
          <label key={r} className="res-step"><ResIcon r={r} /> ({hand[r] ?? 0})
            <input
              type="number" min={0} max={hand[r] ?? 0} value={pick[r]} className="mini"
              onChange={(e) => setPick({ ...pick, [r]: Math.max(0, Math.min(hand[r] ?? 0, +e.target.value)) })}
            />
          </label>
        ))}
        <button disabled={total !== need} onClick={submit}>Discard</button>
      </div>
      {msg && <div className="msg small">{msg}</div>}
    </div>
  );
}

export function DiscardPanel({ state, apply }: { state: GameStateDTO; apply: Apply }) {
  const pending = Object.entries(state.pending_discards);
  if (pending.length === 0) return null;
  return (
    <div className="panel discard-panel">
      <h3>Discards</h3>
      {pending.map(([pid, n]) => (
        <DiscardForm key={pid} pid={pid} need={n} hand={state.players[pid].resources} apply={apply} />
      ))}
    </div>
  );
}
