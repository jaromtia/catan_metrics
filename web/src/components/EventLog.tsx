import type { EventDTO } from "../types";

export function EventLog({ events }: { events: EventDTO[] }) {
  return (
    <div className="panel log">
      <h3>Event log</h3>
      <div className="log-scroll">
        {events.map((e) => {
          const { seq, ts, type, ...rest } = e;
          void ts;
          const fields = Object.entries(rest)
            .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
            .join(" ");
          return (
            <div key={seq} className="log-row">
              <span className="seq">{seq}</span>
              <span className="etype">{type}</span>
              <span className="efields">{fields}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
