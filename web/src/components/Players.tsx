import { playerColor } from "../colors";
import { ResIcon } from "../icons";
import type { GameStateDTO } from "../types";

const RES = ["brick", "lumber", "wool", "grain", "ore"] as const;

function vp(state: GameStateDTO, pid: string): number {
  const p = state.players[pid];
  let v = p.settlements.length + 2 * p.cities.length;
  if (state.longest_road_holder === pid) v += 2;
  if (state.largest_army_holder === pid) v += 2;
  v += p.dev_cards["victory_point"] ?? 0;
  return v;
}

export function Players({ state }: { state: GameStateDTO }) {
  const order = state.player_order;
  return (
    <div className="panel">
      <h3>Players</h3>
      <table className="players">
        <thead>
          <tr>
            <th></th><th>VP</th><th>hand</th>
            {RES.map((r) => <th key={r}><ResIcon r={r} /></th>)}
            <th>S</th><th>C</th><th>R</th><th>kt</th><th>dev</th>
          </tr>
        </thead>
        <tbody>
          {order.map((pid) => {
            const p = state.players[pid];
            const hand = Object.values(p.resources).reduce((a, b) => a + b, 0);
            const dev = Object.values(p.dev_cards).reduce((a, b) => a + b, 0);
            const current = order[state.current_index] === pid;
            return (
              <tr key={pid} className={current ? "current" : ""}>
                <td>
                  <span className="dot" style={{ background: playerColor(pid, order) }} />
                  {pid}
                  {state.longest_road_holder === pid && <span title="Longest Road"> 🛣</span>}
                  {state.largest_army_holder === pid && <span title="Largest Army"> ⚔</span>}
                </td>
                <td className="big">{vp(state, pid)}</td>
                <td>{hand}</td>
                {RES.map((r) => (
                  <td key={r}>{p.resources[r] ?? 0}</td>
                ))}
                <td>{p.settlements.length}</td>
                <td>{p.cities.length}</td>
                <td>{p.roads.length}</td>
                <td>{p.knights_played}</td>
                <td>{dev}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="bank">
        bank:{" "}
        {RES.map((r) => (
          <span key={r} className="bank-res"><ResIcon r={r} /> {state.bank[r]}</span>
        ))}
        {" "}· dev {Object.values(state.dev_deck).reduce((a, b) => a + b, 0)}
      </div>
    </div>
  );
}
