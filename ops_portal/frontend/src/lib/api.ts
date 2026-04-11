const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export async function logout() {
  await fetch(`${API_BASE}/auth/logout`, { method: "POST", credentials: "include" }).catch(() => {});
  window.location.href = "/login";
}

// ── Dashboard request types (shared shape with user portal) ─────

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

export async function fetchTickets(): Promise<DashboardRequest[]> {
  const res = await fetch(`${API_BASE}/api/tickets`, { credentials: "include" });
  return jsonOrError(res, "Tickets API error");
}

export async function fetchTicket(id: string): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/tickets/${id}`, { credentials: "include" });
  return jsonOrError(res, "Ticket fetch error");
}

export async function updateTicketStatus(
  requestId: string,
  status: string,
  comment?: string,
): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/tickets/${requestId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ status, comment }),
  });
  return jsonOrError(res, "Update ticket error");
}

export async function addTicketComment(
  requestId: string,
  text: string,
): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/tickets/${requestId}/comments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ text }),
  });
  return jsonOrError(res, "Add comment error");
}

export type FeedbackVote = "all" | "up" | "down";

export type FeedbackItem = {
  message_id: string;
  session_id: string;
  question: string;
  sql_query: string | null;
  answer: string | null;
  feedback: "up" | "down" | null;
  feedback_comment: string | null;
  created_at: string;
  top_similarity: number;
  top_match_question: string | null;
  promoted_at: string | null;
  promoted_example_id: number | null;
};

export type FeedbackFilters = {
  vote?: FeedbackVote;
  hide_duplicates?: boolean;
  include_promoted?: boolean;
};

export async function fetchFeedback(
  filters: FeedbackFilters = {}
): Promise<FeedbackItem[]> {
  const params = new URLSearchParams();
  if (filters.vote) params.set("vote", filters.vote);
  if (filters.hide_duplicates !== undefined)
    params.set("hide_duplicates", String(filters.hide_duplicates));
  if (filters.include_promoted !== undefined)
    params.set("include_promoted", String(filters.include_promoted));
  const qs = params.toString();
  const res = await fetch(
    `${API_BASE}/api/feedback${qs ? `?${qs}` : ""}`,
    { credentials: "include" }
  );
  return jsonOrError(res, "Feedback API error");
}

export type PromoteResult = {
  example_id: number;
  message_id: string;
  promoted_at: string;
};

export type PromoteConflict = {
  error: "duplicate";
  similarity: number;
  top_match: { example_id: number; question: string };
  threshold: number;
};

export async function promoteFeedback(
  messageId: string,
  question: string,
  sql: string,
  force: boolean = false
): Promise<PromoteResult> {
  const url = `${API_BASE}/api/feedback/${messageId}/promote${force ? "?force=true" : ""}`;
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ question, sql }),
  });
  if (res.status === 409) {
    const body = await res.json().catch(() => ({}));
    const err = new Error("duplicate") as Error & { conflict?: PromoteConflict };
    err.conflict = body?.detail as PromoteConflict;
    throw err;
  }
  return jsonOrError(res, "Promote feedback error");
}

export async function fetchFewshots<T>(): Promise<T> {
  const res = await fetch(`${API_BASE}/api/rag/fewshots`, { credentials: "include" });
  if (!res.ok) throw new Error(`RAG API error: ${res.status}`);
  return res.json();
}

export async function createFewshot(
  question: string,
  sql: string
): Promise<{ id: number }> {
  const res = await fetch(`${API_BASE}/api/rag/fewshots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ question, sql }),
  });
  if (!res.ok) throw new Error(`Create fewshot error: ${res.status}`);
  return res.json();
}
