import { PIPS, pipOffsets } from "../pips";

interface Props {
  cx: number;
  cy: number;
  number: number;
}

/** Circular number chit with probability pips below the numeral (7 excluded on board). */
export function NumberToken({ cx, cy, number }: Props) {
  const red = number === 6 || number === 8;
  const pipCount = PIPS[number] ?? 0;
  const pips = pipOffsets(pipCount);
  const pipY = cy + 8;

  return (
    <>
      <circle cx={cx} cy={cy} r={14} fill="#f5efe0" stroke="#1b2330" />
      <text
        x={cx}
        y={pipCount > 0 ? cy - 2 : cy + 4}
        textAnchor="middle"
        className={red ? "num red" : "num"}
      >
        {number}
      </text>
      {pips.map(([dx, dy], i) => (
        <circle key={i} cx={cx + dx} cy={pipY + dy} r={1.35} className="pip" />
      ))}
    </>
  );
}
