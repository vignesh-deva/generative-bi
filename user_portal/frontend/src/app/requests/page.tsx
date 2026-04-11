"use client";

import { useEffect, useState } from "react";
import {
  Plus,
  Clock,
  Loader2,
  CheckCircle2,
  XCircle,
  FileText,
  ChevronDown,
  ChevronUp,
  Pencil,
  Trash2,
  Send,
  MessageSquare,
  AlertCircle,
  CheckCheck,
  RotateCcw,
  HelpCircle,
  Archive,
} from "lucide-react";
import {
  fetchRequests,
  createDraft,
  updateDraft,
  deleteDraft,
  submitDraft,
  addRequestComment,
  acceptRequest,
  requestChanges,
  closeRequest,
  type DashboardRequest,
  type RequestStatus,
} from "@/lib/api";
import RequestForm from "./RequestForm";

type TabKey = "drafts" | "active" | "closed";

const STATUS_CONFIG: Record<
  RequestStatus,
  { label: string; icon: typeof Clock; color: string; bg: string }
> = {
  draft: { label: "Draft", icon: Pencil, color: "text-slate-600", bg: "bg-slate-100" },
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

const ACTIVE_STATUSES: RequestStatus[] = [
  "requested",
  "in-progress",
  "need additional details",
  "completed",
  "accepted",
  "request changes",
];

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export default function RequestsPage() {
  const [requests, setRequests] = useState<DashboardRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabKey>("active");
  const [showNewForm, setShowNewForm] = useState(false);
  const [editingDraftId, setEditingDraftId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [newComment, setNewComment] = useState<Record<string, string>>({});
  const [changeNote, setChangeNote] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{
    kind: "ok" | "err";
    text: string;
  } | null>(null);

  async function load() {
    try {
      const data = await fetchRequests();
      setRequests(data);
    } catch (e) {
      console.error("Failed to load requests:", e);
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

  const drafts = requests.filter((r) => r.status === "draft");
  const active = requests.filter((r) => ACTIVE_STATUSES.includes(r.status));
  const closed = requests.filter((r) => r.status === "closed");
  const tabs: { key: TabKey; label: string; count: number }[] = [
    { key: "drafts", label: "Drafts", count: drafts.length },
    { key: "active", label: "Active", count: active.length },
    { key: "closed", label: "Closed", count: closed.length },
  ];

  const visible =
    activeTab === "drafts" ? drafts : activeTab === "active" ? active : closed;

  // ── Draft actions ─────────────────────────────────────────────

  async function handleCreateDraft(data: { title: string; description: string }) {
    setBusy(true);
    try {
      await createDraft(data);
      setShowNewForm(false);
      await load();
      setActiveTab("drafts");
      flash("ok", "Draft saved.");
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleCreateAndSubmit(data: { title: string; description: string }) {
    setBusy(true);
    try {
      // Create draft then submit, matching one-shot semantics via the one-shot endpoint
      const { createRequest } = await import("@/lib/api");
      await createRequest(data);
      setShowNewForm(false);
      await load();
      setActiveTab("active");
      flash("ok", "Request submitted.");
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleUpdateDraft(
    id: string,
    data: { title: string; description: string },
  ) {
    setBusy(true);
    try {
      await updateDraft(id, data);
      setEditingDraftId(null);
      await load();
      flash("ok", "Draft updated.");
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSubmitDraft(id: string) {
    setBusy(true);
    try {
      await submitDraft(id);
      await load();
      setActiveTab("active");
      flash("ok", "Draft submitted.");
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleDeleteDraft(id: string) {
    if (!window.confirm("Delete this draft?")) return;
    setBusy(true);
    try {
      await deleteDraft(id);
      await load();
      flash("ok", "Draft deleted.");
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  // ── Comments & transitions ────────────────────────────────────

  async function handleAddComment(id: string) {
    const text = (newComment[id] ?? "").trim();
    if (!text) return;
    setBusy(true);
    try {
      await addRequestComment(id, text);
      setNewComment((prev) => ({ ...prev, [id]: "" }));
      await load();
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleAccept(id: string) {
    setBusy(true);
    try {
      await acceptRequest(id);
      await load();
      flash("ok", "Request accepted.");
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleRequestChanges(id: string) {
    const note = (changeNote[id] ?? "").trim();
    if (!note) {
      flash("err", "Please describe what needs to change.");
      return;
    }
    setBusy(true);
    try {
      await requestChanges(id, note);
      setChangeNote((prev) => ({ ...prev, [id]: "" }));
      await load();
      flash("ok", "Changes requested.");
    } catch (e) {
      flash("err", (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleClose(id: string) {
    if (!window.confirm("Close this request?")) return;
    setBusy(true);
    try {
      await closeRequest(id);
      await load();
      flash("ok", "Request closed.");
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
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm text-[var(--text-muted)]">Loading requests...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">Requests</h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            Submit and track dashboard requests for the BI team
          </p>
        </div>
        <button
          onClick={() => {
            setShowNewForm(!showNewForm);
            setEditingDraftId(null);
          }}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
        >
          <Plus size={16} />
          New Request
        </button>
      </div>

      {/* Status message */}
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

      {/* New-request form */}
      {showNewForm && (
        <div className="rounded-xl border border-[var(--card-border)] bg-white p-5 shadow-sm">
          <RequestForm
            mode="create"
            onSubmit={handleCreateAndSubmit}
            onSaveDraft={handleCreateDraft}
            onCancel={() => setShowNewForm(false)}
            busy={busy}
          />
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-[var(--card-border)]">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`-mb-px border-b-2 px-3 py-2 text-sm font-medium transition-colors ${
              activeTab === tab.key
                ? "border-blue-600 text-blue-600"
                : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/* List */}
      {visible.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
            <FileText size={24} className="text-slate-400" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            {activeTab === "drafts"
              ? "No drafts yet. Click \"New Request\" and save as draft to keep working on it later."
              : activeTab === "active"
              ? "No active requests. Click \"New Request\" to submit one."
              : "No closed requests yet."}
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {visible.map((req) => {
            const cfg = STATUS_CONFIG[req.status];
            const Icon = cfg.icon;
            const isExpanded = expandedId === req.request_id;
            const isEditing = editingDraftId === req.request_id;

            return (
              <div
                key={req.request_id}
                className="rounded-xl border border-[var(--card-border)] bg-white shadow-sm transition-shadow hover:shadow-md"
              >
                <button
                  onClick={() =>
                    setExpandedId(isExpanded ? null : req.request_id)
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
                      {formatDate(req.created_at)}
                      {req.chat_context ? " · attached from chat" : ""}
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
                    {isEditing ? (
                      <RequestForm
                        mode="edit"
                        initial={{
                          title: req.title,
                          description: req.description,
                        }}
                        showSaveDraft={false}
                        onSubmit={(data) =>
                          handleUpdateDraft(req.request_id, data)
                        }
                        onCancel={() => setEditingDraftId(null)}
                        busy={busy}
                      />
                    ) : (
                      <>
                        <p className="whitespace-pre-wrap text-sm text-[var(--text-secondary)]">
                          {req.description}
                        </p>

                        {req.chat_context && (
                          <ChatContextBlock context={req.chat_context} />
                        )}

                        {/* Comments feed */}
                        {req.comments.length > 0 && (
                          <div className="space-y-2">
                            <p className="text-xs font-semibold uppercase text-[var(--text-muted)]">
                              Activity
                            </p>
                            <div className="space-y-1.5">
                              {req.comments.map((c) => (
                                <div
                                  key={c.comment_id}
                                  className={`text-xs ${
                                    c.type === "status_change"
                                      ? "text-[var(--text-muted)] italic"
                                      : "text-[var(--text-secondary)]"
                                  }`}
                                >
                                  <span className="font-medium">{c.author}:</span>{" "}
                                  {c.text}
                                  <span className="ml-2 text-[10px] text-slate-400">
                                    {formatDate(c.created_at)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Draft actions */}
                        {req.status === "draft" && (
                          <div className="flex flex-wrap gap-2 pt-2 border-t border-[var(--card-border)]">
                            <button
                              onClick={() => setEditingDraftId(req.request_id)}
                              disabled={busy}
                              className="flex items-center gap-1.5 rounded-lg border border-[var(--card-border)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-slate-50 disabled:opacity-40"
                            >
                              <Pencil size={12} /> Edit
                            </button>
                            <button
                              onClick={() => handleSubmitDraft(req.request_id)}
                              disabled={busy}
                              className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-40"
                            >
                              <Send size={12} /> Submit
                            </button>
                            <button
                              onClick={() => handleDeleteDraft(req.request_id)}
                              disabled={busy}
                              className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-white px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-40"
                            >
                              <Trash2 size={12} /> Delete
                            </button>
                          </div>
                        )}

                        {/* Active (non-draft, non-closed) — comment + transitions */}
                        {req.status !== "draft" && req.status !== "closed" && (
                          <div className="space-y-2 pt-2 border-t border-[var(--card-border)]">
                            <div className="flex gap-2">
                              <input
                                type="text"
                                placeholder="Add a comment..."
                                value={newComment[req.request_id] ?? ""}
                                onChange={(e) =>
                                  setNewComment((prev) => ({
                                    ...prev,
                                    [req.request_id]: e.target.value,
                                  }))
                                }
                                className="flex-1 rounded-lg border border-[var(--card-border)] bg-white px-3 py-1.5 text-xs text-[var(--text-primary)] outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
                              />
                              <button
                                onClick={() => handleAddComment(req.request_id)}
                                disabled={
                                  busy || !(newComment[req.request_id] ?? "").trim()
                                }
                                className="flex items-center gap-1.5 rounded-lg bg-slate-700 px-3 py-1.5 text-xs font-medium text-white hover:bg-slate-800 disabled:opacity-40"
                              >
                                <MessageSquare size={12} /> Send
                              </button>
                            </div>

                            {req.status === "completed" && (
                              <div className="space-y-2 rounded-lg border border-teal-200 bg-teal-50/50 p-3">
                                <p className="text-xs font-semibold text-teal-800">
                                  Review the completed dashboard
                                </p>
                                <div className="flex flex-wrap gap-2">
                                  <button
                                    onClick={() => handleAccept(req.request_id)}
                                    disabled={busy}
                                    className="flex items-center gap-1.5 rounded-lg bg-green-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-green-700 disabled:opacity-40"
                                  >
                                    <CheckCircle2 size={12} /> Accept
                                  </button>
                                </div>
                                <div className="flex gap-2">
                                  <input
                                    type="text"
                                    placeholder="What needs to change?"
                                    value={changeNote[req.request_id] ?? ""}
                                    onChange={(e) =>
                                      setChangeNote((prev) => ({
                                        ...prev,
                                        [req.request_id]: e.target.value,
                                      }))
                                    }
                                    className="flex-1 rounded-lg border border-[var(--card-border)] bg-white px-3 py-1.5 text-xs outline-none focus:border-purple-400 focus:ring-1 focus:ring-purple-400"
                                  />
                                  <button
                                    onClick={() =>
                                      handleRequestChanges(req.request_id)
                                    }
                                    disabled={
                                      busy ||
                                      !(changeNote[req.request_id] ?? "").trim()
                                    }
                                    className="flex items-center gap-1.5 rounded-lg bg-purple-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-purple-700 disabled:opacity-40"
                                  >
                                    <RotateCcw size={12} /> Request Changes
                                  </button>
                                </div>
                              </div>
                            )}

                            {req.status === "accepted" && (
                              <button
                                onClick={() => handleClose(req.request_id)}
                                disabled={busy}
                                className="flex items-center gap-1.5 rounded-lg border border-[var(--card-border)] bg-white px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] hover:bg-slate-50 disabled:opacity-40"
                              >
                                <XCircle size={12} /> Close
                              </button>
                            )}
                          </div>
                        )}
                      </>
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

// ── Chat context sub-component ─────────────────────────────────

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
