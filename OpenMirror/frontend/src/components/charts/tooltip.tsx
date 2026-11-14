"use client";

import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

interface TipState {
  x: number;
  y: number;
  content: ReactNode;
}

const Ctx = createContext<{ show: (e: { clientX: number; clientY: number }, c: ReactNode) => void; hide: () => void } | null>(
  null,
);

/** One shared tooltip layer for every chart on the page. */
export function TooltipLayer({ children }: { children: ReactNode }) {
  const [tip, setTip] = useState<TipState | null>(null);
  const show = useCallback((e: { clientX: number; clientY: number }, content: ReactNode) => {
    setTip({ x: e.clientX, y: e.clientY, content });
  }, []);
  const hide = useCallback(() => setTip(null), []);
  return (
    <Ctx.Provider value={{ show, hide }}>
      {children}
      {tip ? (
        <div
          role="tooltip"
          className="pointer-events-none fixed z-50 max-w-[260px] rounded-sm border border-rule bg-card px-3 py-2 text-[12px] leading-snug text-ink shadow-[0_6px_24px_rgba(0,0,0,0.12)]"
          style={{
            left: Math.min(tip.x + 14, (typeof window !== "undefined" ? window.innerWidth : 1200) - 280),
            top: tip.y + 14,
          }}
        >
          {tip.content}
        </div>
      ) : null}
    </Ctx.Provider>
  );
}

export function useTip() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useTip must be used inside <TooltipLayer>");
  return ctx;
}

export function TipRow({ color, label, value }: { color?: string; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="flex items-center gap-1.5 text-ink-2">
        {color ? <span className="inline-block size-2 rounded-[1px]" style={{ background: color }} /> : null}
        {label}
      </span>
      <span className="num font-mono">{value}</span>
    </div>
  );
}

export function Legend({ items }: { items: { label: string; color: string }[] }) {
  if (items.length < 2) return null;
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-ink-2" aria-label="Legend">
      {items.map((i) => (
        <li key={i.label} className="flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-[1px]" style={{ background: i.color }} aria-hidden />
          {i.label}
        </li>
      ))}
    </ul>
  );
}

export function Figure({
  title,
  caption,
  children,
  legend,
  action,
}: {
  title: string;
  caption?: string;
  children: ReactNode;
  legend?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <figure className="my-10">
      <div className="mb-3 flex flex-wrap items-end justify-between gap-3 border-t border-ink pt-3">
        <figcaption className="text-[15px] font-semibold">{title}</figcaption>
        <div className="flex items-center gap-4">
          {legend}
          {action}
        </div>
      </div>
      {children}
      {caption ? <p className="mt-2 font-mono text-[11px] leading-5 text-ink-3">{caption}</p> : null}
    </figure>
  );
}
