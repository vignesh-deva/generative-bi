"use client";

import { useState, FormEvent } from "react";
import { ChevronDown, ChevronRight, MessageSquare } from "lucide-react";
import type { ChatContext } from "@/lib/api";

type Props = {
  mode: "create" | "edit";
  initial?: { title: string; description: string };
  chatContext?: ChatContext | null;
  showSaveDraft?: boolean;
  onSubmit: (data: { title: string; description: string }) => Promise<void>;
  onSaveDraft?: (data: { title: string; description: string }) => Promise<void>;
  onCancel: () => void;
  busy?: boolean;
};

const HINTS = [
  ["Goal", "what decision will this dashboard support?"],
  ["Key metrics / KPIs", "which numbers matter most?"],
  ["Breakdowns", "by region, product, time period, etc."],
  ["Time range", "last 30 days, YTD, rolling 12 months?"],
  ["Filters", "any slices that should be interactive?"],
  ["Audience", "who will use this and how often?"],
] as const;

export default function RequestForm({
  mode,
  initial,
  chatContext,
  showSaveDraft = true,
  onSubmit,
  onSaveDraft,
  onCancel,
  busy = false,
}: Props) {
  const [title, setTitle] = useState(initial?.title ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [ctxOpen, setCtxOpen] = useState(false);

  const canSubmit = title.trim().length > 0 && description.trim().length > 0 && !busy;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    await onSubmit({ title: title.trim(), description: description.trim() });
  }

  async function handleSaveDraft() {
    if (!title.trim() || !description.trim() || busy) return;
    if (onSaveDraft) {
      await onSaveDraft({ title: title.trim(), description: description.trim() });
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <h2 className="text-sm font-semibold text-[var(--text-primary)]">
          {mode === "create" ? "New Dashboard Request" : "Edit Draft"}
        </h2>
        <p className="mt-0.5 text-xs text-[var(--text-muted)]">
          Once submitted, the title and description cannot be changed.
        </p>
      </div>

      {chatContext && (
        <div className="rounded-lg border border-blue-200 bg-blue-50/40">
          <button
            type="button"
            onClick={() => setCtxOpen(!ctxOpen)}
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-xs font-medium text-blue-700"
          >
            {ctxOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            <MessageSquare size={12} />
            Attached from chat
          </button>
          {ctxOpen && (
            <div className="space-y-2 border-t border-blue-200 px-3 py-2 text-xs text-[var(--text-secondary)]">
              <div>
                <span className="font-semibold text-blue-700">Question: </span>
                {chatContext.question}
              </div>
              {chatContext.sql && (
                <div>
                  <span className="font-semibold text-blue-700">SQL:</span>
                  <pre className="mt-1 overflow-x-auto rounded bg-slate-900 p-2 text-[11px] text-slate-300">
                    <code>{chatContext.sql}</code>
                  </pre>
                </div>
              )}
              <p className="text-[11px] text-[var(--text-muted)]">
                The full chat context ({chatContext.history.length} recent messages) will be attached.
              </p>
            </div>
          )}
        </div>
      )}

      <div>
        <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
          Title
        </label>
        <input
          type="text"
          placeholder="Short, descriptive title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full rounded-lg border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
        />
      </div>

      <div className="rounded-lg border border-amber-200 bg-amber-50/50 p-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
          What to cover in your description
        </p>
        <ul className="mt-2 space-y-1 text-xs text-amber-900">
          {HINTS.map(([label, hint]) => (
            <li key={label} className="flex gap-1.5">
              <span className="font-semibold">{label}</span>
              <span className="text-amber-800">— {hint}</span>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
          Description
        </label>
        <textarea
          placeholder="Describe the dashboard you need. Cover the points above."
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={7}
          className="w-full resize-none rounded-lg border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-400"
        />
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 disabled:opacity-40"
        >
          {busy ? "Working..." : "Submit Request"}
        </button>
        {showSaveDraft && onSaveDraft && (
          <button
            type="button"
            onClick={handleSaveDraft}
            disabled={!title.trim() || !description.trim() || busy}
            className="rounded-lg border border-[var(--card-border)] bg-white px-4 py-2 text-sm font-medium text-[var(--text-secondary)] transition-colors hover:bg-slate-50 disabled:opacity-40"
          >
            Save Draft
          </button>
        )}
        <button
          type="button"
          onClick={onCancel}
          disabled={busy}
          className="rounded-lg border border-[var(--card-border)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--background)]"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
