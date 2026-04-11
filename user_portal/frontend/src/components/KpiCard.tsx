"use client";

import { ReactNode } from "react";

export default function KpiCard({
  title,
  value,
  icon,
  accent = "#2563eb",
}: {
  title: string;
  value: string;
  icon: ReactNode;
  accent?: string;
}) {
  return (
    <div
      className="group relative flex flex-col justify-between rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] p-5 transition-shadow duration-200 hover:shadow-md"
      style={{
        boxShadow: "var(--card-shadow)",
        borderLeft: `3px solid ${accent}`,
      }}
    >
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            {title}
          </p>
          <p className="mt-2 text-[28px] font-bold leading-none tracking-tight text-[var(--text-primary)]">
            {value}
          </p>
        </div>
        <div
          className="flex h-11 w-11 items-center justify-center rounded-xl bg-slate-50"
          style={{ color: accent }}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}
