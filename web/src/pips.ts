/** Dice-combination count per number token (7 is not placed on the board). */
export const PIPS: Record<number, number> = {
  2: 1, 3: 2, 4: 3, 5: 4, 6: 5,
  7: 0,
  8: 5, 9: 4, 10: 3, 11: 2, 12: 1,
};

/** Offsets for pip dots below the numeral — matches physical chit layouts. */
export function pipOffsets(count: number): [number, number][] {
  const s = 2.8;
  switch (count) {
    case 1:
      return [[0, 0]];
    case 2:
      return [[-s, 0], [s, 0]];
    case 3:
      return [[0, -s * 0.55], [-s, s * 0.55], [s, s * 0.55]];
    case 4:
      return [[-s, -s], [s, -s], [-s, s], [s, s]];
    case 5:
      return [[-s, -s], [s, -s], [0, 0], [-s, s], [s, s]];
    default:
      return [];
  }
}
