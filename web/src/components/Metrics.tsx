import { useState } from "react";
import { playerColor } from "../colors";
import { ResIcon } from "../icons";
import type { MetricsDTO } from "../types";

const PIPS: Record<number, number> = {
  2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 0, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1,
};
const RES = ["brick", "lumber", "wool", "grain", "ore"] as const;

function Section({ title, defaultOpen = true, children }: {
  title: string; defaultOpen?: boolean; children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className={`m-section ${open ? "open" : ""}`}>
      <button className="m-head" onClick={() => setOpen((o) => !o)}>
        <span className="m-caret">{open ? "▾" : "▸"}</span> {title}
      </button>
      {open && <div className="m-body">{children}</div>}
    </div>
  );
}

function Legend({ m }: { m: MetricsDTO }) {
  return (
    <div className="m-legend">
      {m.player_order.map((p) => (
        <span key={p} className="m-legend-item">
          <span className="dot" style={{ background: playerColor(p, m.player_order) }} /> {p}
        </span>
      ))}
    </div>
  );
}

function DiceHistogram({ m }: { m: MetricsDTO }) {
  const total = m.dice_total || 1;
  const max = Math.max(1, ...Object.values(m.dice_histogram));
  return (
    <div className="chart">
      <p className="muted small">bar = observed · line = expected · {m.dice_total} rolls</p>
      <div className="dice tall">
        {Array.from({ length: 11 }, (_, i) => i + 2).map((n) => {
          const obs = m.dice_histogram[String(n)] ?? 0;
          const exp = (total * PIPS[n]) / 36;
          const red = n === 6 || n === 8;
          return (
            <div className="dice-col" key={n}>
              <span className="dice-count">{obs}</span>
              <div className="dice-bars">
                <div className="bar" style={{ height: `${(obs / max) * 100}%`, background: red ? "#e2483d" : undefined }} />
                <div className="exp" style={{ bottom: `${(exp / max) * 100}%` }} />
              </div>
              <div className={`dice-label ${red ? "red" : ""}`}>{n}</div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LuckBars({ m }: { m: MetricsDTO }) {
  const lucks = m.player_order.map((p) => m.players[p].luck);
  const scale = Math.max(1, ...lucks.map((l) => Math.abs(l)));
  return (
    <div className="chart">
      <p className="muted small">actual − expected production (cards)</p>
      {m.player_order.map((pid) => {
        const l = m.players[pid].luck;
        const pct = (Math.abs(l) / scale) * 50;
        return (
          <div className="luck-row" key={pid}>
            <span className="luck-name">
              <span className="dot" style={{ background: playerColor(pid, m.player_order) }} /> {pid}
            </span>
            <div className="luck-track">
              <div
                className={l >= 0 ? "luck-fill pos" : "luck-fill neg"}
                style={{ width: `${pct}%`, [l >= 0 ? "left" : "right"]: "50%" } as React.CSSProperties}
              />
              <div className="luck-zero" />
            </div>
            <span className="luck-val">{l >= 0 ? "+" : ""}{l.toFixed(1)}</span>
          </div>
        );
      })}
    </div>
  );
}

/** Generic multi-player line chart over an [seq, value] series. */
function TimelineChart({ m, series, unit }: {
  m: MetricsDTO; series: (pid: string) => [number, number][]; unit?: string;
}) {
  const W = 360, H = 200, P = 28;
  const all = m.player_order.flatMap(series);
  const maxSeq = Math.max(1, ...all.map((d) => d[0]));
  const maxV = Math.max(1, ...all.map((d) => d[1]));
  const x = (s: number) => P + (s / maxSeq) * (W - 2 * P);
  const y = (v: number) => H - P - (v / maxV) * (H - 2 * P);
  const ticks = 4;
  return (
    <div className="chart">
      <svg viewBox={`0 0 ${W} ${H}`} className="linechart">
        {Array.from({ length: ticks + 1 }, (_, i) => {
          const v = (maxV * i) / ticks;
          return (
            <g key={i}>
              <line x1={P} y1={y(v)} x2={W - P} y2={y(v)} className="grid" />
              <text x={P - 4} y={y(v) + 3} textAnchor="end" className="axis">{Math.round(v)}</text>
            </g>
          );
        })}
        <text x={W - P} y={H - 6} textAnchor="end" className="axis">move →</text>
        {unit && <text x={4} y={12} className="axis">{unit}</text>}
        {m.player_order.map((pid) => {
          const pts = series(pid).map((t) => `${x(t[0])},${y(t[1])}`).join(" ");
          return (
            <polyline key={pid} points={pts} fill="none"
              stroke={playerColor(pid, m.player_order)} strokeWidth={2.5} />
          );
        })}
      </svg>
      <Legend m={m} />
    </div>
  );
}

function ProductionByResource({ m }: { m: MetricsDTO }) {
  return (
    <div className="chart">
      <table className="mtable">
        <thead>
          <tr>
            <th>player</th>
            {RES.map((r) => <th key={r}><ResIcon r={r} /></th>)}
            <th>total</th>
          </tr>
        </thead>
        <tbody>
          {m.player_order.map((pid) => {
            const pm = m.players[pid];
            return (
              <tr key={pid}>
                <td className="left"><span className="dot" style={{ background: playerColor(pid, m.player_order) }} /> {pid}</td>
                {RES.map((r) => <td key={r}>{pm.production[r] ?? 0}</td>)}
                <td className="big">{pm.production_total}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function TradeFlow({ m }: { m: MetricsDTO }) {
  return (
    <div className="chart">
      <p className="muted small">net resources gained (+) / given (−) via trades</p>
      <table className="mtable">
        <thead>
          <tr>
            <th>player</th>
            {RES.map((r) => <th key={r}><ResIcon r={r} /></th>)}
            <th>dom</th><th>mar</th>
          </tr>
        </thead>
        <tbody>
          {m.player_order.map((pid) => {
            const pm = m.players[pid];
            return (
              <tr key={pid}>
                <td className="left"><span className="dot" style={{ background: playerColor(pid, m.player_order) }} /> {pid}</td>
                {RES.map((r) => {
                  const v = pm.trade_net[r] ?? 0;
                  return <td key={r} className={v > 0 ? "pos" : v < 0 ? "neg" : ""}>{v > 0 ? `+${v}` : v}</td>;
                })}
                <td>{pm.trades_domestic}</td>
                <td>{pm.trades_maritime}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RobberTable({ m }: { m: MetricsDTO }) {
  return (
    <div className="chart">
      <p className="muted small">stole = cards taken · blocked = production denied by your robber · lost = cards stolen from you</p>
      <table className="mtable">
        <thead>
          <tr><th>player</th><th title="knights played">⚔ kt</th><th>stole</th><th>blocked</th><th>lost</th></tr>
        </thead>
        <tbody>
          {m.player_order.map((pid) => {
            const pm = m.players[pid];
            return (
              <tr key={pid}>
                <td className="left"><span className="dot" style={{ background: playerColor(pid, m.player_order) }} /> {pid}</td>
                <td>{pm.knights_played}</td>
                <td className={pm.steals_made ? "pos" : ""}>{pm.steals_made}</td>
                <td className={pm.robber_blocked ? "pos" : ""}>{pm.robber_blocked}</td>
                <td className={pm.cards_stolen_from_me ? "neg" : ""}>{pm.cards_stolen_from_me}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function SummaryTable({ m }: { m: MetricsDTO }) {
  return (
    <div className="chart mtable-scroll">
      <table className="mtable">
        <thead>
          <tr>
            <th>player</th><th>VP</th><th>prod</th><th>exp</th><th>luck</th><th>pip</th>
            <th title="knights">⚔</th><th title="dev bought">dev+</th><th title="dev played">dev▶</th>
            <th title="cards discarded">disc</th><th title="steals made">rob</th><th title="cards stolen from">lost</th>
          </tr>
        </thead>
        <tbody>
          {m.player_order.map((pid) => {
            const pm = m.players[pid];
            const devB = Object.values(pm.dev_bought).reduce((a, b) => a + b, 0);
            const devP = Object.values(pm.dev_played).reduce((a, b) => a + b, 0);
            return (
              <tr key={pid}>
                <td className="left"><span className="dot" style={{ background: playerColor(pid, m.player_order) }} /> {pid}</td>
                <td className="big">{pm.final_vp}</td>
                <td>{pm.production_total}</td>
                <td>{pm.expected_production.toFixed(1)}</td>
                <td className={pm.luck >= 0 ? "pos" : "neg"}>{pm.luck >= 0 ? "+" : ""}{pm.luck.toFixed(1)}</td>
                <td>{pm.final_pip_equity}</td>
                <td>{pm.knights_played}</td>
                <td>{devB}</td>
                <td>{devP}</td>
                <td>{pm.cards_discarded}</td>
                <td>{pm.steals_made}</td>
                <td>{pm.cards_stolen_from_me}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function Metrics({ m }: { m: MetricsDTO }) {
  return (
    <div className="panel metrics">
      <h3>Metrics · turn {m.num_turns} · {m.dice_total} rolls{m.winner ? ` · 🏆 ${m.winner}` : ""}</h3>
      <Section title="Summary"><SummaryTable m={m} /></Section>
      <Section title="Victory points over time"><TimelineChart m={m} series={(p) => m.players[p].vp_timeline.map((t) => [t[0], t[1]])} unit="VP" /></Section>
      <Section title="Dice rolls"><DiceHistogram m={m} /></Section>
      <Section title="Luck"><LuckBars m={m} /></Section>
      <Section title="Production by resource"><ProductionByResource m={m} /></Section>
      <Section title="Robber"><RobberTable m={m} /></Section>
      <Section title="Hand size over time" defaultOpen={false}><TimelineChart m={m} series={(p) => m.players[p].hand_timeline} unit="cards" /></Section>
      <Section title="Pip equity over time" defaultOpen={false}><TimelineChart m={m} series={(p) => m.players[p].pip_timeline} unit="pips" /></Section>
      <Section title="Trade flow" defaultOpen={false}><TradeFlow m={m} /></Section>
    </div>
  );
}
