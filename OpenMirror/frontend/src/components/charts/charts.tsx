"use client";

import { useMemo } from "react";
import type { Analytics, PersonStats } from "@/lib/api";
import { addDays, fmtDate, fmtDuration, fmtInt, fmtMonth, fmtPct, parts } from "@/lib/format";
import { TipRow, useTip } from "./tooltip";

type People = { id: number; name: string; color: string }[];

/* ---------------------------------------------------------------------------------------------
 * Cover fingerprint: a 24-hour polar bar chart of when each person writes. Generated from the
 * conversation itself, so every report has its own cover.
 * ------------------------------------------------------------------------------------------- */
export function Fingerprint({ people, stats }: { people: People; stats: PersonStats[] }) {
  const tip = useTip();
  const byId = new Map(stats.map((s) => [s.id, s]));
  const shown = people.slice(0, 4);
  const max = Math.max(1, ...shown.flatMap((p) => byId.get(p.id)?.hour_histogram ?? [0]));
  const R0 = 70;
  const R1 = 230;
  const slice = (Math.PI * 2) / 24;
  const band = (slice * 0.86) / Math.max(shown.length, 1);

  return (
    <svg viewBox="-260 -260 520 520" className="h-auto w-full" role="img" aria-label="When each participant writes, by hour of day">
      {[0.25, 0.5, 0.75, 1].map((f) => (
        <circle key={f} r={R0 + (R1 - R0) * f} fill="none" stroke="var(--rule)" strokeWidth={1} />
      ))}
      <circle r={R0 - 6} fill="none" stroke="var(--rule)" />
      {[0, 6, 12, 18].map((h) => {
        const a = h * slice - Math.PI / 2;
        return (
          <text
            key={h}
            x={Math.cos(a) * (R1 + 16)}
            y={Math.sin(a) * (R1 + 16)}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-[var(--ink-3)] font-mono text-[11px]"
          >
            {String(h).padStart(2, "0")}
          </text>
        );
      })}
      {Array.from({ length: 24 }, (_, h) =>
        shown.map((p, j) => {
          const v = byId.get(p.id)?.hour_histogram[h] ?? 0;
          const r = R0 + (R1 - R0) * (v / max);
          const a0 = h * slice - Math.PI / 2 - (slice * 0.86) / 2 + j * band;
          const a1 = a0 + band - 0.004;
          const path = arc(R0, Math.max(r, R0 + 1.5), a0, a1);
          return (
            <path
              key={`${h}-${p.id}`}
              d={path}
              fill={p.color}
              onMouseMove={(e) =>
                tip.show(
                  e,
                  <>
                    <div className="mb-1 font-semibold">
                      {String(h).padStart(2, "0")}:00–{String(h).padStart(2, "0")}:59
                    </div>
                    <TipRow color={p.color} label={p.name} value={`${fmtInt(v)} messages`} />
                  </>,
                )
              }
              onMouseLeave={tip.hide}
            />
          );
        }),
      )}
    </svg>
  );
}

function arc(r0: number, r1: number, a0: number, a1: number) {
  const p = (r: number, a: number) => `${(Math.cos(a) * r).toFixed(2)} ${(Math.sin(a) * r).toFixed(2)}`;
  return `M ${p(r0, a0)} L ${p(r1, a0)} A ${r1} ${r1} 0 0 1 ${p(r1, a1)} L ${p(r0, a1)} A ${r0} ${r0} 0 0 0 ${p(r0, a0)} Z`;
}

/* ---------------------------------------------------------------------------------------------
 * Monthly stacked bars (interactive timeline). Clicking a month opens its messages.
 * ------------------------------------------------------------------------------------------- */
export function MonthlyBars({
  a,
  people,
  onSelect,
  highlight,
}: {
  a: Analytics;
  people: People;
  onSelect?: (month: string) => void;
  highlight?: Set<string>;
}) {
  const tip = useTip();
  const months = useMemo(() => fillMonths(a.activity.monthly.map((m) => m.month)), [a]);
  const rows = new Map(a.activity.monthly.map((m) => [m.month, m]));
  const max = Math.max(1, ...a.activity.monthly.map((m) => m.total));
  const W = 1000;
  const H = 260;
  const pad = { l: 36, r: 8, t: 10, b: 26 };
  const bw = (W - pad.l - pad.r) / months.length;
  const y = (v: number) => pad.t + (H - pad.t - pad.b) * (1 - v / max);
  const ticks = niceTicks(max);
  const labelEvery = Math.ceil(months.length / 12);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Messages per month by participant">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} stroke="var(--rule)" strokeWidth={1} />
          <text x={pad.l - 6} y={y(t)} textAnchor="end" dominantBaseline="middle" className="fill-[var(--ink-3)] font-mono text-[10px]">
            {fmtInt(t)}
          </text>
        </g>
      ))}
      {months.map((m, i) => {
        const row = rows.get(m);
        const x = pad.l + i * bw;
        let acc = 0;
        const segs = people.map((p) => {
          const v = row?.by[String(p.id)] ?? 0;
          const y0 = y(acc);
          acc += v;
          const y1 = y(acc);
          return { p, v, y0, y1 };
        });
        const hot = highlight?.has(m);
        return (
          <g
            key={m}
            className={onSelect ? "cursor-pointer" : undefined}
            onClick={() => row && onSelect?.(m)}
            onMouseMove={(e) =>
              tip.show(
                e,
                <>
                  <div className="mb-1 font-semibold">{fmtMonth(m)}</div>
                  {people.map((p) => (
                    <TipRow key={p.id} color={p.color} label={p.name} value={fmtInt(row?.by[String(p.id)] ?? 0)} />
                  ))}
                  <div className="mt-1 border-t border-rule pt-1">
                    <TipRow label="Total" value={fmtInt(row?.total ?? 0)} />
                  </div>
                  {onSelect && row ? <div className="mt-1 text-ink-3">Click to read this month</div> : null}
                </>,
              )
            }
            onMouseLeave={tip.hide}
          >
            <rect x={x} y={pad.t} width={bw} height={H - pad.t - pad.b} fill="transparent" />
            {segs.map(({ p, v, y0, y1 }) =>
              v > 0 ? (
                <rect
                  key={p.id}
                  x={x + Math.min(1, bw * 0.1)}
                  y={y1}
                  width={Math.max(bw - 2, 1)}
                  height={Math.max(y0 - y1 - (y1 > pad.t ? 1 : 0), 0.5)}
                  fill={p.color}
                />
              ) : null,
            )}
            {hot ? <circle cx={x + bw / 2} cy={y(row?.total ?? 0) - 8} r={3} fill="var(--mark)" /> : null}
            {i % labelEvery === 0 ? (
              <text x={x + bw / 2} y={H - 8} textAnchor="middle" className="fill-[var(--ink-3)] font-mono text-[10px]">
                {fmtMonth(m, true)}
              </text>
            ) : null}
          </g>
        );
      })}
      <line x1={pad.l} x2={W - pad.r} y1={y(0)} y2={y(0)} stroke="var(--ink)" strokeWidth={1} />
    </svg>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Initiation share per month (100% stacked).
 * ------------------------------------------------------------------------------------------- */
export function InitiationBars({ a, people }: { a: Analytics; people: People }) {
  const tip = useTip();
  const months = fillMonths(a.sessions.initiation_by_month.map((m) => m.month));
  const rows = new Map(a.sessions.initiation_by_month.map((m) => [m.month, m]));
  const W = 1000;
  const H = 150;
  const pad = { l: 36, r: 8, t: 6, b: 24 };
  const bw = (W - pad.l - pad.r) / months.length;
  const h = H - pad.t - pad.b;
  const labelEvery = Math.ceil(months.length / 12);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Share of sessions started by each participant per month">
      {[0, 0.5, 1].map((t) => (
        <text key={t} x={pad.l - 6} y={pad.t + h * (1 - t)} textAnchor="end" dominantBaseline="middle" className="fill-[var(--ink-3)] font-mono text-[10px]">
          {fmtPct(t)}
        </text>
      ))}
      {months.map((m, i) => {
        const row = rows.get(m);
        const x = pad.l + i * bw;
        let acc = 0;
        return (
          <g
            key={m}
            onMouseMove={(e) =>
              tip.show(
                e,
                <>
                  <div className="mb-1 font-semibold">{fmtMonth(m)}</div>
                  {row ? (
                    people.map((p) => (
                      <TipRow key={p.id} color={p.color} label={`${p.name} started`} value={`${row.by[String(p.id)] ?? 0} of ${row.total}`} />
                    ))
                  ) : (
                    <div className="text-ink-3">No sessions</div>
                  )}
                </>,
              )
            }
            onMouseLeave={tip.hide}
          >
            <rect x={x} y={pad.t} width={bw} height={h} fill="transparent" />
            {row
              ? people.map((p) => {
                  const v = (row.by[String(p.id)] ?? 0) / row.total;
                  const y0 = pad.t + h * (1 - acc);
                  acc += v;
                  const y1 = pad.t + h * (1 - acc);
                  return v > 0 ? (
                    <rect key={p.id} x={x + 1} y={y1} width={Math.max(bw - 2, 1)} height={Math.max(y0 - y1 - 1, 0.5)} fill={p.color} />
                  ) : null;
                })
              : null}
            {i % labelEvery === 0 ? (
              <text x={x + bw / 2} y={H - 6} textAnchor="middle" className="fill-[var(--ink-3)] font-mono text-[10px]">
                {fmtMonth(m, true)}
              </text>
            ) : null}
          </g>
        );
      })}
      <line x1={pad.l} x2={W - pad.r} y1={pad.t + h / 2} y2={pad.t + h / 2} stroke="var(--paper)" strokeWidth={1.5} strokeDasharray="3 3" pointerEvents="none" />
    </svg>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Weekday × hour heatmap (sequential single-hue ramp).
 * ------------------------------------------------------------------------------------------- */
export function WeekdayHourHeatmap({ a }: { a: Analytics }) {
  const tip = useTip();
  const { grid, weekdays } = a.activity.weekday_hour;
  const max = Math.max(1, ...grid.flat());
  const cell = 34;
  const W = 40 + 24 * cell;
  const H = 7 * cell + 24;
  const step = (v: number) => (v === 0 ? 0 : 1 + Math.min(6, Math.floor((v / max) * 7)));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Messages by weekday and hour">
      {grid.map((row, d) =>
        row.map((v, h) => (
          <rect
            key={`${d}-${h}`}
            x={40 + h * cell + 1}
            y={d * cell + 1}
            width={cell - 2}
            height={cell - 2}
            rx={2}
            fill={`var(--seq-${step(v)})`}
            onMouseMove={(e) =>
              tip.show(
                e,
                <>
                  <div className="mb-1 font-semibold">
                    {weekdays[d]} {String(h).padStart(2, "0")}:00
                  </div>
                  <TipRow label="Messages" value={fmtInt(v)} />
                </>,
              )
            }
            onMouseLeave={tip.hide}
          />
        )),
      )}
      {weekdays.map((w, d) => (
        <text key={w} x={32} y={d * cell + cell / 2} textAnchor="end" dominantBaseline="middle" className="fill-[var(--ink-3)] font-mono text-[10px]">
          {w}
        </text>
      ))}
      {[0, 3, 6, 9, 12, 15, 18, 21].map((h) => (
        <text key={h} x={40 + h * cell + cell / 2} y={7 * cell + 16} textAnchor="middle" className="fill-[var(--ink-3)] font-mono text-[10px]">
          {String(h).padStart(2, "0")}
        </text>
      ))}
    </svg>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Daily calendar: one row per year, one cell per day.
 * ------------------------------------------------------------------------------------------- */
export function DailyCalendar({ a, onSelectDay }: { a: Analytics; onSelectDay?: (day: string) => void }) {
  const tip = useTip();
  const days = new Map(a.activity.daily.map((d) => [d.day, d.total]));
  const first = parts(a.overview.first_ts);
  const last = parts(a.overview.last_ts);
  const years = Array.from({ length: last.y - first.y + 1 }, (_, i) => first.y + i);
  const max = Math.max(1, ...a.activity.daily.map((d) => d.total));
  const c = 13;
  const W = 36 + 54 * c;
  const rowH = 7 * c + 18;
  const step = (v: number) => (v === 0 ? 0 : 1 + Math.min(6, Math.floor((Math.sqrt(v) / Math.sqrt(max)) * 7)));
  return (
    <svg viewBox={`0 0 ${W} ${years.length * rowH}`} className="h-auto w-full" role="img" aria-label="Messages per day, one row per year">
      {years.map((y, yi) => {
        const jan1 = new Date(Date.UTC(y, 0, 1));
        const offset = (jan1.getUTCDay() + 6) % 7; // Monday-first
        const n = (Date.UTC(y + 1, 0, 1) - jan1.getTime()) / 86400000;
        const start = `${y}-01-01`;
        return (
          <g key={y} transform={`translate(0 ${yi * rowH})`}>
            <text x={0} y={10} className="fill-[var(--ink-3)] font-mono text-[10px]">
              {y}
            </text>
            {Array.from({ length: n }, (_, i) => {
              const day = addDays(start, i);
              const v = days.get(day) ?? 0;
              const k = i + offset;
              const inRange = day >= a.overview.first_ts.slice(0, 10) && day <= a.overview.last_ts.slice(0, 10);
              return (
                <rect
                  key={day}
                  x={36 + Math.floor(k / 7) * c}
                  y={16 + (k % 7) * c - 16 + 4}
                  width={c - 2}
                  height={c - 2}
                  rx={1.5}
                  fill={inRange ? `var(--seq-${step(v)})` : "transparent"}
                  stroke={inRange ? "none" : "var(--rule)"}
                  strokeWidth={0.5}
                  className={v && onSelectDay ? "cursor-pointer" : undefined}
                  onClick={() => v && onSelectDay?.(day)}
                  onMouseMove={(e) =>
                    tip.show(
                      e,
                      <>
                        <div className="mb-1 font-semibold">{fmtDate(day)}</div>
                        <TipRow label="Messages" value={fmtInt(v)} />
                      </>,
                    )
                  }
                  onMouseLeave={tip.hide}
                />
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Bucketed distributions as small multiples (reply time, message length).
 * ------------------------------------------------------------------------------------------- */
export function BucketBars({
  rows,
  people,
  unit,
}: {
  rows: { participant_id: number; buckets: { bucket: string; n: number }[] }[];
  people: People;
  unit: string;
}) {
  const tip = useTip();
  const shown = people.filter((p) => rows.some((r) => r.participant_id === p.id)).slice(0, 6);
  const buckets = rows[0]?.buckets.map((b) => b.bucket) ?? [];
  return (
    <div className="grid gap-x-8 gap-y-6" style={{ gridTemplateColumns: `repeat(auto-fit, minmax(240px, 1fr))` }}>
      {shown.map((p) => {
        const r = rows.find((x) => x.participant_id === p.id)!;
        const total = r.buckets.reduce((s, b) => s + b.n, 0) || 1;
        return (
          <div key={p.id}>
            <div className="mb-2 flex items-center gap-2 text-[13px] font-semibold">
              <span className="inline-block size-2.5 rounded-[1px]" style={{ background: p.color }} aria-hidden />
              {p.name}
              <span className="num ml-auto font-mono text-[11px] font-normal text-ink-3">
                n = {fmtInt(total)} {unit}
              </span>
            </div>
            <div className="space-y-1">
              {r.buckets.map((b, i) => (
                <div
                  key={b.bucket}
                  className="grid grid-cols-[84px_1fr_44px] items-center gap-2"
                  onMouseMove={(e) =>
                    tip.show(e, <TipRow color={p.color} label={`${p.name} · ${buckets[i]}`} value={`${fmtInt(b.n)} (${fmtPct(b.n / total)})`} />)
                  }
                  onMouseLeave={tip.hide}
                >
                  <span className="font-mono text-[11px] text-ink-3">{b.bucket}</span>
                  <span className="h-3 bg-secondary">
                    <span className="block h-3 rounded-r-[2px]" style={{ width: `${(b.n / total) * 100}%`, background: p.color }} />
                  </span>
                  <span className="num text-right font-mono text-[11px] text-ink-2">{fmtPct(b.n / total)}</span>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}

/* ---------------------------------------------------------------------------------------------
 * Moments: a single time axis with proportional dots for surges, drops and big sessions.
 * ------------------------------------------------------------------------------------------- */
export function MomentAxis({
  a,
  events,
  onPick,
}: {
  a: Analytics;
  events: { id: string; ts: string; size: number; kind: "up" | "down" | "session" | "gap"; label: string }[];
  onPick: (id: string) => void;
}) {
  const tip = useTip();
  const t0 = toDays(a.overview.first_ts);
  const t1 = Math.max(toDays(a.overview.last_ts), t0 + 1);
  const W = 1000;
  const H = 170;
  const L = 150; // left gutter for lane labels
  const x = (iso: string) => L + ((toDays(iso) - t0) / (t1 - t0)) * (W - L - 24);
  const maxSize = Math.max(1, ...events.map((e) => e.size));
  const lanes: Record<string, number> = { up: 50, session: 90, down: 130, gap: 130 };
  const years = Array.from({ length: parts(a.overview.last_ts).y - parts(a.overview.first_ts).y + 2 }, (_, i) => parts(a.overview.first_ts).y + i);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full" role="img" aria-label="Notable moments on a timeline">
      {years.map((y) => {
        const iso = `${y}-01-01T00:00:00`;
        const xx = x(iso);
        if (xx < L || xx > W - 20) return null;
        return (
          <g key={y}>
            <line x1={xx} x2={xx} y1={20} y2={H - 18} stroke="var(--rule)" />
            <text x={xx + 4} y={H - 6} className="fill-[var(--ink-3)] font-mono text-[10px]">
              {y}
            </text>
          </g>
        );
      })}
      {[
        ["Surges", 50],
        ["Big sessions", 90],
        ["Drops & silences", 130],
      ].map(([l, yy]) => (
        <text key={l as string} x={0} y={yy as number} dominantBaseline="middle" className="fill-[var(--ink-3)] font-mono text-[10px] uppercase">
          {l}
        </text>
      ))}
      {[50, 90, 130].map((yy) => (
        <line key={yy} x1={L} x2={W - 20} y1={yy} y2={yy} stroke="var(--rule)" strokeDasharray="1 3" />
      ))}
      {events.map((e) => {
        const r = 4 + 14 * Math.sqrt(e.size / maxSize);
        const fill = e.kind === "up" ? "var(--ink)" : e.kind === "session" ? "var(--series-1)" : "var(--surface)";
        return (
          <circle
            key={e.id}
            cx={x(e.ts)}
            cy={lanes[e.kind]}
            r={r}
            fill={fill}
            stroke={e.kind === "down" || e.kind === "gap" ? "var(--mark)" : "var(--surface)"}
            strokeWidth={2}
            className="cursor-pointer"
            onClick={() => onPick(e.id)}
            onMouseMove={(ev) => tip.show(ev, <div>{e.label}<div className="mt-1 text-ink-3">Click for evidence</div></div>)}
            onMouseLeave={tip.hide}
          />
        );
      })}
    </svg>
  );
}

/* --- helpers -------------------------------------------------------------------------------- */

function toDays(iso: string) {
  const p = parts(iso);
  return Date.UTC(p.y, p.m - 1, p.day, p.hh, p.mm) / 86400000;
}

export function fillMonths(present: string[]): string[] {
  if (!present.length) return [];
  const sorted = [...present].sort();
  const out: string[] = [];
  let { y, m } = parts(sorted[0]);
  const end = parts(sorted[sorted.length - 1]);
  while (y < end.y || (y === end.y && m <= end.m)) {
    out.push(`${y}-${String(m).padStart(2, "0")}-01`);
    m += 1;
    if (m > 12) {
      m = 1;
      y += 1;
    }
  }
  return out;
}

function niceTicks(max: number): number[] {
  const raw = max / 4;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((s) => s * mag).find((s) => s >= raw) ?? raw;
  const out = [];
  for (let v = step; v <= max; v += step) out.push(Math.round(v));
  return out;
}

export { fmtDuration };
