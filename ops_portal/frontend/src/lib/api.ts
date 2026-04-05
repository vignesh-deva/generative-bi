const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

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
  const res = await fetch(`${API_BASE}/api/tickets`);
  return jsonOrError(res, "Tickets API error");
}

export async function fetchTicket(id: string): Promise<DashboardRequest> {
  const res = await fetch(`${API_BASE}/api/tickets/${id}`);
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
    body: JSON.stringify({ text }),
  });
  return jsonOrError(res, "Add comment error");
}

export async function fetchFeedback<T>(): Promise<T> {
  const res = await fetch(`${API_BASE}/api/feedback`);
  if (!res.ok) throw new Error(`Feedback API error: ${res.status}`);
  return res.json();
}

export async function fetchFewshots<T>(): Promise<T> {
  const res = await fetch(`${API_BASE}/api/rag/fewshots`);
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
    body: JSON.stringify({ question, sql }),
  });
  if (!res.ok) throw new Error(`Create fewshot error: ${res.status}`);
  return res.json();
}
