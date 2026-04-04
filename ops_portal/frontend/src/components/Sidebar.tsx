"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Ticket,
  MessageSquareWarning,
  BookOpen,
  Settings2,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";

const navItems = [
  { href: "/", label: "Tickets", icon: Ticket },
  { href: "/feedback", label: "Feedback", icon: MessageSquareWarning },
  { href: "/rag", label: "RAG Curation", icon: BookOpen },
];

export default function Sidebar({
  collapsed,
  onToggle,
}: {
  collapsed: boolean;
  onToggle: () => void;
}) {
  const pathname = usePathname();

  return (
    <aside
      className={`flex flex-col rounded-2xl bg-[var(--sidebar-bg)] transition-all duration-300 ${
        collapsed ? "w-[68px]" : "w-60"
      }`}
    >
      {/* Brand */}
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-2.5 overflow-hidden">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-violet-600">
            <Settings2 size={18} className="text-white" />
          </div>
          {!collapsed && (
            <span className="whitespace-nowrap text-base font-bold tracking-tight text-white">
              Ops Center
            </span>
          )}
        </div>
        <button
          onClick={onToggle}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-[var(--sidebar-text)] transition-colors hover:bg-white/10 hover:text-white"
        >
          {collapsed ? (
            <PanelLeftOpen size={16} />
          ) : (
            <PanelLeftClose size={16} />
          )}
        </button>
      </div>

      {/* Divider */}
      <div className="mx-4 border-t border-white/10" />

      {/* Nav */}
      <div className="mt-5 px-3">
        {!collapsed && (
          <p className="mb-2 px-3 text-[10px] font-semibold uppercase tracking-widest text-[var(--sidebar-heading)]">
            Manage
          </p>
        )}
        <nav className="flex flex-col gap-0.5">
          {navItems.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                title={collapsed ? label : undefined}
                className={`group relative flex items-center rounded-lg transition-all duration-150 ${
                  collapsed
                    ? "justify-center px-0 py-2.5"
                    : "gap-3 px-3 py-2"
                } text-[13px] font-medium ${
                  active
                    ? "bg-[var(--sidebar-active)] text-[var(--sidebar-active-text)]"
                    : "text-[var(--sidebar-text)] hover:bg-[var(--sidebar-hover)] hover:text-slate-200"
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
                {!collapsed && label}
                {!collapsed && active && (
                  <span className="ml-auto h-1.5 w-1.5 rounded-full bg-[var(--sidebar-active-text)]" />
                )}
                {collapsed && active && (
                  <span className="absolute right-1 top-1/2 h-1.5 w-1.5 -translate-y-1/2 rounded-full bg-[var(--sidebar-active-text)]" />
                )}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Bottom */}
      {!collapsed && (
        <div className="mt-auto px-4 pb-4">
          <div className="rounded-lg border border-white/10 bg-white/5 p-3">
            <p className="text-xs font-medium text-slate-400">
              Operations Center
            </p>
            <p className="mt-0.5 text-[11px] text-slate-500">
              Platform Management
            </p>
          </div>
        </div>
      )}
    </aside>
  );
}
