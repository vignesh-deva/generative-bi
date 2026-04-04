"use client";

import { Bell, Search, User } from "lucide-react";

export default function Header() {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-[var(--header-border)] bg-[var(--header-bg)] px-6 rounded-t-2xl">
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]"
          />
          <input
            type="text"
            placeholder="Search tickets, feedback..."
            className="h-9 w-72 rounded-lg border border-[var(--card-border)] bg-[var(--background)] pl-9 pr-4 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none transition-colors focus:border-violet-500 focus:ring-1 focus:ring-violet-500"
          />
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button className="relative flex h-9 w-9 items-center justify-center rounded-lg text-[var(--text-secondary)] transition-colors hover:bg-[var(--background)]">
          <Bell size={18} />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
        </button>
        <div className="mx-2 h-6 w-px bg-[var(--card-border)]" />
        <button className="flex items-center gap-2.5 rounded-lg px-2 py-1.5 transition-colors hover:bg-[var(--background)]">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-violet-500 to-violet-600 text-xs font-semibold text-white">
            <User size={16} />
          </div>
          <div className="text-left">
            <p className="text-sm font-medium leading-none text-[var(--text-primary)]">
              Ops Admin
            </p>
            <p className="mt-0.5 text-xs text-[var(--text-muted)]">
              ops@company.com
            </p>
          </div>
        </button>
      </div>
    </header>
  );
}
