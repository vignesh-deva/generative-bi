"use client";

import { useEffect, useMemo, useRef } from "react";
import { BarChart3 } from "lucide-react";
import type { ChartMeta } from "@/lib/api";

type Props = {
  open: boolean;
  charts: ChartMeta[];
  excludeIds: string[];
  query: string;        // text after the slash, used for filtering
  activeIndex: number;
  onActiveIndexChange: (idx: number) => void;
  onSelect: (chart: ChartMeta) => void;
  onClose: () => void;
  /** Ordered list of matches, hoisted to the parent so keyboard nav can act on it. */
  onMatchesChange: (matches: ChartMeta[]) => void;
};

const CHART_TYPE_LABELS: Record<string, string> = {
  kpi: "KPI",
  bar: "Bar chart",
  line: "Line chart",
  pie: "Pie chart",
  donut: "Donut chart",
};

export default function ChartPickerPopover({
  open,
  charts,
  excludeIds,
  query,
  activeIndex,
  onActiveIndexChange,
  onSelect,
  onClose,
  onMatchesChange,
}: Props) {
  const listRef = useRef<HTMLUListElement>(null);

  const matches = useMemo(() => {
    const q = query.trim().toLowerCase();
    const excluded = new Set(excludeIds);
    const filtered = charts.filter((c) => !excluded.has(c.chart_id));
    if (!q) return filtered;
    return filtered.filter(
      (c) =>
        c.title.toLowerCase().includes(q) ||
        c.description.toLowerCase().includes(q) ||
        c.chart_id.toLowerCase().includes(q),
    );
  }, [charts, excludeIds, query]);

  // Push matches up so the parent's keydown handler knows what Enter selects.
  useEffect(() => {
    onMatchesChange(matches);
  }, [matches, onMatchesChange]);

  // Clamp active index whenever matches shrink.
  useEffect(() => {
    if (activeIndex >= matches.length && matches.length > 0) {
      onActiveIndexChange(0);
    }
  }, [matches.length, activeIndex, onActiveIndexChange]);

  // Keep active item scrolled into view.
  useEffect(() => {
    if (!open || !listRef.current) return;
    const el = listRef.current.querySelector<HTMLElement>(
      `[data-idx="${activeIndex}"]`,
    );
    el?.scrollIntoView({ block: "nearest" });
  }, [activeIndex, open]);

  // Close on outside click.
  useEffect(() => {
    if (!open) return;
    function onDocClick(e: MouseEvent) {
      const target = e.target as Node;
      if (listRef.current && !listRef.current.contains(target)) {
        // Let the parent's textarea keep focus; just dismiss the popover.
        const form = (target as HTMLElement).closest?.("form");
        // If the click is inside the same chat form (eg. on the textarea),
        // don't close — the keydown handler manages that lifecycle.
        if (!form) onClose();
      }
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="absolute bottom-full left-0 right-0 mb-2 z-40">
      <div className="mx-auto w-full max-w-3xl">
        <div className="rounded-xl border border-[var(--card-border)] bg-white shadow-lg">
          <div className="flex items-center justify-between border-b border-[var(--card-border)] px-3 py-2">
            <span className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
              Attach chart as context
            </span>
            <span className="text-[11px] text-[var(--text-muted)]">
              {matches.length} match{matches.length === 1 ? "" : "es"}
            </span>
          </div>
          {matches.length === 0 ? (
            <div className="px-3 py-4 text-center text-xs text-[var(--text-muted)]">
              No charts match &ldquo;{query}&rdquo;
            </div>
          ) : (
            <ul
              ref={listRef}
              className="max-h-64 overflow-y-auto py-1 scrollbar-thin"
            >
              {matches.map((chart, idx) => {
                const isActive = idx === activeIndex;
                return (
                  <li key={chart.chart_id} data-idx={idx}>
                    <button
                      type="button"
                      onMouseEnter={() => onActiveIndexChange(idx)}
                      onMouseDown={(e) => {
                        // mousedown so we beat the textarea's blur handler.
                        e.preventDefault();
                        onSelect(chart);
                      }}
                      className={`flex w-full items-start gap-2.5 px-3 py-2 text-left transition-colors ${
                        isActive ? "bg-blue-50" : "hover:bg-slate-50"
                      }`}
                    >
                      <div
                        className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg ${
                          isActive ? "bg-blue-100 text-blue-600" : "bg-slate-100 text-slate-500"
                        }`}
                      >
                        <BarChart3 size={14} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <span className="truncate text-sm font-medium text-[var(--text-primary)]">
                            {chart.title}
                          </span>
                          <span className="rounded-full bg-slate-100 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-500">
                            {CHART_TYPE_LABELS[chart.chart_type] ?? chart.chart_type}
                          </span>
                        </div>
                        <p className="mt-0.5 truncate text-xs text-[var(--text-muted)]">
                          {chart.description}
                        </p>
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          <div className="flex items-center justify-between border-t border-[var(--card-border)] px-3 py-1.5 text-[10px] text-[var(--text-muted)]">
            <span>&uarr;&darr; to navigate &middot; Enter to select &middot; Esc to cancel</span>
          </div>
        </div>
      </div>
    </div>
  );
}
