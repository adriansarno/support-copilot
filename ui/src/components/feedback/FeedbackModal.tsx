"use client";

import { useState } from "react";
import { X } from "lucide-react";
import { submitFeedback } from "@/services/api";

interface FeedbackModalProps {
  chatId: string;
  messageId: string;
  initialRating: number | null;
  onClose: () => void;
}

export default function FeedbackModal({
  chatId,
  messageId,
  initialRating,
  onClose,
}: FeedbackModalProps) {
  const [comment, setComment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!comment.trim()) return;
    setSubmitting(true);
    await submitFeedback(chatId, messageId, initialRating ?? 0, comment);
    setSubmitting(false);
    setSubmitted(true);
    setTimeout(onClose, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-[hsl(var(--background))] rounded-xl border border-[hsl(var(--border))] p-6 w-full max-w-md shadow-lg space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold">Leave Feedback</h3>
          <button onClick={onClose} className="p-1 rounded hover:bg-[hsl(var(--muted))]">
            <X className="w-4 h-4" />
          </button>
        </div>

        {submitted ? (
          <p className="text-sm text-green-600">Thank you for your feedback!</p>
        ) : (
          <>
            <textarea
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="What could be improved? What was helpful?"
              rows={4}
              className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))]
                         bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--ring))] resize-none"
            />
            <div className="flex justify-end gap-2">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm rounded-lg border border-[hsl(var(--border))]
                           hover:bg-[hsl(var(--muted))] transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={submitting || !comment.trim()}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-[hsl(var(--brand))] text-white
                           hover:opacity-90 disabled:opacity-50 transition"
              >
                {submitting ? "Sending..." : "Submit"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
