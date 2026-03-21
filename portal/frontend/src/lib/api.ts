const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDashboard<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api/dashboard/${endpoint}`);
  if (!res.ok) throw new Error(`Dashboard API error: ${res.status}`);
  return res.json();
}

export async function fetchSessions<T>(): Promise<T> {
  const res = await fetch(`${API_BASE}/api/history/sessions`);
  if (!res.ok) throw new Error(`History API error: ${res.status}`);
  return res.json();
}

export async function fetchMessages<T>(sessionId: string): Promise<T> {
  const res = await fetch(
    `${API_BASE}/api/history/sessions/${sessionId}/messages`
  );
  if (!res.ok) throw new Error(`Messages API error: ${res.status}`);
  return res.json();
}

export async function fetchRequests<T>(): Promise<T> {
  const res = await fetch(`${API_BASE}/api/requests`);
  if (!res.ok) throw new Error(`Requests API error: ${res.status}`);
  return res.json();
}

export async function createRequest(
  title: string,
  description?: string
): Promise<{ id: string; status: string }> {
  const res = await fetch(`${API_BASE}/api/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title, description }),
  });
  if (!res.ok) throw new Error(`Create request error: ${res.status}`);
  return res.json();
}

export async function checkHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error(`Health check failed: ${res.status}`);
  return res.json();
}
