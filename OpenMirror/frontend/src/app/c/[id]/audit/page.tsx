"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { Fragment, use, useEffect, useState } from "react";
import { api, ApiError, type ImportAudit } from "@/lib/api";
import { fmtInt } from "@/lib/format";

export default function AuditPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [audit, setAudit] = useState<ImportAudit | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    api.audit(id).then(setAudit).catch((e) => setError(e instanceof ApiError ? e.message : "Could not load the audit."));
  }, [id]);

  return (
    <main className="mx-auto max-w-[1000px] px-4 py-12 sm:px-6">
      <Link href={`/c/${id}`} className="kicker mb-10 inline-flex items-center gap-1.5 hover:text-ink">
        <ArrowLeft className="size-3" /> Back to the report
      </Link>
      <p className="kicker mb-4">Colophon</p>
      <h1 className="display mb-10 text-[clamp(2.6rem,7vw,5rem)]">Import audit</h1>
      {error ? <p className="text-destructive">{error}</p> : null}
      {audit ? (
        <>
          <dl className="num mb-12 grid grid-cols-2 gap-x-6 gap-y-6 border-y border-rule py-8 sm:grid-cols-4" data-testid="audit-stats">
            {[
              ["Lines read", audit.lines_total],
              ["Messages", audit.messages_parsed],
              ["Continuation lines", audit.continuation_lines],
              ["System notices", audit.system_messages],
              ["Issues", Object.values(audit.issue_counts).reduce((s, n) => s + n, 0)],
              ["Media files skipped", audit.archive_media_count],
              ["Undecodable bytes", audit.replacement_chars],
              ["File size (KB)", Math.round(audit.file_size / 1024)],
            ].map(([k, v]) => (
              <div key={k as string}>
                <dt className="kicker mb-1">{k}</dt>
                <dd className="display text-[2.4rem]">{fmtInt(v as number)}</dd>
              </div>
            ))}
          </dl>
          <dl className="mb-12 grid gap-x-8 gap-y-4 text-[15px] sm:grid-cols-[180px_1fr]">
            <dt className="kicker pt-1">File</dt>
            <dd>
              {audit.original_filename} <span className="font-mono text-[12px] text-ink-3">({audit.container})</span>
            </dd>
            <dt className="kicker pt-1">Encoding</dt>
            <dd>
              {audit.encoding} <span className="text-ink-3">— {audit.encoding_reason}</span>
            </dd>
            <dt className="kicker pt-1">Layout</dt>
            <dd>
              {audit.layout} <span className="text-ink-3">— {audit.layout_reason}</span>
            </dd>
            <dt className="kicker pt-1">Date order</dt>
            <dd>
              {audit.date_order}
              {audit.date_order_ambiguous ? <span className="ml-2 rounded-full bg-highlight px-2 py-0.5 font-mono text-[11px]">ambiguous</span> : null}
              <span className="text-ink-3"> — {audit.date_order_reason}</span>
            </dd>
            {audit.notes.map((n) => (
              <Fragment key={n}>
                <dt className="kicker pt-1">Note</dt>
                <dd>{n}</dd>
              </Fragment>
            ))}
          </dl>
          <h2 className="display mb-4 text-[2rem]">Issues</h2>
          {audit.issues.length === 0 ? (
            <p className="text-ink-2">None. Every line was attributed to a message without ambiguity.</p>
          ) : (
            <table className="w-full text-left text-[13px]">
              <thead>
                <tr className="border-b border-ink font-mono text-[10px] uppercase tracking-[0.12em] text-ink-3">
                  <th className="py-2 pr-4 font-normal">Line</th>
                  <th className="py-2 pr-4 font-normal">Kind</th>
                  <th className="py-2 font-normal">Detail</th>
                </tr>
              </thead>
              <tbody>
                {audit.issues.map((i, k) => (
                  <tr key={k} className="border-b border-rule align-top">
                    <td className="num py-2 pr-4 font-mono">{i.line_no || "—"}</td>
                    <td className="py-2 pr-4 font-mono text-[12px]">{i.kind.replaceAll("_", " ")}</td>
                    <td className="py-2">
                      {i.detail}
                      {i.excerpt ? <div className="mt-1 font-mono text-[11px] break-all text-ink-3">{i.excerpt}</div> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      ) : null}
    </main>
  );
}
