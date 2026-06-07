export type Piece = "settlement" | "city" | "road" | "robber";

// A 1x1 transparent image so the browser's default drag ghost (the big chip)
// doesn't cover the board. The on-board hover preview is the real feedback.
const EMPTY_DRAG_IMG =
  typeof Image !== "undefined" ? new Image() : null;
if (EMPTY_DRAG_IMG) {
  EMPTY_DRAG_IMG.src =
    "data:image/gif;base64,R0lGODlhAQABAAAAACH5BAEKAAEALAAAAAABAAEAAAICTAEAOw==";
}

interface Props {
  tool: Piece | null;
  setTool: (p: Piece | null) => void;
  setDragKind: (p: Piece | null) => void;
  disabled: boolean;
  allowed?: Piece[];   // when set, only these pieces are shown
  canBuild?: Partial<Record<Piece, boolean>>;  // false = gray out (can't afford / no pieces left)
}

const PIECES: { kind: Piece; label: string; glyph: JSX.Element }[] = [
  {
    kind: "settlement",
    label: "Settlement",
    glyph: <circle cx={12} cy={12} r={7} />,
  },
  {
    kind: "city",
    label: "City",
    glyph: <rect x={5} y={5} width={14} height={14} rx={2} />,
  },
  {
    kind: "road",
    label: "Road",
    glyph: <rect x={3} y={9} width={18} height={6} rx={3} transform="rotate(-20 12 12)" />,
  },
  {
    kind: "robber",
    label: "Robber",
    glyph: <circle cx={12} cy={12} r={7} fill="#111" stroke="#fff" strokeWidth={1.5} />,
  },
];

export function Palette({ tool, setTool, setDragKind, disabled, allowed, canBuild }: Props) {
  const pieces = allowed ? PIECES.filter((p) => allowed.includes(p.kind)) : PIECES;
  return (
    <div className="panel palette">
      <h3>Place piece</h3>
      <div className="palette-row">
        {pieces.map((p) => {
          const unaffordable = canBuild?.[p.kind] === false;
          return (
          <button
            key={p.kind}
            className={`piece ${tool === p.kind ? "active" : ""} ${unaffordable ? "unaffordable" : ""}`}
            disabled={disabled || unaffordable}
            draggable={!disabled}
            aria-label={p.label}
            aria-pressed={tool === p.kind}
            onClick={() => setTool(tool === p.kind ? null : p.kind)}
            onDragStart={(e) => {
              setDragKind(p.kind);
              e.dataTransfer.effectAllowed = "copy";
              e.dataTransfer.setData("text/plain", p.kind);
              if (EMPTY_DRAG_IMG) e.dataTransfer.setDragImage(EMPTY_DRAG_IMG, 0, 0);
            }}
            onDragEnd={() => setDragKind(null)}
            title={unaffordable ? `Not enough resources for a ${p.label.toLowerCase()}` : `Drag onto the board, or click to select then click a spot`}
          >
            <svg viewBox="0 0 24 24" className="piece-icon" aria-hidden="true">{p.glyph}</svg>
            <span className="piece-label">{p.label}</span>
          </button>
        );
        })}
      </div>
      <p className="muted small">
        {disabled
          ? "viewing history — placement disabled"
          : tool
          ? `click a ${tool === "road" ? "road slot" : "spot"} on the board (Esc to cancel)`
          : "drag a piece onto the board, or click one to select"}
      </p>
    </div>
  );
}
