const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export async function fetchTickets<T>(): Promise<T> {
  const res = await fetch(`${API_BASE}/api/tickets`);
  if (!res.ok) throw new Error(`Tickets API error: ${res.status}`);
  return res.json();
}

export async function updateTicketStatus(
  requestId: string,
  status: string,
  comment?: string
): Promise<void> {
  const res = await fetch(`${API_BASE}/api/tickets/${requestId}/status`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, comment }),
  });
  if (!res.ok) throw new Error(`Update ticket error: ${res.status}`);
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
