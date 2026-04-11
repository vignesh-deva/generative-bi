"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { MessageSquare, Clock } from "lucide-react";
import { fetchSessions } from "@/lib/api";

type Session = {
  session_id: string;
  title: string | null;
  created_at: string;
  updated_at: string;
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
  });
}

export default function RecentPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const data = await fetchSessions<Session[]>();
        setSessions(data);
      } catch (e) {
        console.error("Failed to load sessions:", e);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm text-[var(--text-muted)]">
            Loading recent chats...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Recent</h1>
        <p className="mt-0.5 text-sm text-[var(--text-muted)]">
          Your recent chat sessions
        </p>
      </div>

      {sessions.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
            <Clock size={24} className="text-slate-400" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            No conversations yet. Start a chat to see history here.
          </p>
          <Link
            href="/chat"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700"
          >
            Start a chat
          </Link>
        </div>
      ) : (
        <div className="space-y-2">
          {sessions.map((s) => (
            <Link
              key={s.session_id}
              href={`/chat?session=${s.session_id}`}
              className="flex items-center gap-4 rounded-xl border border-[var(--card-border)] bg-white px-5 py-3.5 shadow-sm transition-shadow hover:shadow-md"
            >
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-50">
                <MessageSquare size={16} className="text-blue-600" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-[var(--text-primary)]">
                  {s.title || "Untitled conversation"}
                </p>
                <p className="text-xs text-[var(--text-muted)]">
                  {timeAgo(s.updated_at)}
                </p>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
