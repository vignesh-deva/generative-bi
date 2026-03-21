"use client";

import { useEffect, useState } from "react";
import { ThumbsUp, ThumbsDown, MessageSquareWarning } from "lucide-react";
import { fetchFeedback } from "@/lib/api";

type FeedbackItem = {
  session_id: string;
  role: string;
  content: string;
  sql_query: string | null;
  feedback: "up" | "down" | null;
  created_at: string;
};

export default function FeedbackPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<"all" | "up" | "down">("all");

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchFeedback<FeedbackItem[]>();
        setItems(data);
      } catch (e) {
        console.error("Failed to load feedback:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered =
    filter === "all" ? items : items.filter((i) => i.feedback === filter);

  const upCount = items.filter((i) => i.feedback === "up").length;
  const downCount = items.filter((i) => i.feedback === "down").length;

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
          <p className="text-sm text-[var(--text-muted)]">
            Loading feedback...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[var(--text-primary)]">
          Feedback
        </h1>
        <p className="mt-0.5 text-sm text-[var(--text-muted)]">
          User feedback on AI-generated responses
        </p>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilter("all")}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            filter === "all"
              ? "bg-violet-100 text-violet-700"
              : "bg-white text-[var(--text-secondary)] hover:bg-slate-50"
          }`}
        >
          All ({items.length})
        </button>
        <button
          onClick={() => setFilter("up")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            filter === "up"
              ? "bg-green-50 text-green-700"
              : "bg-white text-[var(--text-secondary)] hover:bg-slate-50"
          }`}
        >
          <ThumbsUp size={12} /> Positive ({upCount})
        </button>
        <button
          onClick={() => setFilter("down")}
          className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            filter === "down"
              ? "bg-red-50 text-red-700"
              : "bg-white text-[var(--text-secondary)] hover:bg-slate-50"
          }`}
        >
          <ThumbsDown size={12} /> Negative ({downCount})
        </button>
      </div>

      {/* Feedback list */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
            <MessageSquareWarning size={24} className="text-slate-400" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            {items.length === 0
              ? "No feedback yet. It appears here when users rate chat responses."
              : "No feedback matches this filter."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((item, idx) => (
            <div
              key={idx}
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
                  <p className="text-sm text-[var(--text-primary)]">
                    {item.content}
                  </p>
                  {item.sql_query && (
                    <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600">
                      <code>{item.sql_query}</code>
                    </pre>
                  )}
                  <p className="mt-2 text-xs text-[var(--text-muted)]">
                    Session: {item.session_id.slice(0, 8)}... &middot;{" "}
                    {new Date(item.created_at).toLocaleDateString("en-IN", {
                      day: "numeric",
                      month: "short",
                      year: "numeric",
                    })}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
