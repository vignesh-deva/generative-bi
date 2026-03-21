"use client";

import { ReactNode } from "react";

export default function KpiCard({
  title,
  value,
  icon,
  accent = "#3b82f6",
}: {
  title: string;
  value: string;
  icon: ReactNode;
  accent?: string;
}) {
  return (
    <div
      className="group relative overflow-hidden rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] p-5 transition-shadow duration-200 hover:shadow-md"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      {/* Accent top bar */}
      <div
        className="absolute inset-x-0 top-0 h-[3px]"
        style={{ background: accent }}
      />
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--text-muted)]">
            {title}
          </p>
          <p className="mt-2 text-2xl font-bold tracking-tight text-[var(--text-primary)]">
            {value}
          </p>
        </div>
        <div
          className="flex h-11 w-11 items-center justify-center rounded-xl"
          style={{ background: `${accent}12`, color: accent }}
        >
          {icon}
        </div>
      </div>
    </div>
  );
}
