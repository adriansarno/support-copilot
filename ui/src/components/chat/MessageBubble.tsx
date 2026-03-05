"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { User, Bot } from "lucide-react";

interface Citation {
  source_index: number;
  chunk_id: string;
  title: string;
  source_type: string;
  content_snippet: string;
}

interface Grade {
  relevance: number;
  faithfulness: number;
  completeness: number;
  low_confidence: boolean;
}

export interface MessageProps {
  role: "user" | "assistant";
  content: string;
  messageId?: string;
  citations?: Citation[];
  grade?: Grade | null;
  onCitationClick?: (citation: Citation) => void;
  feedbackSlot?: React.ReactNode;
}

export default function MessageBubble({
  role,
  content,
  citations,
  grade,
  onCitationClick,
  feedbackSlot,
}: MessageProps) {
  const isUser = role === "user";

  return (
    <div className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-[hsl(var(--brand))]/10 flex items-center justify-center flex-shrink-0">
          <Bot className="w-4 h-4 text-[hsl(var(--brand))]" />
        </div>
      )}

      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
          isUser
            ? "bg-[hsl(var(--brand))] text-white"
            : "bg-[hsl(var(--muted))]"
        }`}
      >
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>

        {grade?.low_confidence && (
          <div className="mt-2 text-xs px-2 py-1 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 inline-block">
            Low confidence
          </div>
        )}

        {citations && citations.length > 0 && (
          <div className="mt-3 border-t border-[hsl(var(--border))]/40 pt-2">
            <p className="text-xs font-medium opacity-70 mb-1">Sources</p>
            <div className="flex flex-wrap gap-1">
              {citations.map((c) => (
                <button
                  key={c.chunk_id}
                  onClick={() => onCitationClick?.(c)}
                  className="text-xs px-2 py-0.5 rounded-full bg-[hsl(var(--background))]/60
                             hover:bg-[hsl(var(--background))] border border-[hsl(var(--border))]/50
                             transition"
                >
                  [{c.source_index}] {c.title}
                </button>
              ))}
            </div>
          </div>
        )}

        {feedbackSlot && <div className="mt-2">{feedbackSlot}</div>}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-[hsl(var(--muted))] flex items-center justify-center flex-shrink-0">
          <User className="w-4 h-4" />
        </div>
      )}
    </div>
  );
}
