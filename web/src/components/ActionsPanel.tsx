import { useState } from "react";
import { ApiError } from "../api";
import { RESOURCE_ICON, ResIcon } from "../icons";
import type { GameStateDTO } from "../types";

const RES = ["brick", "lumber", "wool", "grain", "ore"] as const;
type Res = (typeof RES)[number];

type Apply = (cmd: Record<string, unknown>) => Promise<{ events: string[] }>;

/** Best maritime ratio for `give`, from ports the current player occupies. */
function bestRatio(state: GameStateDTO, player: string, give: Res): number {
  const p = state.players[player];
  const buildings = new Set([...p.settlements, ...p.cities]);
  let ratio = 4;
  for (const port of state.board.ports) {
    if (!port.vertices.some((v) => buildings.has(v))) continue;
    if (port.type === "generic") ratio = Math.min(ratio, 3);
    if (port.type === give) ratio = Math.min(ratio, 2);
  }
  return ratio;
}

export function ActionsPanel({
  state,
  apply,
  disabled,
  variant = "all",
  player,
  enforce = false,
  onRoadBuilding,
}: {
  state: GameStateDTO;
  apply: Apply;
  disabled: boolean;
  variant?: "all" | "roll" | "actions";
  player?: string;
  enforce?: boolean;   // when true, block trades the player can't actually make
  onRoadBuilding?: () => void;  // start placing Road Building roads on the map
}) {
  const me = player ?? state.player_order[state.current_index];
  const showRoll = variant !== "actions";
  const showEnd = variant !== "roll";
  const showTrades = variant !== "roll";
  const others = state.player_order.filter((p) => p !== me);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function run(cmd: Record<string, unknown>, label: string) {
    try {
      const res = await apply(cmd);
      setMsg({ ok: true, text: `✓ ${label} → ${res.events.join(", ")}` });
    } catch (err) {
      const d = err instanceof ApiError ? err.detail : String(err);
      setMsg({ ok: false, text: `✗ ${label}: ${typeof d === "string" ? d : JSON.stringify(d)}` });
    }
  }

  // turn
  const [d1, setD1] = useState(4);
  const [d2, setD2] = useState(3);

  // bank trade
  const [bGive, setBGive] = useState<Res>("brick");
  const [bRecv, setBRecv] = useState<Res>("ore");
  const [bRecvAmt, setBRecvAmt] = useState(1);
  const ratio = bestRatio(state, me, bGive);
  const bGiveAmt = ratio * bRecvAmt;

  // player trade
  const [partner, setPartner] = useState(others[0] ?? "");
  const [give, setGive] = useState<Record<Res, number>>({ brick: 0, lumber: 0, wool: 0, grain: 0, ore: 0 });
  const [recv, setRecv] = useState<Record<Res, number>>({ brick: 0, lumber: 0, wool: 0, grain: 0, ore: 0 });
  const mapOf = (m: Record<Res, number>) =>
    Object.fromEntries(RES.filter((r) => m[r] > 0).map((r) => [r, m[r]]));

  // dev cards
  const [yop1, setYop1] = useState<Res>("ore");
  const [yop2, setYop2] = useState<Res>("grain");
  const [mono, setMono] = useState<Res>("wool");

  const dis = disabled;
  const resOptions = RES.map((r) => <option key={r} value={r}>{RESOURCE_ICON[r]} {r}</option>);

  // Client-side legality (only enforced in guided mode): you can only give
  // resources you actually hold, and a domestic partner must hold their side.
  const myRes = state.players[me]?.resources ?? {};
  const bankShort = (myRes[bGive] ?? 0) < bGiveAmt;
  const bankBlocked = enforce && (bankShort || bGive === bRecv);
  // "Give" options for resources the player holds none of are disabled in guided
  // mode; you can still receive anything (the "get" side stays fully enabled).
  const bankGiveOptions = RES.map((r) => (
    <option key={r} value={r} disabled={enforce && (myRes[r] ?? 0) === 0}>{RESOURCE_ICON[r]} {r}</option>
  ));

  const giveSel = mapOf(give);
  const recvSel = mapOf(recv);
  const partnerRes = partner ? state.players[partner]?.resources ?? {} : {};
  const meLacks = RES.find((r) => give[r] > (myRes[r] ?? 0));
  const partnerLacks = RES.find((r) => recv[r] > (partnerRes[r] ?? 0));
  const emptySides = Object.keys(giveSel).length === 0 || Object.keys(recvSel).length === 0;
  const tradeBlocked = enforce && (!!meLacks || !!partnerLacks || emptySides);

  // Dev cards are recorded face-down: a purchase just adds a hidden card; its
  // type is only learned when it is played or revealed. So legality is about
  // having a playable hidden card, not about owning a specific type.
  const canAffordDev =
    !enforce || ((myRes.ore ?? 0) >= 1 && (myRes.wool ?? 0) >= 1 && (myRes.grain ?? 0) >= 1);
  const hiddenDev = state.players[me]?.hidden_dev ?? 0;
  const deckOut = state.dev_deck_size <= 0;
  // A card cannot be played the turn it was drawn, and only one per turn.
  const playableHidden = hiddenDev - (state.dev_bought_this_turn ?? 0);
  const canPlayDev = !enforce || (!state.dev_played_this_turn && playableHidden > 0);
  // A VP card may be revealed even the turn it was drawn.
  const canRevealVp = !enforce || hiddenDev > 0;

  return (
    <div className="panel actions">
      <h3>Actions · {me}</h3>

      <section>
        <div className="row-label">Turn</div>
        <div className="action-row">
          {showRoll && (
            <>
              <span>🎲</span>
              <input type="number" min={1} max={6} value={d1} onChange={(e) => setD1(+e.target.value)} className="mini" />
              <input type="number" min={1} max={6} value={d2} onChange={(e) => setD2(+e.target.value)} className="mini" />
              <button disabled={dis} onClick={() => run({ type: "RollDice", player: me, die1: d1, die2: d2 }, `roll ${d1}+${d2}`)}>Roll</button>
            </>
          )}
          {showEnd && (
            <button disabled={dis} onClick={() => run({ type: "EndTurn", player: me }, "end turn")}>End turn</button>
          )}
        </div>
      </section>

      {showTrades && <section>
        <div className="row-label">Bank / port trade</div>
        <div className="action-row">
          give
          <input type="number" value={bGiveAmt} readOnly className="mini" title={`${ratio}:1`} />
          <select value={bGive} onChange={(e) => setBGive(e.target.value as Res)}>
            {bankGiveOptions}
          </select>
          → get
          <input type="number" min={1} value={bRecvAmt} onChange={(e) => setBRecvAmt(Math.max(1, +e.target.value))} className="mini" />
          <select value={bRecv} onChange={(e) => setBRecv(e.target.value as Res)}>
            {resOptions}
          </select>
          <span className="muted">{ratio}:1</span>
          <button
            disabled={dis || bankBlocked}
            onClick={() => run(
              { type: "TradeWithBank", player: me, give: bGive, give_amount: bGiveAmt, receive: bRecv, receive_amount: bRecvAmt },
              `bank ${bGiveAmt} ${bGive} → ${bRecvAmt} ${bRecv}`,
            )}
          >Trade</button>
        </div>
        {bankBlocked && (
          <div className="msg err small">
            {bGive === bRecv ? "pick two different resources" : `${me} has ${myRes[bGive] ?? 0} ${bGive}, needs ${bGiveAmt}`}
          </div>
        )}
      </section>}

      {showTrades && <section>
        <div className="row-label">Record a trade</div>
        <div className="action-row">
          with
          <select value={partner} onChange={(e) => setPartner(e.target.value)}>
            {others.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
          <span className="muted small">logs the trade that actually happened</span>
        </div>
        <div className="trade-grid">
          <div>
            <div className="muted small">you give</div>
            {RES.map((r) => {
              const owned = myRes[r] ?? 0;
              const off = enforce && owned === 0;
              const cap = (v: number) => (enforce ? Math.min(owned, v) : v);
              return (
                <label key={r} className={`res-step ${off ? "off" : ""}`}><ResIcon r={r} />
                  <input
                    type="number" min={0} max={enforce ? owned : undefined}
                    disabled={off} value={give[r]} className="mini"
                    onChange={(e) => setGive({ ...give, [r]: cap(Math.max(0, +e.target.value)) })}
                  />
                </label>
              );
            })}
          </div>
          <div>
            <div className="muted small">you get</div>
            {RES.map((r) => {
              const owned = partnerRes[r] ?? 0;
              const off = enforce && owned === 0;
              const cap = (v: number) => (enforce ? Math.min(owned, v) : v);
              return (
                <label key={r} className={`res-step ${off ? "off" : ""}`}><ResIcon r={r} />
                  <input
                    type="number" min={0} max={enforce ? owned : undefined}
                    disabled={off} value={recv[r]} className="mini"
                    onChange={(e) => setRecv({ ...recv, [r]: cap(Math.max(0, +e.target.value)) })}
                  />
                </label>
              );
            })}
          </div>
        </div>
        <button
          disabled={dis || !partner || tradeBlocked}
          onClick={() => run(
            { type: "TradeWithPlayer", player: me, partner, gave: mapOf(give), received: mapOf(recv) },
            `traded with ${partner}`,
          )}
        >Record trade</button>
        {tradeBlocked && (
          <div className="msg err small">
            {emptySides
              ? "both sides must include at least one resource"
              : meLacks
                ? `${me} doesn't have enough ${meLacks} to give`
                : `${partner} doesn't have enough ${partnerLacks} to give`}
          </div>
        )}
        </section>}

      {showTrades && <section>
        <div className="row-label">
          Buy development card <span className="muted">(<ResIcon r="ore" /><ResIcon r="wool" /><ResIcon r="grain" />)</span>
        </div>
        <div className="dev-buy">
          <button
            className="dev-buy-btn"
            disabled={dis || (enforce && (!canAffordDev || deckOut))}
            title={
              deckOut ? "deck is empty"
                : !canAffordDev && enforce ? "need ore, wool, grain"
                : "record drawing a card — its type stays hidden until it's played or revealed"
            }
            onClick={() => run({ type: "BuyDevCard", player: me }, "buy dev card")}
          >
            Buy (hidden)
          </button>
          <span className="muted small">{state.dev_deck_size} left · {hiddenDev} hidden in hand</span>
        </div>

        <div className="row-label">Play / reveal a card</div>
        <div className="action-row">
          Victory Point
          <button
            disabled={dis || (enforce && !canRevealVp)}
            title="reveal a hidden card as a Victory Point (it then counts toward your score)"
            onClick={() => run({ type: "RevealVictoryPoint", player: me }, "reveal VP")}
          >Reveal</button>
          <span className="muted small">when a player shows a VP card</span>
        </div>
        {canPlayDev && (
          <>
            <div className="action-row">
              Year of Plenty
              <select value={yop1} onChange={(e) => setYop1(e.target.value as Res)}>{resOptions}</select>
              <select value={yop2} onChange={(e) => setYop2(e.target.value as Res)}>{resOptions}</select>
              <button disabled={dis} onClick={() => run({ type: "PlayYearOfPlenty", player: me, resources: [yop1, yop2] }, "year of plenty")}>Play</button>
            </div>
            <div className="action-row">
              Monopoly
              <select value={mono} onChange={(e) => setMono(e.target.value as Res)}>{resOptions}</select>
              <button disabled={dis} onClick={() => run({ type: "PlayMonopoly", player: me, resource: mono }, `monopoly ${mono}`)}>Play</button>
            </div>
            <div className="action-row">
              Road Building
              <button disabled={dis || !onRoadBuilding} onClick={() => onRoadBuilding?.()}>Place roads on map</button>
            </div>
          </>
        )}
        <p className="muted small">Knights are played via the Robber piece.</p>
      </section>}

      {msg && <div className={msg.ok ? "msg ok" : "msg err"}>{msg.text}</div>}
    </div>
  );
}
