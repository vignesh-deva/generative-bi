"use client";

import { useEffect, useState } from "react";
import {
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  Ticket,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { fetchTickets } from "@/lib/api";

type DashboardRequest = {
  request_id: string;
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

const STATUSES = ["Pending", "In Progress", "Done", "Rejected"] as const;

export default function TicketsPage() {
  const [tickets, setTickets] = useState<DashboardRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<string>("all");
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchTickets<DashboardRequest[]>();
        setTickets(data);
      } catch (e) {
        console.error("Failed to load tickets:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  const filtered =
    filter === "all" ? tickets : tickets.filter((t) => t.status === filter);

  const counts = tickets.reduce(
    (acc, t) => {
      acc[t.status] = (acc[t.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>
  );

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
          <p className="text-sm text-[var(--text-muted)]">Loading tickets...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[var(--text-primary)]">
          Tickets
        </h1>
        <p className="mt-0.5 text-sm text-[var(--text-muted)]">
          Dashboard requests from business users
        </p>
      </div>

      {/* Status filter tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setFilter("all")}
          className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
            filter === "all"
              ? "bg-violet-100 text-violet-700"
              : "bg-white text-[var(--text-secondary)] hover:bg-slate-50"
          }`}
        >
          All ({tickets.length})
        </button>
        {STATUSES.map((s) => {
          const cfg = STATUS_CONFIG[s];
          return (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                filter === s
                  ? `${cfg.bg} ${cfg.color}`
                  : "bg-white text-[var(--text-secondary)] hover:bg-slate-50"
              }`}
            >
              {s} ({counts[s] || 0})
            </button>
          );
        })}
      </div>

      {/* Tickets list */}
      {filtered.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
            <Ticket size={24} className="text-slate-400" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            {tickets.length === 0
              ? "No tickets yet. They appear here when users submit dashboard requests."
              : "No tickets match this filter."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((t) => {
            const cfg = STATUS_CONFIG[t.status] || STATUS_CONFIG.Pending;
            const Icon = cfg.icon;
            const isExpanded = expanded === t.request_id;
            return (
              <div
                key={t.request_id}
                className="rounded-xl border border-[var(--card-border)] bg-white shadow-sm transition-shadow hover:shadow-md"
              >
                <button
                  onClick={() => setExpanded(isExpanded ? null : t.request_id)}
                  className="flex w-full items-center gap-4 px-5 py-3.5 text-left"
                >
                  <div
                    className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg ${cfg.bg}`}
                  >
                    <Icon size={16} className={cfg.color} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                      {t.title}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {new Date(t.created_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.color}`}
                  >
                    {t.status}
                  </span>
                  {isExpanded ? (
                    <ChevronUp size={16} className="text-[var(--text-muted)]" />
                  ) : (
                    <ChevronDown size={16} className="text-[var(--text-muted)]" />
                  )}
                </button>
                {isExpanded && (
                  <div className="border-t border-[var(--card-border)] px-5 py-3.5">
                    {t.description && (
                      <p className="text-sm text-[var(--text-secondary)]">
                        {t.description}
                      </p>
                    )}
                    {t.comments.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <p className="text-xs font-semibold uppercase text-[var(--text-muted)]">
                          Comments
                        </p>
                        {t.comments.map((c, i) => (
                          <div
                            key={i}
                            className="text-xs text-[var(--text-secondary)]"
                          >
                            <span className="font-medium">{c.author}:</span>{" "}
                            {c.text}
                          </div>
                        ))}
                      </div>
                    )}
                    {!t.description && t.comments.length === 0 && (
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
