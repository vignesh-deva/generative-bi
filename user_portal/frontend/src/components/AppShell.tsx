"use client";

import { useState, ReactNode } from "react";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function AppShell({ children }: { children: ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const toggle = () => setCollapsed((c) => !c);

  return (
    <div
      className={`flex h-screen overflow-hidden bg-[var(--sidebar-bg)] transition-all duration-300 ${
        collapsed ? "gap-0 p-2 pl-0" : "gap-2 p-2"
      }`}
    >
      <Sidebar collapsed={collapsed} onToggle={toggle} />
      <div
        className={`flex flex-1 flex-col overflow-hidden bg-[var(--background)] transition-all duration-300 ${
          collapsed ? "rounded-r-2xl" : "rounded-2xl"
        }`}
      >
        <Header onToggleSidebar={toggle} sidebarCollapsed={collapsed} />
        <main className="flex-1 overflow-y-auto p-6">{children}</main>
      </div>
    </div>
  );
}
