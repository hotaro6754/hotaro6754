// Participant identity colours: the validated categorical order, fixed per
// participant (by rank of message count at load time, never re-cycled).
export const SERIES_COUNT = 8;

export function seriesVar(index: number): string {
  return index < SERIES_COUNT ? `var(--series-${index + 1})` : "var(--series-other)";
}

export function makeColorMap(ids: number[]): Map<number, string> {
  const m = new Map<number, string>();
  ids.forEach((id, i) => m.set(id, seriesVar(i)));
  return m;
}
