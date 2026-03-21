"use client";

import { ReactNode } from "react";

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
        <h3 className="text-[13px] font-semibold text-[var(--text-secondary)]">
          {title}
        </h3>
      </div>
      <div className="flex flex-1 items-center justify-center p-4">
        {children}
      </div>
    </div>
  );
}
