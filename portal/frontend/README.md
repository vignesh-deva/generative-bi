# frontend/

Next.js + Tailwind — User portal for the Generative BI Agent.

## Pages

| Sidebar Nav | Route | Description |
|-------------|-------|-------------|
| **Dashboard** | `/dashboard` | Static 2x2 chart grid with hardcoded FMCG data |
| **Request New** | `/requests/new` | Submit a request for a new dashboard/report |
| **+ New Chat** | `/chat` | NL → SQL chat with streaming agent responses |
| **Recent** | `/chat/history` | Past chat sessions (click to view) |

Requests have a detail view with viewable and editable comments.

## Stack

- Next.js (App Router)
- Tailwind CSS
- Runs on port 3000

## Getting Started

```bash
npm install
npm run dev   # starts on http://localhost:3000
```
