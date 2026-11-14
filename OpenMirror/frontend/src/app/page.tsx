"use client";

import { ArrowUpRight, Trash2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { Uploader } from "@/components/uploader";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { api, ApiError, type Conversation } from "@/lib/api";
import { fmtDate, fmtInt } from "@/lib/format";

// Decorative, entirely fictional fragments that drift around the hero.
const FRAGMENTS = [
  { t: "did you book the tickets?", x: "6%", y: "18%", r: -6 },
  { t: "on my way 🚲", x: "78%", y: "12%", r: 5 },
  { t: "haha same", x: "14%", y: "62%", r: 4 },
  { t: "call me when you’re free", x: "72%", y: "58%", r: -4 },
  { t: "image omitted", x: "86%", y: "34%", r: 8, muted: true },
  { t: "sorry, just saw this", x: "3%", y: "40%", r: -3 },
  { t: "who’s bringing snacks?", x: "60%", y: "80%", r: 3 },
  { t: "reached", x: "24%", y: "84%", r: -7 },
];

export default function Home() {
  const [items, setItems] = useState<Conversation[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<Conversation | null>(null);

  const load = useCallback(() => {
    api
      .conversations()
      .then((c) => {
        setItems(c);
        setError(null);
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load conversations."));
  }, []);

  useEffect(load, [load]);

  async function confirmDelete() {
    if (!pending) return;
    await api.remove(pending.id);
    setPending(null);
    load();
  }

  return (
    <main>
      {/* Hero */}
      <section className="relative overflow-hidden border-b border-rule">
        <div aria-hidden className="pointer-events-none absolute inset-0 hidden md:block">
          {FRAGMENTS.map((f, i) => (
            <span
              key={i}
              className="om-float absolute rounded-[14px] border border-rule bg-card px-3 py-1.5 text-[13px] text-ink-3 shadow-[0_1px_0_rgba(0,0,0,0.03)]"
              style={{
                left: f.x,
                top: f.y,
                rotate: `${f.r}deg`,
                opacity: f.muted ? 0.45 : 0.75,
                animationDelay: `${i * -1.7}s`,
              }}
            >
              {f.t}
            </span>
          ))}
        </div>
        <div className="relative mx-auto flex max-w-[860px] flex-col items-center px-4 pt-24 pb-20 text-center sm:pt-32 sm:pb-28">
          <p className="kicker mb-6">Your conversation, decoded</p>
          <h1 className="display text-[clamp(2.6rem,7vw,5rem)]">
            The story behind the messages.
            <span className="mt-1 block text-ink-3">With receipts.</span>
          </h1>
          <p className="mt-7 max-w-[560px] text-[17px] leading-relaxed text-ink-2">
            Drop in a WhatsApp export. OpenMirror reads every message on this computer and writes a chaptered
            report where every claim links to the exact messages behind it, counterexamples included.
          </p>
          <div className="mt-10 w-full max-w-[620px]">
            <Uploader onImported={load} />
          </div>
        </div>
      </section>

      {/* Library */}
      <section className="mx-auto max-w-[1240px] px-4 py-16 sm:px-6">
        <div className="mb-8 flex items-baseline justify-between gap-4">
          <h2 className="display text-[2.2rem]">Your reports</h2>
          <span className="kicker">{items ? `${items.length} on this device` : ""}</span>
        </div>
        {error ? (
          <p role="alert" className="rounded-sm border border-rule bg-card p-5 text-[15px] text-ink-2">
            {error}
          </p>
        ) : items === null ? (
          <p className="kicker">Loading…</p>
        ) : items.length === 0 ? (
          <p className="max-w-[520px] text-[16px] text-ink-3">
            Nothing here yet. Try one of the fictional samples in <code className="font-mono text-[13px]">samples/</code>{" "}
            before using a real export.
          </p>
        ) : (
          <ul className="divide-y divide-rule border-y border-rule" data-testid="conversation-list">
            {items.map((c) => (
              <li key={c.id} className="group flex items-center gap-4 py-4">
                <Link
                  href={`/c/${c.id}`}
                  className="display min-w-0 flex-1 truncate text-[clamp(1.8rem,4.4vw,3.4rem)] text-ink-3 transition-colors group-hover:text-ink focus-visible:text-ink focus-visible:outline-none"
                >
                  {c.title}
                </Link>
                <div className="hidden shrink-0 text-right font-mono text-[11px] uppercase leading-5 tracking-[0.12em] text-ink-3 sm:block">
                  <div className="num">{fmtInt(c.message_count)} messages · {c.participant_count} people</div>
                  <div className="num">
                    {c.first_ts ? fmtDate(c.first_ts) : "—"} → {c.last_ts ? fmtDate(c.last_ts) : "—"}
                  </div>
                </div>
                <Link
                  href={`/c/${c.id}`}
                  aria-label={`Open report for ${c.title}`}
                  className="hidden size-10 items-center justify-center rounded-full bg-secondary text-ink sm:inline-flex"
                >
                  <ArrowUpRight className="size-4" />
                </Link>
                <button
                  type="button"
                  onClick={() => setPending(c)}
                  aria-label={`Delete ${c.title}`}
                  data-testid="delete-conversation"
                  className="inline-flex size-10 items-center justify-center rounded-full text-ink-3 hover:bg-secondary hover:text-destructive"
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Principles */}
      <section className="border-t border-rule">
        <div className="mx-auto grid max-w-[1240px] gap-10 px-4 py-16 sm:px-6 md:grid-cols-3">
          {[
            ["01", "Stays here", "Runs on 127.0.0.1. No account, no upload, no tracking. Delete a chat and every message, statistic and finding goes with it."],
            ["02", "Shows its work", "Each finding states its method and confidence and opens the actual messages behind it, including the ones that argue against it."],
            ["03", "Facts before feelings", "It measures who writes, when, how much and how fast. It doesn’t guess at motives or hand out red flags."],
          ].map(([n, t, d]) => (
            <div key={n}>
              <div className="kicker mb-3">{n}</div>
              <h3 className="display mb-3 text-[1.6rem]">{t}</h3>
              <p className="text-[15px] leading-relaxed text-ink-2">{d}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-rule">
        <div className="mx-auto flex max-w-[1240px] flex-wrap justify-between gap-2 px-4 py-6 font-mono text-[11px] uppercase tracking-[0.12em] text-ink-3 sm:px-6">
          <span>OpenMirror · MIT · open source</span>
          <span>Your conversations never leave this device</span>
        </div>
      </footer>

      <AlertDialog open={pending !== null} onOpenChange={(o) => !o && setPending(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete “{pending?.title}”?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently removes the imported messages, participants, analysis, findings and import audit from this
              computer. Your original export file is not touched.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction onClick={confirmDelete} data-testid="confirm-delete" className="bg-destructive text-white hover:bg-destructive/90">
              Delete everything
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </main>
  );
}
