"use client";

import { useState, useRef, useEffect, FormEvent, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import {
  Send, Bot, User, Loader2, Sparkles, Table2,
  ChevronRight, ChevronDown, FilePlus,
} from "lucide-react";
import { authHeader, fetchMessages, type ChatContext } from "@/lib/api";
import RequestModal from "./RequestModal";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sql?: string;
  steps?: string[];
  stepsOpen?: boolean;
  timestamp: Date;
};

// ── Steps panel ───────────────────────────────────────────────────

function StepsPanel({
  steps,
  isOpen,
  isStreaming,
  onToggle,
}: {
  steps: string[];
  isOpen: boolean;
  isStreaming: boolean;
  onToggle: () => void;
}) {
  const listRef = useRef<HTMLUListElement>(null);

  // Auto-scroll to latest step whenever a new one arrives or panel opens
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [steps.length, isOpen]);

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="mb-2 flex items-center gap-1.5 rounded-full border border-[var(--card-border)] bg-slate-50 px-2.5 py-1 text-[11px] text-[var(--text-muted)] transition-colors hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600"
      >
        <ChevronRight size={11} />
        {steps.length} step{steps.length !== 1 ? "s" : ""}
      </button>
    );
  }

  return (
    <div className="mb-3 rounded-lg border border-[var(--card-border)] bg-slate-50 px-3 py-2">
      <button
        onClick={onToggle}
        className="flex w-full items-center justify-between text-[11px] font-medium text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
      >
        <span className="text-[10px] uppercase tracking-wide text-slate-400">
          Reasoning
        </span>
        <ChevronDown size={11} />
      </button>

      {/* Fixed height + scroll + auto-scroll to latest */}
      <ul
        ref={listRef}
        className="mt-2 max-h-36 space-y-1.5 overflow-y-auto pr-1 scrollbar-thin"
      >
        {steps.map((step, i) => {
          const isActive = isStreaming && i === steps.length - 1;
          const isDone = !isActive;
          return (
            <li key={i} className="flex items-center gap-2 text-[11px]">
              {isActive ? (
                <Loader2 size={10} className="shrink-0 animate-spin text-blue-500" />
              ) : (
                <div className="h-1.5 w-1.5 shrink-0 rounded-full bg-blue-300" />
              )}
              <span
                className={
                  isActive
                    ? "font-medium text-blue-600"
                    : isDone
                    ? "text-slate-400"
                    : "text-[var(--text-muted)]"
                }
              >
                {step}
              </span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ── Types ─────────────────────────────────────────────────────────

type HistoryMessage = {
  role: "user" | "assistant";
  content: string;
  sql_query?: string | null;
  created_at: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// ── Chat page ─────────────────────────────────────────────────────

function ChatPageInner() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [showSql, setShowSql] = useState<string | null>(null);
  const [requestModal, setRequestModal] = useState<{
    title: string;
    context: ChatContext;
  } | null>(null);
  const [requestFlash, setRequestFlash] = useState<string | null>(null);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sessionIdRef = useRef<string | null>(null);
  const streamingMsgIdRef = useRef<string | null>(null);
  const searchParams = useSearchParams();
  const sessionParam = searchParams.get("session");

  function toggleSteps(msgId: string) {
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, stepsOpen: !m.stepsOpen } : m))
    );
  }

  function openRequestModalForMessage(msg: Message) {
    const idx = messages.findIndex((m) => m.id === msg.id);
    if (idx < 0) return;
    // Previous user message (the question this response answers)
    let question = "";
    for (let i = idx - 1; i >= 0; i--) {
      if (messages[i].role === "user") {
        question = messages[i].content;
        break;
      }
    }
    // Last 6 messages ending at this assistant message (inclusive)
    const start = Math.max(0, idx - 5);
    const history = messages.slice(start, idx + 1).map((m) => ({
      role: m.role,
      content: m.content,
      created_at: m.timestamp.toISOString(),
    }));
    const context: ChatContext = {
      message_id: msg.id,
      question,
      answer: msg.content,
      sql: msg.sql ?? null,
      history,
    };
    const initialTitle = (question || msg.content).slice(0, 80);
    setRequestModal({ title: initialTitle, context });
  }

  function onRequestResult(kind: "draft" | "submitted") {
    setRequestFlash(
      kind === "submitted" ? "Request submitted." : "Draft saved."
    );
    setTimeout(() => setRequestFlash(null), 3500);
  }

  // Load session history whenever the ?session= param changes
  useEffect(() => {
    if (!sessionParam) {
      sessionIdRef.current = null;
      setMessages([]);
      return;
    }
    if (sessionIdRef.current === sessionParam) return;

    sessionIdRef.current = sessionParam;
    setLoadingHistory(true);
    setMessages([]);

    fetchMessages<HistoryMessage[]>(sessionParam)
      .then((data) => {
        setMessages(
          data.map((m) => ({
            id: crypto.randomUUID(),
            role: m.role,
            content: m.content,
            sql: m.sql_query ?? undefined,
            timestamp: new Date(m.created_at),
          }))
        );
      })
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, [sessionParam]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!loadingHistory) inputRef.current?.focus();
  }, [loadingHistory]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setStreaming(true);

    const assistantId = crypto.randomUUID();
    streamingMsgIdRef.current = assistantId;
    setMessages((prev) => [
      ...prev,
      { id: assistantId, role: "assistant", content: "", timestamp: new Date() },
    ]);

    try {
      const res = await fetch(`${API_BASE}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...authHeader() },
        body: JSON.stringify({ query: text, session_id: sessionIdRef.current }),
      });

      if (!res.ok) throw new Error(`API error: ${res.status}`);

      const returnedSessionId = res.headers.get("X-Session-Id");
      if (returnedSessionId && !sessionIdRef.current) {
        sessionIdRef.current = returnedSessionId;
        window.history.replaceState(null, "", `/chat?session=${returnedSessionId}`);
      }

      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      let accumulated = "";
      let sql = "";
      let steps: string[] = [];
      let firstTokenSeen = false;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6);
            if (data === "[DONE]") break;

            try {
              const parsed = JSON.parse(data);
              if (parsed.type === "step") {
                steps = [...steps, parsed.content];
              } else if (parsed.type === "token") {
                if (!firstTokenSeen) {
                  firstTokenSeen = true;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId ? { ...m, stepsOpen: false } : m
                    )
                  );
                }
                accumulated += parsed.content;
              } else if (parsed.type === "sql") {
                sql = parsed.content;
              } else if (parsed.type === "error") {
                accumulated = parsed.content;
              }
            } catch {
              accumulated += data;
            }
          }

          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: accumulated,
                    sql: sql || undefined,
                    steps: steps.length > 0 ? steps : undefined,
                    stepsOpen: m.stepsOpen ?? true,
                  }
                : m
            )
          );
        }
      }

      if (!accumulated) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, content: "Sorry, I couldn't generate a response." }
              : m
          )
        );
      }
    } catch {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId
            ? { ...m, content: "Failed to connect to the server. Please try again." }
            : m
        )
      );
    } finally {
      streamingMsgIdRef.current = null;
      setStreaming(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  }

  if (loadingHistory) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-7 w-7 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          <p className="text-sm text-[var(--text-muted)]">Loading conversation…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-[var(--card-border)] pb-3">
        <h1 className="text-xl font-bold text-[var(--text-primary)]">Chat</h1>
        <p className="mt-0.5 text-sm text-[var(--text-muted)]">
          Ask questions about your FMCG supply chain data
        </p>
      </div>

      {requestFlash && (
        <div className="fixed right-6 top-6 z-40 rounded-lg border border-green-200 bg-green-50 px-4 py-2 text-sm text-green-700 shadow-md">
          {requestFlash}
        </div>
      )}

      {requestModal && (
        <RequestModal
          open={!!requestModal}
          onClose={() => setRequestModal(null)}
          initialTitle={requestModal.title}
          chatContext={requestModal.context}
          sessionId={sessionIdRef.current}
          onResult={onRequestResult}
        />
      )}

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto py-5">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-blue-50">
              <Sparkles size={24} className="text-blue-500" />
            </div>
            <div>
              <p className="text-base font-semibold text-[var(--text-primary)]">
                Ask anything about your data
              </p>
              <p className="mt-1 max-w-xs text-sm text-[var(--text-muted)]">
                Query your FMCG supply chain database, surface insights,
                and explore trends in plain English.
              </p>
            </div>
            <div className="mt-1 flex flex-wrap justify-center gap-2">
              {[
                "What are the top selling products?",
                "Show monthly revenue trend",
                "Which zone has highest sales?",
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                    setTimeout(() => inputRef.current?.focus(), 0);
                  }}
                  className="rounded-lg border border-[var(--card-border)] bg-white px-3 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:border-blue-300 hover:bg-blue-50 hover:text-blue-600"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        ) : (
          /* Constrain message column width for readability */
          <div className="mx-auto w-full max-w-3xl space-y-5 px-1">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-3 ${
                  msg.role === "user" ? "justify-end" : "justify-start"
                }`}
              >
                {msg.role === "assistant" && (
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-50 mt-0.5">
                    <Bot size={14} className="text-blue-600" />
                  </div>
                )}

                <div
                  className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                    msg.role === "user"
                      ? "bg-blue-600 text-white"
                      : "border border-[var(--card-border)] bg-white text-[var(--text-primary)] shadow-sm"
                  }`}
                >
                  {/* Thinking indicator — three staggered dots */}
                  {msg.role === "assistant" &&
                  !msg.content &&
                  !msg.steps &&
                  streaming ? (
                    <div className="flex items-center gap-1 py-1">
                      {[0, 150, 300].map((delay) => (
                        <span
                          key={delay}
                          className="h-2 w-2 rounded-full bg-slate-300 animate-bounce"
                          style={{ animationDelay: `${delay}ms` }}
                        />
                      ))}
                    </div>
                  ) : (
                    <>
                      {msg.steps && msg.steps.length > 0 && (
                        <StepsPanel
                          steps={msg.steps}
                          isOpen={msg.stepsOpen ?? false}
                          isStreaming={streaming && msg.id === streamingMsgIdRef.current}
                          onToggle={() => toggleSteps(msg.id)}
                        />
                      )}
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                      {msg.role === "assistant" && msg.content && (
                        <div className="mt-2.5 flex items-center gap-3">
                          {msg.sql && (
                            <button
                              onClick={() =>
                                setShowSql(showSql === msg.id ? null : msg.id)
                              }
                              className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                            >
                              <Table2 size={12} />
                              {showSql === msg.id ? "Hide SQL" : "View SQL"}
                            </button>
                          )}
                          <button
                            onClick={() => openRequestModalForMessage(msg)}
                            className="flex items-center gap-1.5 text-xs text-[var(--text-muted)] hover:text-blue-600"
                          >
                            <FilePlus size={12} />
                            Request Dashboard
                          </button>
                        </div>
                      )}
                      {msg.sql && msg.role === "user" && (
                        <button
                          onClick={() =>
                            setShowSql(showSql === msg.id ? null : msg.id)
                          }
                          className="mt-2.5 flex items-center gap-1.5 text-xs text-blue-200 hover:text-white"
                        >
                          <Table2 size={12} />
                          {showSql === msg.id ? "Hide SQL" : "View SQL"}
                        </button>
                      )}
                      {showSql === msg.id && msg.sql && (
                        <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-900 p-3 text-xs text-slate-300">
                          <code>{msg.sql}</code>
                        </pre>
                      )}
                    </>
                  )}
                </div>

                {msg.role === "user" && (
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-blue-600 mt-0.5">
                    <User size={14} className="text-white" />
                  </div>
                )}
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Input bar — constrained width, compact */}
      <form
        onSubmit={handleSubmit}
        className="border-t border-[var(--card-border)] pt-3 pb-1"
      >
        <div className="mx-auto w-full max-w-3xl">
          <div className="flex items-end gap-2 rounded-xl border border-[var(--card-border)] bg-white px-4 py-3 shadow-sm transition-shadow focus-within:border-blue-300 focus-within:shadow-md">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your data…"
              rows={1}
              className="max-h-36 min-h-[52px] flex-1 resize-none bg-transparent py-1 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none"
            />
            <button
              type="submit"
              disabled={!input.trim() || streaming}
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-blue-600 text-white transition-colors hover:bg-blue-700 disabled:opacity-40 disabled:hover:bg-blue-600"
            >
              {streaming ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
            </button>
          </div>
          <p className="mt-1.5 text-center text-[11px] text-[var(--text-muted)]">
            AI-generated — verify important figures before acting on them.
          </p>
        </div>
      </form>
    </div>
  );
}

export default function ChatPage() {
  return (
    <Suspense>
      <ChatPageInner />
    </Suspense>
  );
}
