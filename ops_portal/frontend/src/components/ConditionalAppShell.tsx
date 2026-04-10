"use client";

import { usePathname } from "next/navigation";
import { ReactNode } from "react";
import AppShell from "./AppShell";

export default function ConditionalAppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  if (pathname === "/login") return <>{children}</>;
  return <AppShell>{children}</AppShell>;
}
