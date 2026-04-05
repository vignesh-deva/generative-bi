"use client";

import { useEffect, useState, FormEvent } from "react";
import {
  Plus,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  FileText,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { fetchRequests, createRequest } from "@/lib/api";

type DashboardRequest = {
  title: string;
  description: string | null;
  status: "Pending" | "In Progress" | "Done" | "Rejected";
  comments: { author: string; text: string; created_at: string }[];
  created_at: string;
  updated_at: string;
};

const STATUS_CONFIG: Record<
  string,
  { icon: typeof Clock; color: string; bg: string }
> = {
  Pending: { icon: Clock, color: "text-amber-600", bg: "bg-amber-50" },
  "In Progress": { icon: Loader2, color: "text-blue-600", bg: "bg-blue-50" },
  Done: { icon: CheckCircle2, color: "text-green-600", bg: "bg-green-50" },
  Rejected: { icon: XCircle, color: "text-red-600", bg: "bg-red-50" },
};

export default function RequestsPage() {
  const [requests, setRequests] = useState<DashboardRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function load() {
    try {
      const data = await fetchRequests<DashboardRequest[]>();
      setRequests(data);
    } catch (e) {
      console.error("Failed to load requests:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || submitting) return;
    setSubmitting(true);
    try {
      await createRequest(title.trim(), description.trim() || undefined);
      setTitle("");
      setDescription("");
      setShowForm(false);
      setLoading(true);
      await load();
    } catch (e) {
      console.error("Failed to create request:", e);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm text-[var(--text-muted)]">
            Loading requests...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            Requests
          </h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            Submit and track dashboard requests for the BI team
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          <Plus size={16} />
          New Request
        </button>
      </div>

      {/* Submit form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-[var(--card-border)] bg-white p-5 shadow-sm"
        >
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            New Dashboard Request
          </h2>
          <div className="mt-3 space-y-3">
            <input
              type="text"
              placeholder="Request title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full rounded-lg border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
            />
            <textarea
              placeholder="Describe what you need (optional)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full resize-none rounded-lg border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
            />
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={!title.trim() || submitting}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-40"
              >
                {submitting ? "Submitting..." : "Submit"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-lg border border-[var(--card-border)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--background)]"
              >
                Cancel
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Requests list */}
      {requests.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
            <FileText size={24} className="text-slate-400" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            No requests yet. Click &quot;New Request&quot; to submit one.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {requests.map((req) => {
            const cfg = STATUS_CONFIG[req.status] || STATUS_CONFIG.Pending;
            const Icon = cfg.icon;
            const isExpanded = expanded === req.title;
            return (
              <div
                key={req.title + req.created_at}
                className="rounded-xl border border-[var(--card-border)] bg-white shadow-sm transition-shadow hover:shadow-md"
              >
                <button
                  onClick={() =>
                    setExpanded(isExpanded ? null : req.title)
                  }
                  className="flex w-full items-center gap-4 px-5 py-3.5 text-left"
                >
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${cfg.bg}`}
                  >
                    <Icon size={16} className={cfg.color} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                      {req.title}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {new Date(req.created_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.color}`}
                  >
                    {req.status}
                  </span>
                  {isExpanded ? (
                    <ChevronUp size={16} className="text-[var(--text-muted)]" />
                  ) : (
                    <ChevronDown
                      size={16}
                      className="text-[var(--text-muted)]"
                    />
                  )}
                </button>
                {isExpanded && (
                  <div className="border-t border-[var(--card-border)] px-5 py-3.5">
                    {req.description && (
                      <p className="text-sm text-[var(--text-secondary)]">
                        {req.description}
                      </p>
                    )}
                    {req.comments.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs font-semibold uppercase text-[var(--text-muted)]">
                          Comments
                        </p>
                        {req.comments.map((c, i) => (
                          <div key={i} className="text-xs text-[var(--text-secondary)]">
                            <span className="font-medium">{c.author}:</span>{" "}
                            {c.text}
                          </div>
                        ))}
                      </div>
                    )}
                    {!req.description && req.comments.length === 0 && (
                      <p className="text-sm text-[var(--text-muted)]">
                        No description or comments yet.
                      </p>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
