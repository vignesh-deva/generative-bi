"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  MessageSquareWarning,
  Sparkles,
  AlertTriangle,
  X,
} from "lucide-react";
import {
  fetchFeedback,
  promoteFeedback,
  type FeedbackItem,
  type FeedbackVote,
  type PromoteConflict,
} from "@/lib/api";

type PromoteState = {
  item: FeedbackItem;
  question: string;
  sql: string;
  conflict: PromoteConflict | null;
  submitting: boolean;
  error: string | null;
};

function similarityColor(sim: number): string {
  if (sim >= 0.8) return "bg-red-50 text-red-700 border-red-200";
  if (sim >= 0.5) return "bg-amber-50 text-amber-700 border-amber-200";
  return "bg-emerald-50 text-emerald-700 border-emerald-200";
}

export default function FeedbackPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FeedbackVote>("all");
  const [hideDuplicates, setHideDuplicates] = useState(true);
  const [flash, setFlash] = useState<string | null>(null);
  const [promote, setPromote] = useState<PromoteState | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchFeedback({
        vote: filter,
        hide_duplicates: hideDuplicates,
      });
      setItems(data);
    } catch (e) {
      console.error("Failed to load feedback:", e);
    } finally {
      setLoading(false);
    }
  }, [filter, hideDuplicates]);

  useEffect(() => {
    load();
  }, [load]);

  function openPromote(item: FeedbackItem) {
    setPromote({
      item,
      question: item.question,
      sql: item.sql_query ?? "",
      conflict: null,
      submitting: false,
      error: null,
    });
  }

  async function doPromote(force: boolean) {
    if (!promote) return;
    setPromote({ ...promote, submitting: true, error: null });
    try {
      await promoteFeedback(
        promote.item.message_id,
        promote.question,
        promote.sql,
        force
      );
      setPromote(null);
      setFlash("Promoted to RAG.");
      setTimeout(() => setFlash(null), 3500);
      load();
    } catch (e: unknown) {
      const err = e as Error & { conflict?: PromoteConflict };
      if (err?.conflict) {
        setPromote({
          ...promote,
          conflict: err.conflict,
          submitting: false,
          error: null,
        });
      } else {
        setPromote({
          ...promote,
          submitting: false,
          error: err?.message ?? "Failed to promote",
        });
      }
    }
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Feedback</h1>
        <p className="mt-0.5 text-sm text-[var(--text-muted)]">
          Review user ratings on AI responses and promote good ones into RAG
        </p>
      </div>

      {flash && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700">
          {flash}
        </div>
      )}

      {/* Controls row */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setFilter("all")}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            filter === "all"
              ? "bg-violet-100 text-violet-700"
              : "bg-white text-[var(--text-secondary)] hover:bg-slate-50"
          }`}
        >
          All
        </button>
        <button
          onClick={() => setFilter("up")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            filter === "up"
              ? "bg-green-50 text-green-700"
              : "bg-white text-[var(--text-secondary)] hover:bg-slate-50"
          }`}
        >
          <ThumbsUp size={12} /> Positive
        </button>
        <button
          onClick={() => setFilter("down")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            filter === "down"
              ? "bg-red-50 text-red-700"
              : "bg-white text-[var(--text-secondary)] hover:bg-slate-50"
          }`}
        >
          <ThumbsDown size={12} /> Negative
        </button>

        <label
          className="ml-auto flex items-center gap-2 rounded-lg border border-[var(--card-border)] bg-white px-3 py-1.5 text-xs text-[var(--text-secondary)]"
          title="Hides feedback whose NL question already matches an existing RAG example at >= 80% cosine similarity"
        >
          <input
            type="checkbox"
            checked={hideDuplicates}
            onChange={(e) => setHideDuplicates(e.target.checked)}
            className="accent-violet-600"
          />
          Hide likely duplicates (≥80%)
        </label>
      </div>

      {/* List */}
      {loading ? (
        <div className="flex h-40 items-center justify-center">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
            <MessageSquareWarning size={24} className="text-slate-400" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            {hideDuplicates
              ? "No new feedback to review. Toggle off 'Hide likely duplicates' to see everything."
              : "No feedback matches these filters."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {items.map((item) => (
            <div
              key={item.message_id}
              className="rounded-xl border border-[var(--card-border)] bg-white px-5 py-3.5 shadow-sm"
            >
              <div className="flex items-start gap-3">
                <div
                  className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
                    item.feedback === "up" ? "bg-green-50" : "bg-red-50"
                  }`}
                >
                  {item.feedback === "up" ? (
                    <ThumbsUp size={14} className="text-green-600" />
                  ) : (
                    <ThumbsDown size={14} className="text-red-600" />
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[var(--text-primary)]">
                    {item.question}
                  </p>
                  {item.sql_query && (
                    <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600">
                      <code>{item.sql_query}</code>
                    </pre>
                  )}
                  {item.feedback_comment && (
                    <p className="mt-2 rounded-md bg-slate-50 px-2 py-1.5 text-xs italic text-slate-600">
                      “{item.feedback_comment}”
                    </p>
                  )}
                  <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--text-muted)]">
                    <span>Session {item.session_id.slice(0, 8)}…</span>
                    <span>·</span>
                    <span>
                      {new Date(item.created_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </span>
                    <span
                      className={`rounded-full border px-2 py-0.5 text-[10px] font-medium ${similarityColor(
                        item.top_similarity
                      )}`}
                      title={
                        item.top_match_question
                          ? `Closest RAG example: ${item.top_match_question}`
                          : "No existing RAG examples to compare"
                      }
                    >
                      {Math.round(item.top_similarity * 100)}% similar
                    </span>
                    {item.promoted_at && (
                      <span className="rounded-full border border-violet-200 bg-violet-50 px-2 py-0.5 text-[10px] font-medium text-violet-700">
                        Promoted
                      </span>
                    )}
                  </div>
                </div>

                {!item.promoted_at && (
                  <button
                    onClick={() => openPromote(item)}
                    className="flex shrink-0 items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700"
                  >
                    <Sparkles size={12} /> Promote to RAG
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Promote modal */}
      {promote && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 p-4">
          <div className="w-full max-w-2xl rounded-xl border border-[var(--card-border)] bg-white shadow-xl">
            <div className="flex items-center justify-between border-b border-[var(--card-border)] px-5 py-3">
              <h2 className="text-sm font-semibold text-[var(--text-primary)]">
                Promote to RAG
              </h2>
              <button
                onClick={() => setPromote(null)}
                className="rounded-md p-1 text-[var(--text-muted)] hover:bg-slate-100"
              >
                <X size={16} />
              </button>
            </div>
            <div className="space-y-3 px-5 py-4">
              <div>
                <label className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                  Question
                </label>
                <textarea
                  value={promote.question}
                  onChange={(e) =>
                    setPromote({ ...promote, question: e.target.value, conflict: null })
                  }
                  rows={2}
                  className="mt-1 w-full rounded-lg border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm focus:border-violet-400 focus:ring-1 focus:ring-violet-400"
                />
              </div>
              <div>
                <label className="text-[11px] font-medium uppercase tracking-wide text-[var(--text-muted)]">
                  SQL
                </label>
                <textarea
                  value={promote.sql}
                  onChange={(e) =>
                    setPromote({ ...promote, sql: e.target.value })
                  }
                  rows={8}
                  className="mt-1 w-full resize-none rounded-lg border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 font-mono text-xs focus:border-violet-400 focus:ring-1 focus:ring-violet-400"
                />
              </div>

              {promote.conflict && (
                <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
                  <AlertTriangle size={14} className="mt-0.5 shrink-0" />
                  <div>
                    <p className="font-medium">
                      Near-duplicate of an existing example
                      ({Math.round(promote.conflict.similarity * 100)}% similar).
                    </p>
                    <p className="mt-1 italic">
                      “{promote.conflict.top_match.question}”
                    </p>
                    <p className="mt-1">
                      Edit the question to be more distinct, or promote anyway.
                    </p>
                  </div>
                </div>
              )}

              {promote.error && (
                <p className="text-xs text-red-600">{promote.error}</p>
              )}
            </div>
            <div className="flex justify-end gap-2 border-t border-[var(--card-border)] px-5 py-3">
              <button
                onClick={() => setPromote(null)}
                className="rounded-lg px-3 py-1.5 text-xs text-[var(--text-secondary)] hover:bg-slate-50"
              >
                Cancel
              </button>
              <button
                onClick={() => doPromote(promote.conflict != null)}
                disabled={
                  promote.submitting ||
                  !promote.question.trim() ||
                  !promote.sql.trim()
                }
                className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-50"
              >
                {promote.submitting
                  ? "Promoting…"
                  : promote.conflict
                  ? "Promote anyway"
                  : "Promote"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
