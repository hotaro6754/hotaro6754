"use client";

import { ChevronDown, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { api, type Confidence, type FindingDetail, type Message } from "@/lib/api";
import { fmtDate, fmtTime } from "@/lib/format";
import { cn } from "@/lib/utils";

export function ConfidenceTag({ level }: { level: Confidence }) {
  const dots = level === "high" ? 3 : level === "medium" ? 2 : 1;
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.14em] text-ink-3" title={`${level} confidence`}>
      <span className="flex gap-[3px]" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span key={i} className={cn("inline-block size-[6px] rounded-full", i < dots ? "bg-ink" : "bg-rule")} />
        ))}
      </span>
      {level}
    </span>
  );
}

/** A message rendered as a citation: who, when (as written in the export), where in the file, verbatim text. */
export function MessageCitation({
  m,
  color,
  focus,
  note,
  tone = "support",
}: {
  m: Message;
  color?: string;
  focus?: boolean;
  note?: string | null;
  tone?: "support" | "counterexample" | "context";
}) {
  const placeholder = m.message_type !== "text" && m.message_type !== "system";
  return (
    <div
      className={cn(
        "relative border-l-2 py-2 pr-2 pl-3",
        tone === "counterexample" ? "border-mark" : tone === "context" ? "border-rule" : "border-ink",
        focus && "bg-highlight",
      )}
      data-testid="evidence-message"
    >
      <div className="mb-0.5 flex flex-wrap items-baseline gap-x-2 text-[12px]">
        <span className="flex items-center gap-1.5 font-semibold">
          {color ? <span className="inline-block size-2 rounded-[1px]" style={{ background: color }} aria-hidden /> : null}
          {m.sender ?? "WhatsApp notice"}
        </span>
        <span className="num font-mono text-[11px] text-ink-3" title={`Parsed as ${m.ts}`}>
          {m.ts_original}
        </span>
        <span className="num ml-auto font-mono text-[10px] text-ink-3">
          line {m.line_start}
          {m.line_end !== m.line_start ? `–${m.line_end}` : ""} · #{m.id}
        </span>
      </div>
      <p className={cn("text-[15px] leading-snug break-words whitespace-pre-wrap", placeholder && "font-mono text-[12px] text-ink-3 italic")}>
        {m.text || <span className="text-ink-3 italic">(empty message)</span>}
        {m.is_edited ? <span className="ml-1 font-mono text-[10px] text-ink-3">edited</span> : null}
      </p>
      {note ? <p className="mt-1 font-mono text-[10px] uppercase tracking-[0.1em] text-ink-3">{note}</p> : null}
    </div>
  );
}

function ContextToggle({ conversationId, message, colors }: { conversationId: string; message: Message; colors: Map<number, string> }) {
  const [open, setOpen] = useState(false);
  const [ctx, setCtx] = useState<Message[] | null>(null);
  useEffect(() => {
    if (open && !ctx) api.messages(conversationId, { around: message.id, radius: 5 }).then((r) => setCtx(r.messages));
  }, [open, ctx, conversationId, message.id]);
  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="mt-1 ml-3 inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3 hover:text-ink"
        aria-expanded={open}
        data-testid="show-context"
      >
        <ChevronDown className={cn("size-3 transition-transform", open && "rotate-180")} />
        {open ? "Hide context" : "Show in context"}
      </button>
      {open ? (
        <div className="mt-2 ml-3 space-y-0.5 border-l border-dashed border-rule pl-3">
          {ctx ? (
            ctx.map((m) => (
              <MessageCitation key={m.id} m={m} color={m.sender_id != null ? colors.get(m.sender_id) : undefined} focus={m.id === message.id} tone="context" />
            ))
          ) : (
            <Loader2 className="size-4 animate-spin text-ink-3" />
          )}
        </div>
      ) : null}
    </div>
  );
}

export function EvidenceDrawer({
  conversationId,
  findingId,
  onClose,
  colors,
}: {
  conversationId: string;
  findingId: string | null;
  onClose: () => void;
  colors: Map<number, string>;
}) {
  const [data, setData] = useState<FindingDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setData(null);
    setError(null);
    if (findingId) api.finding(conversationId, findingId).then(setData).catch((e) => setError(String(e.message ?? e)));
  }, [conversationId, findingId]);

  const support = data?.evidence.filter((e) => e.role === "support") ?? [];
  const counter = data?.evidence.filter((e) => e.role === "counterexample") ?? [];

  return (
    <Sheet open={findingId !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 overflow-y-auto border-l border-rule bg-paper p-0 sm:max-w-[620px]" data-testid="evidence-drawer">
        <SheetHeader className="border-b border-rule p-6 pb-5">
          <div className="kicker">Case file · {findingId}</div>
          <SheetTitle className="display mt-2 text-[2rem] leading-[1.02]">{data?.title ?? "Loading…"}</SheetTitle>
          <SheetDescription className="sr-only">Evidence, method and confidence for this finding.</SheetDescription>
        </SheetHeader>
        {error ? <p className="p-6 text-destructive">{error}</p> : null}
        {data ? (
          <div className="space-y-8 p-6">
            <p className="font-serif text-[1.15rem] leading-relaxed" data-testid="finding-statement">
              {data.statement}
            </p>

            <dl className="grid grid-cols-[110px_1fr] gap-x-4 gap-y-3 border-y border-rule py-4 text-[14px]">
              <dt className="kicker pt-0.5">Confidence</dt>
              <dd>
                <ConfidenceTag level={data.confidence} />
                <p className="mt-1 text-ink-2">{data.confidence_reason}</p>
              </dd>
              <dt className="kicker pt-0.5">Method</dt>
              <dd className="text-ink-2">{data.method}</dd>
              {data.time_start ? (
                <>
                  <dt className="kicker pt-0.5">Window</dt>
                  <dd className="num font-mono text-[12px] text-ink-2">
                    {fmtDate(data.time_start)}
                    {data.time_end ? ` → ${fmtDate(data.time_end)}` : ""}
                  </dd>
                </>
              ) : null}
            </dl>

            <section>
              <h3 className="kicker mb-3 text-ink">
                Supporting messages · {support.length}
              </h3>
              {support.length ? (
                <div className="space-y-3">
                  {support.map((e) => (
                    <div key={`s-${e.message.id}-${e.note}`}>
                      <MessageCitation m={e.message} note={e.note} color={e.message.sender_id != null ? colors.get(e.message.sender_id) : undefined} />
                      <ContextToggle conversationId={conversationId} message={e.message} colors={colors} />
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-[14px] text-ink-3">This finding is about the export as a whole and has no single supporting message.</p>
              )}
            </section>

            <section>
              <h3 className="kicker mb-3 text-mark">Against this · {counter.length}</h3>
              {data.counterexample_note ? <p className="mb-3 text-[14px] text-ink-2">{data.counterexample_note}</p> : null}
              {counter.length ? (
                <div className="space-y-3">
                  {counter.map((e) => (
                    <div key={`c-${e.message.id}-${e.note}`}>
                      <MessageCitation m={e.message} note={e.note} tone="counterexample" color={e.message.sender_id != null ? colors.get(e.message.sender_id) : undefined} />
                      <ContextToggle conversationId={conversationId} message={e.message} colors={colors} />
                    </div>
                  ))}
                </div>
              ) : !data.counterexample_note ? (
                <p className="text-[14px] text-ink-3">No counterexamples apply. This is an exact count.</p>
              ) : null}
            </section>

            <details className="border-t border-rule pt-4 text-[12px]">
              <summary className="kicker cursor-pointer">Raw metrics</summary>
              <pre className="mt-3 max-h-[300px] overflow-auto rounded-sm bg-secondary p-3 font-mono text-[11px] leading-relaxed text-ink-2">
                {JSON.stringify(data.metrics, null, 2)}
              </pre>
            </details>
          </div>
        ) : !error ? (
          <div className="p-6">
            <Loader2 className="size-5 animate-spin text-ink-3" />
          </div>
        ) : null}
      </SheetContent>
    </Sheet>
  );
}

/** Browse messages for a time window or a search query. */
export function MessageBrowser({
  conversationId,
  query,
  onClose,
  colors,
}: {
  conversationId: string;
  query: { title: string; start?: string; end?: string; q?: string } | null;
  onClose: () => void;
  colors: Map<number, string>;
}) {
  const [msgs, setMsgs] = useState<Message[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setMsgs([]);
    setTotal(0);
    if (!query) return;
    setLoading(true);
    api
      .messages(conversationId, { start: query.start, end: query.end, q: query.q, limit: 200 })
      .then((r) => {
        setMsgs(r.messages);
        setTotal(r.total);
      })
      .finally(() => setLoading(false));
  }, [conversationId, query]);

  async function more() {
    if (!query) return;
    setLoading(true);
    const r = await api.messages(conversationId, { start: query.start, end: query.end, q: query.q, limit: 200, offset: msgs.length });
    setMsgs((m) => [...m, ...r.messages]);
    setLoading(false);
  }

  let lastDay = "";
  return (
    <Sheet open={query !== null} onOpenChange={(o) => !o && onClose()}>
      <SheetContent side="right" className="w-full gap-0 overflow-y-auto border-l border-rule bg-paper p-0 sm:max-w-[620px]" data-testid="message-browser">
        <SheetHeader className="border-b border-rule p-6 pb-5">
          <div className="kicker">{query?.q ? "Search" : "Reading"}</div>
          <SheetTitle className="display mt-2 text-[2rem] leading-[1.02]">{query?.title}</SheetTitle>
          <SheetDescription className="num font-mono text-[11px] text-ink-3">{total.toLocaleString()} messages</SheetDescription>
        </SheetHeader>
        <div className="space-y-1 p-6">
          {msgs.map((m) => {
            const day = m.ts.slice(0, 10);
            const header = day !== lastDay;
            lastDay = day;
            return (
              <div key={m.id}>
                {header ? <div className="kicker mt-5 mb-2 border-b border-rule pb-1">{fmtDate(day)}</div> : null}
                <div className="flex gap-3">
                  <span className="num w-10 shrink-0 pt-2.5 font-mono text-[10px] text-ink-3">{fmtTime(m.ts)}</span>
                  <div className="min-w-0 flex-1">
                    <MessageCitation m={m} tone="context" color={m.sender_id != null ? colors.get(m.sender_id) : undefined} />
                  </div>
                </div>
              </div>
            );
          })}
          {loading ? <Loader2 className="mt-4 size-5 animate-spin text-ink-3" /> : null}
          {!loading && msgs.length < total ? (
            <button type="button" className="pill-ghost mt-6" onClick={more}>
              Load more
            </button>
          ) : null}
          {!loading && total === 0 ? <p className="text-ink-3">No messages match.</p> : null}
        </div>
      </SheetContent>
    </Sheet>
  );
}
