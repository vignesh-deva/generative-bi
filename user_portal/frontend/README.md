# frontend/

Next.js + Tailwind — User portal for the Generative BI Agent.

## Pages

| Sidebar Nav | Route | Description |
|-------------|-------|-------------|
| **Dashboard** | `/` | 3×3 grid — 3 KPI cards + 6 recharts charts |
| **Chat** | `/chat` | NL-to-SQL chat with SSE streaming, SQL viewer, collapsible pipeline steps panel |
| **Recent** | `/recent` | Past chat sessions with relative timestamps, click to resume |
| **Requests** | `/requests` | Dashboard request lifecycle — Drafts / Active / Closed tabs, comment threads |

Unauthenticated visits to any route are redirected to `/login` by `src/middleware.ts`. The login form posts credentials to the backend and stores the returned JWT as a cookie.

## Stack

- Next.js (App Router)
- Tailwind CSS
- Runs on port 3000

## Getting Started

```bash
npm install
npm run dev   # starts on http://localhost:3000
```

Set `NEXT_PUBLIC_API_URL` in the environment (or it defaults to `http://localhost:8000`).
