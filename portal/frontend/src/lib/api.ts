const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchDashboard<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}/api/dashboard/${endpoint}`);
  if (!res.ok) throw new Error(`Dashboard API error: ${res.status}`);
  return res.json();
}
