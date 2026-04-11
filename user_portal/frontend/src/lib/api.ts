const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function logout() {
  await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" }).catch(() => {});
  window.location.href = "/login";
}

export async function fetchDashboard<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api/dashboard/${endpoint}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Dashboard API error: ${res.status}`);
  return res.json();
}

// ── Chart metadata (for chat slash-command chart picker) ─────────

export type ChartMeta = {
  chart_id: string;
  title: string;
  description: string;
  chart_type: "kpi" | "bar" | "line" | "pie" | "donut";
  sql_query: string;
};

export async function fetchChartsMetadata(): Promise<ChartMeta[]> {
  const res = await fetch(`${API_BASE}/api/dashboard/charts/metadata`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Charts metadata API error: ${res.status}`);
  return res.json();
}

export async function fetchSessions<T>(): Promise<T> {
  const res = await fetch(`${API_BASE}/api/history/sessions`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`History API error: ${res.status}`);
  return res.json();
}

// ── Session events (used to notify the sidebar when a new chat is created) ──

export type SessionMeta = {
  session_id: string;
  title: string | null;
  updated_at: string;
};

type SessionListener = (session: SessionMeta) => void;
const sessionCreatedListeners = new Set<SessionListener>();

export function onSessionCreated(fn: SessionListener): () => void {
  sessionCreatedListeners.add(fn);
  return () => {
    sessionCreatedListeners.delete(fn);
  };
}

export function emitSessionCreated(session: SessionMeta): void {
  sessionCreatedListeners.forEach((fn) => fn(session));
}

export async function fetchMessages<T>(sessionId: string): Promise<T> {
  const res = await fetch(
    `${API_BASE}/api/history/sessions/${sessionId}/messages`,
    { credentials: "include" }
  );
  if (!res.ok) throw new Error(`Messages API error: ${res.status}`);
  return res.json();
}

export type FeedbackVote = "up" | "down" | null;

export async function submitFeedback(
  messageId: string,
  vote: FeedbackVote,
  comment: string | null
): Promise<{ message_id: string; feedback: FeedbackVote; feedback_comment: string | null }> {
  const res = await fetch(`${API_BASE}/api/feedback/${messageId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ feedback: vote, comment }),
  });
  return jsonOrError(res, "Submit feedback failed");
}

// ── Dashboard request types ──────────────────────────────────────

export type RequestStatus =
  | "draft"
  | "requested"
  | "in-progress"
  | "need additional details"
  | "completed"
  | "accepted"
  | "request changes"
  | "closed";

export type ChatHistoryMessage = {
  role: "user" | "assistant";
  content: string;
  created_at?: string | null;
};

export type ChatContext = {
  message_id: string;
  question: string;
  answer: string;
  sql: string | null;
  history: ChatHistoryMessage[];
};

export type RequestComment = {
  comment_id: string;
  author: string;
  text: string;
  type: "comment" | "status_change";
  created_at: string;
};

export type StatusHistoryEntry = {
  from: string | null;
  to: string;
  actor: "user" | "ops" | "system";
  at: string;
  note: string | null;
};

export type DashboardRequest = {
  request_id: string;
  session_id: string | null;
  title: string;
  description: string;
  chat_context: ChatContext | null;
  status: RequestStatus;
  created_at: string;
  updated_at: string;
  submitted_at: string | null;
  closed_at: string | null;
  auto_close_eligible_at: string | null;
  comments: RequestComment[];
  status_history: StatusHistoryEntry[];
};

// ── Dashboard request endpoints ──────────────────────────────────

async function jsonOrError<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body?.detail ? `: ${body.detail}` : "";
    } catch {
      /* ignore */
    }
    throw new Error(`${label} (${res.status})${detail}`);
  }
  return res.json();
}

export async function fetchRequests(): Promise<DashboardRequest[]> {
  const res = await fetch(`${API_BASE}/api/requests`, { credentials: "include" });
  return jsonOrError(res, "Fetch requests failed");
}

export async function fetchRequest(id: string): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests/${id}`, { credentials: "include" });
  return jsonOrError(res, "Fetch request failed");
}

export async function createDraft(payload: {
  title: string;
  description: string;
  chat_context?: ChatContext | null;
  session_id?: string | null;
}): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests/drafts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return jsonOrError(res, "Create draft failed");
}

export async function updateDraft(
  id: string,
  payload: { title?: string; description?: string }
): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests/drafts/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return jsonOrError(res, "Update draft failed");
}

export async function deleteDraft(id: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/requests/drafts/${id}`, {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Delete draft failed (${res.status})`);
}

export async function submitDraft(id: string): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests/drafts/${id}/submit`, {
    method: "POST",
    credentials: "include",
  });
  return jsonOrError(res, "Submit draft failed");
}

export async function createRequest(payload: {
  title: string;
  description: string;
  chat_context?: ChatContext | null;
  session_id?: string | null;
}): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  return jsonOrError(res, "Create request failed");
}

export async function addRequestComment(
  id: string,
  text: string
): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests/${id}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ text }),
  });
  return jsonOrError(res, "Add comment failed");
}

export async function acceptRequest(
  id: string,
  note?: string
): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests/${id}/accept`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ note: note ?? null }),
  });
  return jsonOrError(res, "Accept failed");
}

export async function requestChanges(
  id: string,
  note: string
): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests/${id}/request-changes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ note }),
  });
  return jsonOrError(res, "Request changes failed");
}

export async function closeRequest(id: string): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/requests/${id}/close`, {
    method: "POST",
    credentials: "include",
  });
  return jsonOrError(res, "Close failed");
}

export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
