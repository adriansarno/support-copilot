"use client";

import { useState } from "react";
import { ThumbsUp, ThumbsDown, MessageSquare } from "lucide-react";
import { submitFeedback } from "@/services/api";
import FeedbackModal from "./FeedbackModal";

interface ThumbsUpDownProps {
  chatId: string;
  messageId: string;
}

export default function ThumbsUpDown({ chatId, messageId }: ThumbsUpDownProps) {
  const [rating, setRating] = useState<number | null>(null);
  const [showModal, setShowModal] = useState(false);

  const handleRate = async (value: 1 | -1) => {
    setRating(value);
    await submitFeedback(chatId, messageId, value);
  };

  return (
    <div className="flex items-center gap-1">
      <button
        onClick={() => handleRate(1)}
        className={`p-1 rounded transition ${
          rating === 1
            ? "text-green-600 bg-green-50 dark:bg-green-900/30"
            : "text-[hsl(var(--muted-foreground))] hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20"
        }`}
        aria-label="Thumbs up"
      >
        <ThumbsUp className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => handleRate(-1)}
        className={`p-1 rounded transition ${
          rating === -1
            ? "text-red-600 bg-red-50 dark:bg-red-900/30"
            : "text-[hsl(var(--muted-foreground))] hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
        }`}
        aria-label="Thumbs down"
      >
        <ThumbsDown className="w-3.5 h-3.5" />
      </button>
      <button
        onClick={() => setShowModal(true)}
        className="p-1 rounded text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))] transition"
        aria-label="Leave comment"
      >
        <MessageSquare className="w-3.5 h-3.5" />
      </button>

      {showModal && (
        <FeedbackModal
          chatId={chatId}
          messageId={messageId}
          initialRating={rating}
          onClose={() => setShowModal(false)}
        />
      )}
    </div>
  );
}
