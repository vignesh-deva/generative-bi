"use client";

import { useEffect, useState } from "react";
import {
  Clock,
  Loader2,
  CheckCircle2,
  CheckCheck,
  Ticket,
  ChevronDown,
  ChevronUp,
  HelpCircle,
  RotateCcw,
  Archive,
  AlertCircle,
  MessageSquare,
  Play,
  Pause,
} from "lucide-react";
import {
  fetchTickets,
  updateTicketStatus,
  addTicketComment,
  type DashboardRequest,
  type RequestStatus,
} from "@/lib/api";

type TabKey = "all" | RequestStatus;

const STATUS_CONFIG: Record<
  RequestStatus,
  { label: string; icon: typeof Clock; color: string; bg: string }
> = {
  draft: { label: "Draft", icon: Clock, color: "text-slate-600", bg: "bg-slate-100" },
  requested: { label: "Requested", icon: Clock, color: "text-amber-600", bg: "bg-amber-50" },
  "in-progress": { label: "In Progress", icon: Loader2, color: "text-blue-600", bg: "bg-blue-50" },
  "need additional details": {
    label: "Need Details",
    icon: HelpCircle,
    color: "text-orange-600",
    bg: "bg-orange-50",
  },
  completed: { label: "Completed", icon: CheckCheck, color: "text-teal-600", bg: "bg-teal-50" },
  accepted: { label: "Accepted", icon: CheckCircle2, color: "text-green-600", bg: "bg-green-50" },
  "request changes": {
    label: "Changes Requested",
    icon: RotateCcw,
    color: "text-purple-600",
    bg: "bg-purple-50",
  },
  closed: { label: "Closed", icon: Archive, color: "text-slate-500", bg: "bg-slate-50" },
};

const TAB_STATUSES: RequestStatus[] = [
  "requested",
  "in-progress",
  "need additional details",
  "completed",
  "accepted",
  "request changes",
  "closed",
];

// Ops-allowed transitions by current status → list of {label, target}
const OPS_ACTIONS: Record<string, { label: string; target: RequestStatus; icon: typeof Play }[]> = {
  requested: [
    { label: "Start", target: "in-progress", icon: Play },
    { label: "Need Details", target: "need additional details", icon: HelpCircle },
  ],
  "in-progress": [
    { label: "Complete", target: "completed", icon: CheckCheck },
    { label: "Need Details", target: "need additional details", icon: HelpCircle },
  ],
  "need additional details": [
    { label: "Resume", target: "in-progress", icon: Play },
  ],
  "request changes": [
    { label: "Resume", target: "in-progress", icon: Play },
    { label: "Need Details", target: "need additional details", icon: HelpCircle },
  ],
};

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function TicketsPage() {
  const [tickets, setTickets] = useState<DashboardRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<TabKey>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [transitionComment, setTransitionComment] = useState<Record<string, string>>({});
  const [newComment, setNewComment] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  async function load() {
    try {
      const data = await fetchTickets();
      setTickets(data);
    } catch (e) {
      console.error("Failed to load tickets:", e);
      setStatusMessage({ kind: "err", text: (e as Error).message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function flash(kind: "ok" | "err", text: string) {
    setStatusMessage({ kind, text });
    setTimeout(() => setStatusMessage(null), 4000);
  }

  const filtered =
    filter === "all" ? tickets : tickets.filter((t) => t.status === filter);

  const counts = tickets.reduce(
    (acc, t) => {
      acc[t.status] = (acc[t.status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  async function handleTransition(id: string, target: RequestStatus) {
    const comment = (transitionComment[id] ?? "").trim();
    setBusy(true);
    try {
      await updateTicketStatus(id, target, comment || undefined);
      setTransitionComment((prev) => ({ ...prev, [id]: "" }));
      await load();
      flash("ok", `Status: ${target}`);
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAddComment(id: string) {
    const text = (newComment[id] ?? "").trim();
    if (!text) return;
    setBusy(true);
    try {
      await addTicketComment(id, text);
      setNewComment((prev) => ({ ...prev, [id]: "" }));
      await load();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

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
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Tickets</h1>
        <p className="mt-0.5 text-sm text-[var(--text-muted)]">
          Dashboard requests from business users
        </p>
      </div>

      {statusMessage && (
        <div
          className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-sm ${
            statusMessage.kind === "ok"
              ? "border-green-200 bg-green-50 text-green-700"
              : "border-red-200 bg-red-50 text-red-700"
          }`}
        >
          <AlertCircle size={14} />
          {statusMessage.text}
        </div>
      )}

      {/* Tabs */}
      <div className="flex flex-wrap gap-2">
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
        {TAB_STATUSES.map((s) => {
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
              {cfg.label} ({counts[s] || 0})
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
            const cfg = STATUS_CONFIG[t.status];
            const Icon = cfg.icon;
            const isExpanded = expandedId === t.request_id;
            const actions = OPS_ACTIONS[t.status] ?? [];
            return (
              <div
                key={t.request_id}
                className="rounded-xl border border-[var(--card-border)] bg-white shadow-sm transition-shadow hover:shadow-md"
              >
                <button
                  onClick={() => setExpandedId(isExpanded ? null : t.request_id)}
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
                      {formatDate(t.created_at)}
                      {t.chat_context ? " · from chat" : ""}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${cfg.bg} ${cfg.color}`}
                  >
                    {cfg.label}
                  </span>
                  {isExpanded ? (
                    <ChevronUp size={16} className="text-[var(--text-muted)]" />
                  ) : (
                    <ChevronDown size={16} className="text-[var(--text-muted)]" />
                  )}
                </button>

                {isExpanded && (
                  <div className="border-t border-[var(--card-border)] px-5 py-4 space-y-4">
                    <p className="whitespace-pre-wrap text-sm text-[var(--text-secondary)]">
                      {t.description}
                    </p>

                    {t.chat_context && <ChatContextBlock context={t.chat_context} />}

                    {t.comments.length > 0 && (
                      <div className="space-y-2">
                        <p className="text-xs font-semibold uppercase text-[var(--text-muted)]">
                          Activity
                        </p>
                        <div className="space-y-1.5">
                          {t.comments.map((c) => (
                            <div
                              key={c.comment_id}
                              className={`text-xs ${
                                c.type === "status_change"
                                  ? "text-[var(--text-muted)] italic"
                                  : "text-[var(--text-secondary)]"
                              }`}
                            >
                              <span className="font-medium">{c.author}:</span> {c.text}
                              <span className="ml-2 text-[10px] text-slate-400">
                                {formatDate(c.created_at)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {t.status !== "closed" && (
                      <div className="space-y-2 pt-2 border-t border-[var(--card-border)]">
                        <div className="flex gap-2">
                          <input
                            type="text"
                            placeholder="Add a comment..."
                            value={newComment[t.request_id] ?? ""}
                            onChange={(e) =>
                              setNewComment((prev) => ({
                                ...prev,
                                [t.request_id]: e.target.value,
                              }))
                            }
                            className="flex-1 rounded-lg border border-[var(--card-border)] bg-white px-3 py-1.5 text-xs text-[var(--text-primary)] outline-none focus:border-violet-400 focus:ring-1 focus:ring-violet-400"
                          />
                          <button
                            onClick={() => handleAddComment(t.request_id)}
                            disabled={busy || !(newComment[t.request_id] ?? "").trim()}
                            className="flex items-center gap-1.5 rounded-lg bg-slate-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-40"
                          >
                            <MessageSquare size={12} /> Send
                          </button>
                        </div>

                        {actions.length > 0 && (
                          <div className="space-y-2 rounded-lg border border-violet-200 bg-violet-50/40 p-3">
                            <input
                              type="text"
                              placeholder="Optional note for the status change..."
                              value={transitionComment[t.request_id] ?? ""}
                              onChange={(e) =>
                                setTransitionComment((prev) => ({
                                  ...prev,
                                  [t.request_id]: e.target.value,
                                }))
                              }
                              className="w-full rounded-lg border border-[var(--card-border)] bg-white px-3 py-1.5 text-xs text-[var(--text-primary)] outline-none focus:border-violet-400 focus:ring-1 focus:ring-violet-400"
                            />
                            <div className="flex flex-wrap gap-2">
                              {actions.map((a) => {
                                const ActionIcon = a.icon;
                                return (
                                  <button
                                    key={a.target}
                                    onClick={() => handleTransition(t.request_id, a.target)}
                                    disabled={busy}
                                    className="flex items-center gap-1.5 rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-violet-700 disabled:opacity-40"
                                  >
                                    <ActionIcon size={12} /> {a.label}
                                  </button>
                                );
                              })}
                            </div>
                          </div>
                        )}

                        {actions.length === 0 && (
                          <p className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] italic">
                            <Pause size={12} /> Waiting on user response.
                          </p>
                        )}
                      </div>
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

// ── Chat context block ─────────────────────────────────────────

function ChatContextBlock({
  context,
}: {
  context: NonNullable<DashboardRequest["chat_context"]>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/40">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-blue-700"
      >
        {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        <MessageSquare size={12} />
        Chat context ({context.history.length} recent messages)
      </button>
      {open && (
        <div className="space-y-2 border-t border-blue-200 px-3 py-2 text-xs text-[var(--text-secondary)]">
          <div>
            <span className="font-semibold text-blue-700">Question: </span>
            {context.question}
          </div>
          <div>
            <span className="font-semibold text-blue-700">Answer: </span>
            <span className="whitespace-pre-wrap">{context.answer}</span>
          </div>
          {context.sql && (
            <div>
              <span className="font-semibold text-blue-700">SQL:</span>
              <pre className="mt-1 overflow-x-auto rounded bg-slate-900 p-2 text-[11px] text-slate-300">
                <code>{context.sql}</code>
              </pre>
            </div>
          )}
          {context.history.length > 0 && (
            <div>
              <p className="font-semibold text-blue-700">Recent history:</p>
              <ul className="mt-1 space-y-1">
                {context.history.map((m, i) => (
                  <li key={i} className="text-[11px]">
                    <span className="font-medium capitalize">{m.role}:</span>{" "}
                    <span className="text-[var(--text-muted)]">{m.content}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
