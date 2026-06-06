import { useState } from "react";
import { ApiError } from "../api";

const HINTS = [
  "settlement <v>", "road <e>",
  "roll <d1> <d2>", "end",
  "build road <e>", "build settlement <v>", "build city <v>",
  "buy <card>", "play knight <q,r> [victim [res]]",
  "trade bank <give> <n> <recv> <n>", "robber <q,r> [victim [res]]",
];

interface Props {
  disabled: boolean;
  apply: (line: string) => Promise<{ events: string[] }>;
}

export function CommandBar({ disabled, apply }: Props) {
  const [line, setLine] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!line.trim()) return;
    try {
      const res = await apply(line.trim());
      setMsg({ ok: true, text: `✓ ${res.events.join(", ")}` });
      setLine("");
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : String(err);
      setMsg({ ok: false, text: `✗ ${typeof detail === "string" ? detail : JSON.stringify(detail)}` });
    }
  }

  return (
    <div className="panel command">
      <h3>Command</h3>
      <form onSubmit={submit} className="cmdbar">
        <input
          value={line}
          onChange={(e) => setLine(e.target.value)}
          placeholder={disabled ? "viewing history…" : "type a move, e.g. roll 4 3"}
          disabled={disabled}
        />
        <button disabled={disabled}>Send</button>
      </form>
      {msg && <div className={msg.ok ? "msg ok" : "msg err"}>{msg.text}</div>}
      <details className="hints">
        <summary>command reference</summary>
        <ul>{HINTS.map((h) => <li key={h}><code>{h}</code></li>)}</ul>
      </details>
    </div>
  );
}
