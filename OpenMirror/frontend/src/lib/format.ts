export const fmtInt = (n: number) => Math.round(n).toLocaleString("en-US");
export const fmtPct = (x: number) => `${Math.round(x * 100)}%`;

export function fmtDuration(s: number | null | undefined): string {
  if (s == null) return "—";
  if (s < 60) return `${Math.round(s)} s`;
  if (s < 3600) return `${Math.round(s / 60)} min`;
  if (s < 86400 * 2) return `${(s / 3600).toFixed(1)} h`;
  return `${(s / 86400).toFixed(1)} days`;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Timestamps are naive local times from the export; parse them by hand so the
// browser's own time zone never shifts them.
export function parts(iso: string) {
  const [d, t = "00:00:00"] = iso.split("T");
  const [y, m, day] = d.split("-").map(Number);
  const [hh, mm] = t.split(":").map(Number);
  return { y, m, day, hh, mm };
}

export function fmtDate(iso: string): string {
  const p = parts(iso);
  return `${p.day} ${MONTHS[p.m - 1]} ${p.y}`;
}

export function fmtMonth(iso: string, short = false): string {
  const p = parts(iso);
  return short ? `${MONTHS[p.m - 1]} ’${String(p.y).slice(2)}` : `${MONTHS[p.m - 1]} ${p.y}`;
}

export function fmtTime(iso: string): string {
  const p = parts(iso);
  return `${String(p.hh).padStart(2, "0")}:${String(p.mm).padStart(2, "0")}`;
}

export function nextMonth(iso: string): string {
  const p = parts(iso);
  const y = p.m === 12 ? p.y + 1 : p.y;
  const m = p.m === 12 ? 1 : p.m + 1;
  return `${y}-${String(m).padStart(2, "0")}-01`;
}

export function addDays(isoDate: string, days: number): string {
  const p = parts(isoDate);
  const d = new Date(Date.UTC(p.y, p.m - 1, p.day + days));
  return d.toISOString().slice(0, 10);
}
