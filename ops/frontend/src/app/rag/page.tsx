"use client";

import { useEffect, useState, FormEvent } from "react";
import { Plus, BookOpen, Trash2 } from "lucide-react";
import { fetchFewshots, createFewshot } from "@/lib/api";

type Fewshot = {
  id: number;
  question: string;
  sql: string;
  created_at: string;
};

export default function RagCurationPage() {
  const [fewshots, setFewshots] = useState<Fewshot[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [question, setQuestion] = useState("");
  const [sql, setSql] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function load() {
    try {
      const data = await fetchFewshots<Fewshot[]>();
      setFewshots(data);
    } catch (e) {
      console.error("Failed to load fewshots:", e);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!question.trim() || !sql.trim() || submitting) return;
    setSubmitting(true);
    try {
      await createFewshot(question.trim(), sql.trim());
      setQuestion("");
      setSql("");
      setShowForm(false);
      setLoading(true);
      await load();
    } catch (e) {
      console.error("Failed to create fewshot:", e);
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
          <p className="text-sm text-[var(--text-muted)]">
            Loading few-shot examples...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-bold text-[var(--text-primary)]">
            RAG Curation
          </h1>
          <p className="mt-0.5 text-sm text-[var(--text-muted)]">
            Manage few-shot NL-to-SQL examples for retrieval-augmented generation
          </p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-700"
        >
          <Plus size={16} />
          Add Example
        </button>
      </div>

      {/* Add form */}
      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="rounded-xl border border-[var(--card-border)] bg-white p-5 shadow-sm"
        >
          <h2 className="text-sm font-semibold text-[var(--text-primary)]">
            New Few-Shot Example
          </h2>
          <div className="mt-3 space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                Natural Language Question
              </label>
              <input
                type="text"
                placeholder="e.g., What are the top 5 products by revenue?"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                className="w-full rounded-lg border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-violet-400 focus:ring-1 focus:ring-violet-400"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-[var(--text-secondary)]">
                SQL Query
              </label>
              <textarea
                placeholder="SELECT p.name, SUM(s.qty_sold * s.selling_price) AS revenue..."
                value={sql}
                onChange={(e) => setSql(e.target.value)}
                rows={4}
                className="w-full resize-none rounded-lg border border-[var(--card-border)] bg-[var(--background)] px-3 py-2 font-mono text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-violet-400 focus:ring-1 focus:ring-violet-400"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={!question.trim() || !sql.trim() || submitting}
                className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-violet-700 disabled:opacity-40"
              >
                {submitting ? "Adding..." : "Add Example"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="rounded-lg border border-[var(--card-border)] px-4 py-2 text-sm text-[var(--text-secondary)] transition-colors hover:bg-[var(--background)]"
              >
                Cancel
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Fewshots list */}
      {fewshots.length === 0 ? (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100">
            <BookOpen size={24} className="text-slate-400" />
          </div>
          <p className="text-sm text-[var(--text-muted)]">
            No few-shot examples yet. Add examples to improve SQL generation accuracy.
          </p>
        </div>
      ) : (
        <div className="space-y-2">
          {fewshots.map((fs) => (
            <div
              key={fs.id}
              className="rounded-xl border border-[var(--card-border)] bg-white px-5 py-4 shadow-sm"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[var(--text-primary)]">
                    {fs.question}
                  </p>
                  <pre className="mt-2 overflow-x-auto rounded-lg bg-slate-50 p-2.5 text-xs text-slate-600">
                    <code>{fs.sql}</code>
                  </pre>
                  {fs.created_at && (
                    <p className="mt-2 text-xs text-[var(--text-muted)]">
                      Added{" "}
                      {new Date(fs.created_at).toLocaleDateString("en-IN", {
                        day: "numeric",
                        month: "short",
                        year: "numeric",
                      })}
                    </p>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
