"use client";

import { ArrowLeft, ArrowRight, FileSearch, Search } from "lucide-react";
import Link from "next/link";
import { use, useCallback, useEffect, useMemo, useState } from "react";
import {
  BucketBars,
  DailyCalendar,
  Fingerprint,
  InitiationBars,
  MomentAxis,
  MonthlyBars,
  WeekdayHourHeatmap,
} from "@/components/charts/charts";
import { Figure, Legend, TooltipLayer } from "@/components/charts/tooltip";
import { ConfidenceTag, EvidenceDrawer, MessageBrowser } from "@/components/report/evidence";
import { api, ApiError, type Analytics, type Chapter, type Finding, type Report } from "@/lib/api";
import { makeColorMap } from "@/lib/colors";
import { addDays, fmtDate, fmtDuration, fmtInt, fmtMonth, fmtPct, nextMonth } from "@/lib/format";

type BrowseQuery = { title: string; start?: string; end?: string; q?: string };

export default function ReportPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [data, setData] = useState<{ report: Report; analytics: Analytics } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [finding, setFinding] = useState<string | null>(null);
  const [browse, setBrowse] = useState<BrowseQuery | null>(null);
  const [search, setSearch] = useState("");
  const [gap, setGap] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => {
    api
      .report(id)
      .then((r) => {
        setData({ report: r.report, analytics: r.analytics });
        setGap(r.analytics.params.session_gap_minutes);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load the report."));
  }, [id]);
  useEffect(load, [load]);

  const people = useMemo(() => {
    if (!data) return [];
    const colors = makeColorMap(data.report.participants.map((p) => p.id));
    return data.report.participants.map((p) => ({ id: p.id, name: p.name, color: colors.get(p.id)! }));
  }, [data]);
  const colors = useMemo(() => new Map(people.map((p) => [p.id, p.color])), [people]);

  async function reanalyse(minutes: number) {
    setBusy(true);
    setGap(minutes);
    await api.reanalyze(id, minutes);
    load();
    setBusy(false);
  }

  if (error)
    return (
      <main className="mx-auto max-w-[760px] px-4 py-24">
        <p className="kicker mb-4">Report unavailable</p>
        <p className="display text-[2.4rem]">{error}</p>
        <Link href="/" className="pill mt-8">
          <ArrowLeft className="size-4" /> Back to reports
        </Link>
      </main>
    );
  if (!data)
    return (
      <main className="mx-auto max-w-[1240px] px-4 py-24 sm:px-6">
        <p className="kicker">Assembling the report…</p>
      </main>
    );

  const { report, analytics: a } = data;
  const findings = new Map(report.findings.map((f) => [f.id, f]));

  return (
    <TooltipLayer>
      <main>
        {/* Cover ------------------------------------------------------------------------------- */}
        <section className="border-b border-rule">
          <div className="mx-auto grid max-w-[1240px] gap-10 px-4 pt-10 pb-14 sm:px-6 lg:grid-cols-[1.15fr_0.85fr] lg:pt-16">
            <div className="flex flex-col">
              <Link href="/" className="kicker mb-10 inline-flex items-center gap-1.5 hover:text-ink">
                <ArrowLeft className="size-3" /> All reports
              </Link>
              <p className="kicker mb-5">Your conversation, decoded</p>
              <h1 className="display text-[clamp(3rem,9vw,7rem)] break-words" data-testid="report-title">
                {report.title}
              </h1>
              {!a.empty ? (
                <p className="mt-6 max-w-[540px] font-serif text-[1.3rem] leading-snug text-ink-2">
                  {fmtDate(a.overview.first_ts)} – {fmtDate(a.overview.last_ts)}. A report in eight chapters, built from{" "}
                  {fmtInt(a.overview.participant_messages)} messages. Every claim cites its sources.
                </p>
              ) : null}
              <ul className="mt-8 flex flex-wrap gap-x-5 gap-y-2" data-testid="participants">
                {people.map((p) => (
                  <li key={p.id} className="flex items-center gap-2 text-[15px]">
                    <span className="inline-block size-3 rounded-[2px]" style={{ background: p.color }} aria-hidden />
                    <span className="font-semibold">{p.name}</span>
                    <span className="num font-mono text-[12px] text-ink-3" data-testid="participant-count">
                      {fmtInt(report.participants.find((x) => x.id === p.id)!.messages)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
            {!a.empty ? (
              <div className="mx-auto w-full max-w-[460px]">
                <Fingerprint people={people} stats={a.participants} />
                <p className="mt-1 text-center font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3">
                  Cover generated from this chat · messages by hour of day
                </p>
              </div>
            ) : null}
          </div>
          {report.headline.length ? (
            <dl className="mx-auto grid max-w-[1240px] grid-cols-2 border-t border-rule px-4 sm:grid-cols-3 sm:px-6 lg:grid-cols-5">
              {report.headline.map((h) => (
                <div key={h.label} className="border-rule py-6 pr-4 lg:border-r lg:last:border-r-0 lg:[&:not(:first-child)]:pl-6">
                  <dt className="kicker mb-2">{h.label}</dt>
                  <dd className="display num text-[clamp(2.2rem,4.5vw,3.6rem)]">{h.value}</dd>
                </div>
              ))}
            </dl>
          ) : null}
        </section>

        {/* Tools --------------------------------------------------------------------------------- */}
        <div className="sticky top-0 z-30 border-b border-rule bg-paper/92 backdrop-blur-sm">
          <div className="mx-auto flex max-w-[1240px] flex-wrap items-center gap-3 px-4 py-2.5 sm:px-6">
            <nav className="hidden items-center gap-1 lg:flex" aria-label="Chapters">
              {report.chapters.map((c) => (
                <a key={c.key} href={`#${c.key}`} className="num rounded-full px-2 py-1 font-mono text-[11px] text-ink-3 hover:bg-secondary hover:text-ink" title={c.title}>
                  {c.number}
                </a>
              ))}
            </nav>
            <form
              className="flex min-w-[200px] flex-1 items-center gap-2 rounded-full border border-rule bg-card px-3 py-1.5 lg:max-w-[360px] lg:ml-auto"
              onSubmit={(e) => {
                e.preventDefault();
                if (search.trim()) setBrowse({ title: `“${search.trim()}”`, q: search.trim() });
              }}
            >
              <Search className="size-4 text-ink-3" aria-hidden />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search every message"
                aria-label="Search messages"
                className="min-w-0 flex-1 bg-transparent text-[14px] outline-none placeholder:text-ink-3"
                data-testid="search-input"
              />
            </form>
            <Link href={`/c/${id}/audit`} className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-[13px] text-ink-2 hover:bg-secondary">
              <FileSearch className="size-4" /> Import audit
            </Link>
          </div>
        </div>

        {/* Index --------------------------------------------------------------------------------- */}
        <section className="mx-auto max-w-[1240px] px-4 py-16 sm:px-6" aria-label="Contents">
          <p className="kicker mb-6">Contents</p>
          <ol className="border-t border-rule">
            {report.chapters.map((c) => (
              <li key={c.key} className="border-b border-rule">
                <a href={`#${c.key}`} className="group grid grid-cols-[3.5rem_1fr] items-baseline gap-4 py-3 sm:grid-cols-[6rem_1fr_auto]">
                  <span className="display num text-[clamp(1.6rem,3.5vw,2.8rem)] text-ink-3 group-hover:text-mark">{c.number}</span>
                  <span className="display text-[clamp(1.6rem,3.5vw,2.8rem)] text-ink-3 transition-colors group-hover:text-ink">{c.title}</span>
                  <span className="col-start-2 text-[14px] text-ink-3 sm:col-start-3 sm:text-right">{c.question}</span>
                </a>
              </li>
            ))}
          </ol>
        </section>

        {/* Chapters ------------------------------------------------------------------------------ */}
        {report.chapters.map((c) => (
          <ChapterSection
            key={c.key}
            chapter={c}
            findings={c.finding_ids.map((f) => findings.get(f)!).filter(Boolean)}
            onFinding={setFinding}
          >
            <Figures
              chapter={c}
              a={a}
              people={people}
              findings={report.findings}
              conversationId={id}
              onBrowse={setBrowse}
              onFinding={setFinding}
              gap={gap}
              onGap={reanalyse}
              busy={busy}
            />
          </ChapterSection>
        ))}

        <footer className="border-t border-rule">
          <div className="mx-auto max-w-[1240px] px-4 py-10 sm:px-6">
            <p className="max-w-[680px] text-[14px] text-ink-3">{report.disclaimer}</p>
            <p className="num mt-3 font-mono text-[11px] text-ink-3">
              Engine {report.engine_version} · generated {report.generated_at.replace("T", " ").slice(0, 16)} UTC · AI used: {report.ai_used ? "yes" : "no"}
            </p>
          </div>
        </footer>
      </main>

      <EvidenceDrawer conversationId={id} findingId={finding} onClose={() => setFinding(null)} colors={colors} />
      <MessageBrowser conversationId={id} query={browse} onClose={() => setBrowse(null)} colors={colors} />
    </TooltipLayer>
  );
}

function ChapterSection({
  chapter,
  findings,
  onFinding,
  children,
}: {
  chapter: Chapter;
  findings: Finding[];
  onFinding: (id: string) => void;
  children: React.ReactNode;
}) {
  return (
    <section id={chapter.key} className="scroll-mt-14 border-t border-ink" data-testid={`chapter-${chapter.key}`}>
      <div className="mx-auto max-w-[1240px] px-4 py-16 sm:px-6 lg:py-24">
        <header className="mb-10 grid gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <div className="display num text-[clamp(4.5rem,12vw,9rem)] text-ink-3">{chapter.number}</div>
          <div className="self-end">
            <h2 className="display text-[clamp(2.4rem,6vw,4.6rem)]">{chapter.title}</h2>
            <p className="mt-3 font-serif text-[1.35rem] text-ink-2 italic">{chapter.question}</p>
          </div>
        </header>
        <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,2fr)]">
          <aside className="order-2 lg:order-1">
            {findings.length ? (
              <div className="lg:sticky lg:top-20">
                <p className="kicker mb-3">Findings · {findings.length}</p>
                <ul className="border-t border-rule">
                  {findings.map((f) => (
                    <li key={f.id} className="border-b border-rule">
                      <button
                        type="button"
                        onClick={() => onFinding(f.id)}
                        className="group block w-full py-4 text-left focus-visible:outline-2 focus-visible:outline-mark"
                        data-testid="finding"
                        data-finding-id={f.id}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <span className="text-[15px] leading-snug font-semibold">{f.title}</span>
                          <ArrowRight className="mt-0.5 size-4 shrink-0 text-ink-3 transition-transform group-hover:translate-x-0.5 group-hover:text-mark" />
                        </div>
                        <p className="mt-1.5 text-[13px] leading-snug text-ink-2">{f.statement}</p>
                        <div className="mt-2 flex items-center gap-3">
                          <ConfidenceTag level={f.confidence} />
                          <span className="num font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">
                            {f.evidence.filter((e) => e.role === "support").length} sources
                            {f.evidence.some((e) => e.role === "counterexample")
                              ? ` · ${f.evidence.filter((e) => e.role === "counterexample").length} against`
                              : ""}
                          </span>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </aside>
          <div className="order-1 min-w-0 lg:order-2">
            <div className="prose-report max-w-[680px]">
              {chapter.paragraphs.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
            {children}
          </div>
        </div>
      </div>
    </section>
  );
}

function Figures({
  chapter,
  a,
  people,
  findings,
  conversationId,
  onBrowse,
  onFinding,
  gap,
  onGap,
  busy,
}: {
  chapter: Chapter;
  a: Analytics;
  people: { id: number; name: string; color: string }[];
  findings: Finding[];
  conversationId: string;
  onBrowse: (q: BrowseQuery) => void;
  onFinding: (id: string) => void;
  gap: number | null;
  onGap: (m: number) => void;
  busy: boolean;
}) {
  if (a.empty) return null;
  const legend = <Legend items={people.map((p) => ({ label: p.name, color: p.color }))} />;
  const stats = new Map(a.participants.map((p) => [p.id, p]));
  const out: React.ReactNode[] = [];

  for (const fig of chapter.figures) {
    if (fig === "monthly_activity")
      out.push(
        <Figure key={fig} title="Messages per month" legend={legend} caption="Click a month to read its messages. Red dots mark months that changed sharply (see The Moments).">
          <MonthlyBars
            a={a}
            people={people}
            highlight={new Set(a.volume_changes.map((v) => v.month))}
            onSelect={(m) => onBrowse({ title: fmtMonth(m), start: m, end: nextMonth(m) })}
          />
        </Figure>,
      );
    if (fig === "participant_table")
      out.push(
        <Figure key={fig} title="Side by side" caption="Medians are used for word counts and reply times because a few very long messages or slow replies would distort an average.">
          <div className="overflow-x-auto">
            <table className="num w-full min-w-[560px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">
                  <th className="py-2 font-normal" />
                  {people.map((p) => (
                    <th key={p.id} className="py-2 text-right font-normal">
                      <span className="inline-flex items-center gap-1.5">
                        <span className="inline-block size-2 rounded-[1px]" style={{ background: p.color }} />
                        {p.name}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ["Messages", (s) => fmtInt(s.messages)],
                    ["Share", (s) => fmtPct(s.share)],
                    ["Median words", (s) => String(s.median_words)],
                    ["Questions asked", (s) => fmtInt(s.questions)],
                    ["Media sent", (s) => fmtInt(s.media)],
                    ["Emoji used", (s) => fmtInt(s.emoji_total)],
                    ["Top emoji", (s) => s.top_emojis.slice(0, 3).map((e) => e.emoji).join(" ") || "—"],
                    ["Messages per turn", (s) => s.messages_per_turn.toFixed(2)],
                    ["Sessions started", (s) => `${fmtInt(s.sessions_initiated)} (${fmtPct(s.initiation_share)})`],
                    ["Median reply", (s) => fmtDuration(s.reply_median_s)],
                    ["Late-night share", (s) => fmtPct(s.late_night_share)],
                    ["Deleted / edited", (s) => `${s.deleted} / ${s.edited}`],
                  ] as [string, (s: Analytics["participants"][number]) => string][]
                ).map(([label, fn]) => (
                  <tr key={label} className="border-b border-rule">
                    <td className="py-2 text-ink-2">{label}</td>
                    {people.map((p) => (
                      <td key={p.id} className="py-2 text-right font-mono">
                        {stats.get(p.id) ? fn(stats.get(p.id)!) : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Figure>,
      );
    if (fig === "length_distribution")
      out.push(
        <Figure key={fig} title="How long messages are" caption="Share of each person’s text messages by word count.">
          <BucketBars rows={a.length_distribution} people={people} unit="texts" />
        </Figure>,
      );
    if (fig === "initiation_by_month" && people.length > 1)
      out.push(
        <Figure
          key={fig}
          title="Who started each month’s conversations"
          legend={legend}
          action={
            <label className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">
              New session after
              <select
                value={gap ?? 240}
                disabled={busy}
                onChange={(e) => onGap(Number(e.target.value))}
                className="rounded-full border border-rule bg-transparent px-2 py-0.5 text-[11px] text-ink"
                data-testid="gap-select"
              >
                {[60, 120, 240, 480, 720, 1440].map((m) => (
                  <option key={m} value={m}>
                    {m < 60 ? `${m} min` : `${m / 60} h`}
                  </option>
                ))}
              </select>
            </label>
          }
          caption="Share of sessions opened by each person. The dashed line marks an even split. Changing the session gap recomputes the whole report."
        >
          <InitiationBars a={a} people={people} />
        </Figure>,
      );
    if (fig === "reply_distribution")
      out.push(
        <Figure key={fig} title="How quickly people reply" caption="Within-session replies only. A reply that arrives after the session gap starts a new session and isn’t counted here.">
          <BucketBars rows={a.reply_times} people={people} unit="replies" />
        </Figure>,
      );
    if (fig === "daily_calendar")
      out.push(
        <Figure key={fig} title="Every day" caption="Stronger blue means more messages. Click a day to read it. Outlined cells fall outside the export.">
          <DailyCalendar a={a} onSelectDay={(d) => onBrowse({ title: fmtDate(d), start: d, end: addDays(d, 1) })} />
        </Figure>,
      );
    if (fig === "weekday_hour")
      out.push(
        <Figure key={fig} title="The weekly rhythm" caption="All participants combined, in the exporting phone’s local time.">
          <WeekdayHourHeatmap a={a} />
        </Figure>,
      );
    if (fig === "volume_changes") {
      const events = findings
        .filter((f) => ["volume_change", "large_session", "silence"].includes(f.finding_type) && f.time_start !== undefined)
        .map((f) => {
          const m = f.metrics as Record<string, number | string>;
          const kind: "up" | "down" | "session" | "gap" =
            f.finding_type === "large_session" ? "session" : f.finding_type === "silence" ? "gap" : m.direction === "up" ? "up" : "down";
          const ts = (f.time_start ?? f.time_end)!;
          const size = kind === "gap" ? Number(m.gap_s) / 86400 : Number(m.messages ?? 1);
          return { id: f.id, ts, size, kind, label: `${f.title}: ${f.statement}` };
        })
        .filter((e) => e.ts);
      out.push(
        <Figure key={fig} title="Notable moments on one axis" caption="Circle size is proportional to message count (or silence length). Click a circle for its evidence.">
          <MomentAxis a={a} events={events} onPick={onFinding} />
        </Figure>,
      );
    }
    if (fig === "topic_table")
      out.push(
        <Figure key={fig} title="Recurring words" caption={`${a.topics.method}. The three bars show use in the early, middle and late thirds of the timeline. Click a word to read every message that uses it.`}>
          <ol className="border-t border-rule" data-testid="topic-table">
            {a.topics.terms.slice(0, 15).map((t, i) => {
              const peak = Math.max(1, ...t.by_period);
              return (
                <li key={t.term} className="grid grid-cols-[2rem_1fr_auto] items-center gap-3 border-b border-rule py-2 sm:grid-cols-[2rem_1fr_9rem_5rem]">
                  <span className="num font-mono text-[11px] text-ink-3">{String(i + 1).padStart(2, "0")}</span>
                  <button type="button" className="text-left text-[17px] font-semibold hover:text-mark" onClick={() => onBrowse({ title: `“${t.term}”`, q: t.term })}>
                    {t.term}
                  </button>
                  <span className="hidden h-5 items-end gap-[3px] sm:flex" aria-label={`Early ${t.by_period[0]}, middle ${t.by_period[1]}, late ${t.by_period[2]}`}>
                    {t.by_period.map((v, k) => (
                      <span key={k} className="w-6 rounded-t-[2px] bg-ink" style={{ height: `${Math.max(8, (v / peak) * 100)}%`, opacity: v ? 1 : 0.15 }} />
                    ))}
                  </span>
                  <span className="num text-right font-mono text-[11px] text-ink-3">
                    {t.sessions} sessions
                  </span>
                </li>
              );
            })}
          </ol>
        </Figure>,
      );
    if (fig === "period_comparison" && a.periods.length === 3)
      out.push(
        <Figure key={fig} title="Early, middle, late" caption="The span from the first to the last message, split into three equal stretches of time.">
          <div className="overflow-x-auto">
            <table className="num w-full min-w-[560px] text-left text-[13px]">
              <thead>
                <tr className="border-b border-rule font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">
                  <th className="py-2 font-normal" />
                  {a.periods.map((p) => (
                    <th key={p.label} className="py-2 text-right font-normal">
                      {p.label}
                      <div className="normal-case tracking-normal">
                        {fmtDate(p.start)} – {fmtDate(p.end)}
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-rule">
                  <td className="py-2 text-ink-2">Messages per day</td>
                  {a.periods.map((p) => (
                    <td key={p.label} className="py-2 text-right font-mono">
                      {p.messages_per_day.toFixed(1)}
                    </td>
                  ))}
                </tr>
                {people.slice(0, 6).flatMap((person) => [
                  <tr key={`${person.id}-s`} className="border-b border-rule">
                    <td className="py-2 text-ink-2">
                      <span className="mr-1.5 inline-block size-2 rounded-[1px]" style={{ background: person.color }} />
                      {person.name}: share of sessions started
                    </td>
                    {a.periods.map((p) => (
                      <td key={p.label} className="py-2 text-right font-mono">
                        {p.by[String(person.id)] ? fmtPct(p.by[String(person.id)].initiation_share) : "—"}
                      </td>
                    ))}
                  </tr>,
                  <tr key={`${person.id}-r`} className="border-b border-rule">
                    <td className="py-2 text-ink-2">
                      <span className="mr-1.5 inline-block size-2 rounded-[1px]" style={{ background: person.color }} />
                      {person.name}: median reply
                    </td>
                    {a.periods.map((p) => (
                      <td key={p.label} className="py-2 text-right font-mono">
                        {fmtDuration(p.by[String(person.id)]?.reply_median_s)}
                      </td>
                    ))}
                  </tr>,
                ])}
              </tbody>
            </table>
          </div>
        </Figure>,
      );
    if (fig === "import_audit")
      out.push(
        <Figure key={fig} title="Colophon" caption="Every line of the export is accounted for: it starts a message, continues one, or is recorded as an issue.">
          <dl className="num grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
            {[
              ["All messages", fmtInt(a.overview.total_messages)],
              ["System notices", fmtInt(a.overview.system_messages)],
              ["Session gap", `${a.params.session_gap_minutes / 60} h`],
              ["Engine", a.engine_version],
            ].map(([k, v]) => (
              <div key={k}>
                <dt className="kicker mb-1">{k}</dt>
                <dd className="display text-[1.8rem]">{v}</dd>
              </div>
            ))}
          </dl>
          <Link href={`/c/${conversationId}/audit`} className="pill-ghost mt-6">
            <FileSearch className="size-4" /> Open the full import audit
          </Link>
        </Figure>,
      );
  }
  return <>{out}</>;
}
