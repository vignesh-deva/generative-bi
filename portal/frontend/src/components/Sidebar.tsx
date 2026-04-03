"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  BarChart3,
  PanelLeftClose,
} from "lucide-react";
import { fetchSessions } from "@/lib/api";

type Session = {
  session_id: string;
  title: string | null;
  updated_at: string;
};

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/chat", label: "Chat", icon: MessageSquare },
  { href: "/requests", label: "Requests", icon: FileText },
];

export default function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const pathname = usePathname();
  const [sessions, setSessions] = useState<Session[]>([]);

  useEffect(() => {
    const cutoff = Date.now() - 30 * 24 * 60 * 60 * 1000;
    fetchSessions<Session[]>()
      .then((data) =>
        setSessions(
          data.filter((s) => new Date(s.updated_at).getTime() >= cutoff)
        )
      )
      .catch(() => {});
  }, []);

  return (
    <aside
      className={`flex flex-col rounded-2xl bg-[var(--sidebar-bg)] transition-all duration-300 ${
        collapsed ? "w-0 overflow-hidden" : "w-60"
      }`}
    >
      {/* Brand */}
      <div className="flex h-14 shrink-0 items-center justify-between px-4">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600">
            <BarChart3 size={18} className="text-white" />
          </div>
          <span className="whitespace-nowrap text-base font-bold tracking-tight text-white">
            Generative BI
          </span>
        </div>
        <button
          onClick={onToggle}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--sidebar-text)] transition-colors hover:bg-white/10 hover:text-white"
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      {/* Divider */}
      <div className="mx-4 shrink-0 border-t border-white/10" />

      {/* Top nav items */}
      <div className="mt-5 shrink-0 px-3">
        <nav className="flex flex-col gap-0.5">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`group relative flex items-center gap-3 py-2 pr-3 text-[13px] font-medium transition-all duration-150 ${
                  active
                    ? "border-l-2 border-[var(--sidebar-active-border)] bg-[var(--sidebar-hover)] pl-[10px] text-[var(--sidebar-active-text)]"
                    : "rounded-lg pl-3 text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] hover:text-slate-200"
                }`}
              >
                <Icon
                  size={18}
                  strokeWidth={active ? 2.2 : 1.8}
                  className={
                    active
                      ? "text-[var(--sidebar-active-text)]"
                      : "text-[var(--sidebar-text)] group-hover:text-slate-300"
                  }
                />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Recents section */}
      <div className="mt-5 flex min-h-0 flex-1 flex-col px-3">
        <p className="mb-1.5 shrink-0 px-1 text-[10px] font-semibold uppercase tracking-widest text-[var(--sidebar-heading)]">
          Recents
        </p>
        <div className="flex-1 overflow-y-auto">
          {sessions.length === 0 ? (
            <p className="px-1 text-[11px] text-[var(--sidebar-text)]">
              No recent chats
            </p>
          ) : (
            <div className="flex flex-col gap-0.5">
              {sessions.map((s) => (
                <Link
                  key={s.session_id}
                  href={`/chat?session=${s.session_id}`}
                  className="block truncate rounded-lg px-2 py-1.5 text-[12px] text-[var(--sidebar-text)] transition-colors hover:bg-[var(--sidebar-hover)] hover:text-slate-200"
                  title={s.title ?? "Untitled conversation"}
                >
                  {s.title || "Untitled conversation"}
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom label */}
      <div className="shrink-0 px-4 pb-5 pt-3">
        <p className="text-[11px] font-medium text-[var(--sidebar-heading)]">
          FMCG Analytics
        </p>
        <p className="mt-0.5 text-[10px] text-zinc-500">v1.0 · Supply Chain</p>
      </div>
    </aside>
  );
}
