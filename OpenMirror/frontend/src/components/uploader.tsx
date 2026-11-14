"use client";

import { ArrowRight, FileArchive, FileText, Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

const ORDERS = [
  { value: "auto", label: "Detect automatically" },
  { value: "DMY", label: "Day / month / year" },
  { value: "MDY", label: "Month / day / year" },
  { value: "YMD", label: "Year / month / day" },
];

export function Uploader({ onImported }: { onImported?: () => void }) {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [order, setOrder] = useState("auto");
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function pick(f: File | undefined | null) {
    setError(null);
    if (!f) return;
    if (!/\.(txt|zip)$/i.test(f.name)) {
      setError("Choose the .txt or .zip file produced by WhatsApp’s “Export chat”.");
      return;
    }
    setFile(f);
  }

  async function submit() {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      const res = await api.importFile(file, order);
      onImported?.();
      router.push(`/c/${res.conversation.id}`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "The import failed.");
      setBusy(false);
    }
  }

  const Icon = file?.name.toLowerCase().endsWith(".zip") ? FileArchive : FileText;

  return (
    <div className="w-full">
      <div
        role="button"
        tabIndex={0}
        aria-label="Choose a WhatsApp export file"
        data-testid="dropzone"
        onClick={() => input.current?.click()}
        onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && input.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          pick(e.dataTransfer.files?.[0]);
        }}
        className={cn(
          "group flex cursor-pointer items-center gap-4 rounded-full border border-rule bg-card py-2 pr-2 pl-6 transition-colors",
          "hover:border-ink-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-mark",
          over && "border-mark bg-highlight",
        )}
      >
        <Icon className="size-5 shrink-0 text-ink-3" aria-hidden />
        <div className="min-w-0 flex-1 text-left">
          {file ? (
            <>
              <div className="truncate text-[15px] font-semibold" data-testid="selected-file">
                {file.name}
              </div>
              <div className="num font-mono text-[11px] text-ink-3">{(file.size / 1024).toFixed(0)} KB · ready</div>
            </>
          ) : (
            <>
              <div className="text-[15px] font-semibold">Drop a WhatsApp export here</div>
              <div className="font-mono text-[11px] text-ink-3">.txt (Android) or .zip (iPhone) · stays on this computer</div>
            </>
          )}
        </div>
        <button
          type="button"
          className="pill shrink-0"
          disabled={!file || busy}
          onClick={(e) => {
            e.stopPropagation();
            submit();
          }}
          data-testid="analyze"
        >
          {busy ? <Loader2 className="size-4 animate-spin" /> : null}
          {busy ? "Reading" : "Analyse"}
          {!busy ? <ArrowRight className="size-4" /> : null}
        </button>
        <input
          ref={input}
          type="file"
          accept=".txt,.zip,text/plain,application/zip"
          className="sr-only"
          data-testid="file-input"
          onChange={(e) => pick(e.target.files?.[0])}
        />
      </div>

      <div className="mt-3 flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-[13px] text-ink-3">
        <label htmlFor="date-order" className="font-mono text-[11px] uppercase tracking-[0.14em]">
          Date format
        </label>
        <select
          id="date-order"
          value={order}
          onChange={(e) => setOrder(e.target.value)}
          className="rounded-full border border-rule bg-transparent px-3 py-1 text-[13px] text-ink-2 focus-visible:outline-2 focus-visible:outline-mark"
        >
          {ORDERS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>

      {error ? (
        <p role="alert" className="mt-4 text-center text-[14px] text-destructive" data-testid="upload-error">
          {error}
        </p>
      ) : null}
    </div>
  );
}
