// Typed client for the local OpenMirror API. All requests go to the loopback
// backend; nothing is sent to any third party.

export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export interface Participant {
  id: number;
  display_name: string;
  message_count: number;
}

export interface Conversation {
  id: string;
  title: string;
  source_platform: string;
  source_layout: string | null;
  imported_at: string;
  status: string;
  message_count: number;
  participant_count: number;
  first_ts: string | null;
  last_ts: string | null;
  participants?: Participant[];
}

export interface Message {
  id: number;
  seq: number;
  sender_id: number | null;
  sender: string | null;
  ts_original: string;
  ts: string;
  text: string;
  message_type: string;
  media_kind: string | null;
  is_edited: boolean;
  line_start: number;
  line_end: number;
}

export interface EvidenceRef {
  message_id: number;
  role: "support" | "counterexample";
  note: string | null;
}

export type Confidence = "high" | "medium" | "low";

export interface Finding {
  id: string;
  chapter: string;
  finding_type: string;
  title: string;
  statement: string;
  method: string;
  confidence: Confidence;
  confidence_reason: string;
  metrics: Record<string, unknown>;
  counterexample_note: string | null;
  time_start: string | null;
  time_end: string | null;
  evidence: EvidenceRef[];
}

export interface FindingDetail extends Omit<Finding, "evidence"> {
  evidence: { role: "support" | "counterexample"; note: string | null; message: Message }[];
}

export interface Chapter {
  key: string;
  number: string;
  title: string;
  question: string;
  paragraphs: string[];
  figures: string[];
  finding_ids: string[];
}

export interface Report {
  title: string;
  subtitle: string;
  generated_at: string;
  engine_version: string;
  ai_used: boolean;
  participants: { id: number; name: string; messages: number }[];
  headline: { label: string; value: string }[];
  chapters: Chapter[];
  findings: Finding[];
  disclaimer: string;
}

export interface SeriesRow {
  total: number;
  by: Record<string, number>;
  [key: string]: unknown;
}

export interface PersonStats {
  id: number;
  name: string;
  messages: number;
  share: number;
  text_messages: number;
  words: number;
  mean_words: number;
  median_words: number;
  media: number;
  deleted: number;
  edited: number;
  questions: number;
  links: number;
  emoji_total: number;
  top_emojis: { emoji: string; count: number }[];
  hour_histogram: number[];
  peak_hour: number;
  late_night_share: number;
  sessions_initiated: number;
  initiation_share: number;
  turns: number;
  messages_per_turn: number;
  longest_burst: number;
  replies: number;
  reply_median_s: number | null;
  reply_p25_s: number | null;
  reply_p75_s: number | null;
  reply_p90_s: number | null;
}

export interface Period {
  label: string;
  start: string;
  end: string;
  messages: number;
  messages_per_day: number;
  sessions: number;
  by: Record<string, { messages: number; share: number; initiated: number; initiation_share: number; reply_median_s: number | null; replies: number }>;
}

export interface Analytics {
  engine_version: string;
  params: { session_gap_minutes: number; late_night_start_hour: number; late_night_end_hour: number };
  empty?: boolean;
  overview: {
    total_messages: number;
    participant_messages: number;
    system_messages: number;
    by_type: Record<string, number>;
    span_days: number;
    active_days: number;
    active_day_share: number;
    messages_per_active_day: number;
    first_ts: string;
    last_ts: string;
    sessions: number;
  };
  participants: PersonStats[];
  activity: {
    daily: (SeriesRow & { day: string })[];
    weekly: (SeriesRow & { week: string })[];
    monthly: (SeriesRow & { month: string })[];
    weekday_hour: { weekdays: string[]; grid: number[][] };
    hour_of_day: number[];
  };
  length_distribution: { participant_id: number; buckets: { bucket: string; n: number }[] }[];
  reply_times: { participant_id: number; n: number; buckets: { bucket: string; n: number }[] }[];
  sessions: {
    count: number;
    gap_threshold_minutes: number;
    median_messages: number | null;
    median_duration_s: number | null;
    initiation_by_month: (SeriesRow & { month: string })[];
  };
  streaks: { longest: { start: string; end: string; days: number }[]; count: number };
  participation_by_month: { month: string; total: number; share: Record<string, number> }[];
  periods: Period[];
  volume_changes: { month: string; messages: number; trailing_mean: number; relative_change: number | null; direction: "up" | "down" }[];
  topics: {
    method: string;
    total_sessions: number;
    terms: { term: string; messages: number; sessions: number; session_share: number; by: Record<string, number>; first_ts: string; last_ts: string; by_period: number[] }[];
    distinctive_by_period: { term: string; z: number; in_period: number; elsewhere: number }[][];
  };
  definitions: Record<string, string>;
}

export interface ImportAudit {
  id: string;
  original_filename: string;
  container: string;
  file_size: number;
  encoding: string;
  encoding_reason: string;
  replacement_chars: number;
  layout: string;
  layout_reason: string;
  date_order: string;
  date_order_reason: string;
  date_order_ambiguous: boolean;
  lines_total: number;
  header_lines: number;
  continuation_lines: number;
  messages_parsed: number;
  system_messages: number;
  archive_media_count: number;
  issue_counts: Record<string, number>;
  notes: string[];
  started_at: string;
  finished_at: string;
  issues: { line_no: number; kind: string; detail: string; excerpt: string | null }[];
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...init, cache: "no-store" });
  } catch {
    throw new ApiError(0, `Cannot reach the local OpenMirror server at ${API_BASE}. Is the backend running?`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* keep status text */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; version: string; max_upload_mb: number }>("/api/health"),
  conversations: () => request<Conversation[]>("/api/conversations"),
  conversation: (id: string) => request<Conversation>(`/api/conversations/${id}`),
  importFile: (file: File, dateOrder: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("date_order", dateOrder);
    return request<{ conversation: Conversation; import_job_id: string }>("/api/imports", { method: "POST", body: form });
  },
  remove: (id: string) => request<void>(`/api/conversations/${id}`, { method: "DELETE" }),
  report: (id: string) =>
    request<{ analysis_run_id: string; created_at: string; report: Report; analytics: Analytics }>(`/api/conversations/${id}/report`),
  reanalyze: (id: string, sessionGapMinutes: number) =>
    request<{ analysis_run_id: string }>(`/api/conversations/${id}/analyze`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ session_gap_minutes: sessionGapMinutes }),
    }),
  finding: (id: string, findingId: string) => request<FindingDetail>(`/api/conversations/${id}/findings/${encodeURIComponent(findingId)}`),
  audit: (id: string) => request<ImportAudit>(`/api/conversations/${id}/import`),
  messages: (id: string, params: Record<string, string | number | undefined>) => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(params)) if (v !== undefined && v !== "") qs.set(k, String(v));
    return request<{ messages: Message[]; total: number; focus_id?: number }>(`/api/conversations/${id}/messages?${qs}`);
  },
};
