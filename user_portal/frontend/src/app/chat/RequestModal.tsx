"use client";

import { useEffect, useState } from "react";
import { X } from "lucide-react";
import { createDraft, createRequest, type ChatContext } from "@/lib/api";
import RequestForm from "../requests/RequestForm";

type Props = {
  open: boolean;
  onClose: () => void;
  initialTitle: string;
  chatContext: ChatContext;
  sessionId: string | null;
  onResult?: (kind: "draft" | "submitted") => void;
};

export default function RequestModal({
  open,
  onClose,
  initialTitle,
  chatContext,
  sessionId,
  onResult,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Escape to close + body-scroll-lock
  useEffect(() => {
    if (!open) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && !busy) onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose, busy]);

  if (!open) return null;

  async function handleSubmit(data: { title: string; description: string }) {
    setBusy(true);
    setError(null);
    try {
      await createRequest({
        title: data.title,
        description: data.description,
        chat_context: chatContext,
        session_id: sessionId,
      });
      onResult?.("submitted");
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function handleSaveDraft(data: { title: string; description: string }) {
    setBusy(true);
    setError(null);
    try {
      await createDraft({
        title: data.title,
        description: data.description,
        chat_context: chatContext,
        session_id: sessionId,
      });
      onResult?.("draft");
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      onClick={() => !busy && onClose()}
    >
      <div
        className="w-full max-w-2xl max-h-[90vh] overflow-y-auto rounded-xl bg-white shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-[var(--card-border)] px-5 py-3">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">
            Request a Dashboard
          </h3>
          <button
            onClick={onClose}
            disabled={busy}
            className="text-[var(--text-muted)] hover:text-[var(--text-secondary)] disabled:opacity-40"
          >
            <X size={18} />
          </button>
        </div>

        <div className="p-5">
          {error && (
            <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          <RequestForm
            mode="create"
            initial={{ title: initialTitle, description: "" }}
            chatContext={chatContext}
            showSaveDraft
            onSubmit={handleSubmit}
            onSaveDraft={handleSaveDraft}
            onCancel={onClose}
            busy={busy}
          />
        </div>
      </div>
    </div>
  );
}
