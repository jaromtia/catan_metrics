import { useEffect, useRef } from "react";
import type { GameStateDTO } from "./types";

/** Subscribe to live state pushes for a game. `enabled` pauses updates
 *  (used when scrubbing through history). */
export function useGameSocket(
  gameId: string | null,
  enabled: boolean,
  onState: (state: GameStateDTO) => void,
) {
  const onStateRef = useRef(onState);
  onStateRef.current = onState;
  const enabledRef = useRef(enabled);
  enabledRef.current = enabled;

  useEffect(() => {
    if (!gameId) return;
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/api/games/${gameId}/ws`);
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "state" && enabledRef.current) {
        onStateRef.current(msg.state as GameStateDTO);
      }
    };
    return () => ws.close();
  }, [gameId]);
}
