import type React from "react";
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
  const currentPid = order[state.current_index];
  const currentColor = playerColor(currentPid, order);
  return (
    <div className="panel players">
      <div className="players-header">
        <h3>Players</h3>
        <span
          className="turn-indicator"
          style={{ "--c": currentColor } as React.CSSProperties}
        >
          <span className="dot" style={{ background: currentColor }} />
          {currentPid}&rsquo;s turn
        </span>
      </div>
      <table className="players">
        <thead>
          <tr>
            <th></th>
            <th className="help" title="Victory points">VP</th>
            <th className="help" title="Cards in hand">hand</th>
            {RES.map((r) => <th key={r}><ResIcon r={r} /></th>)}
            <th className="help" title="Settlements">S</th>
            <th className="help" title="Cities">C</th>
            <th className="help" title="Roads">R</th>
            <th className="help" title="Knights played">kt</th>
            <th className="help" title="Development cards in hand">dev</th>
          </tr>
        </thead>
        <tbody>
          {order.map((pid) => {
            const p = state.players[pid];
            const hand = Object.values(p.resources).reduce((a, b) => a + b, 0);
            const dev = (p.hidden_dev ?? 0) + Object.values(p.dev_cards).reduce((a, b) => a + b, 0);
            const isCurrent = pid === currentPid;
            return (
              <tr
                key={pid}
                className={isCurrent ? "current" : ""}
                style={{ "--c": playerColor(pid, order) } as React.CSSProperties}
              >
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
        {" "}· dev {state.dev_deck_size}
      </div>
    </div>
  );
}
