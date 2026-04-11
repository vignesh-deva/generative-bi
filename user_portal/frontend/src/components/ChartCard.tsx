"use client";

import { ReactNode } from "react";
import { MoreHorizontal } from "lucide-react";

export default function ChartCard({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div
      className="flex flex-col rounded-xl border border-[var(--card-border)] bg-[var(--card-bg)] transition-shadow duration-200 hover:shadow-md"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="flex items-center justify-between border-b border-[var(--card-border)] px-5 py-3.5">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">
          {title}
        </h3>
        <button
          className="flex h-7 w-7 items-center justify-center rounded-md text-[var(--text-muted)] transition-colors hover:bg-[var(--background)] hover:text-[var(--text-secondary)]"
          aria-label="Chart options"
        >
          <MoreHorizontal size={16} />
        </button>
      </div>
      <div className="flex flex-1 items-center justify-center p-4">
        {children}
      </div>
    </div>
  );
}
