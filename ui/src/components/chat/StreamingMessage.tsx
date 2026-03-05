"use client";

import { Bot, Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface StreamingMessageProps {
  content: string;
  isLoading: boolean;
}

export default function StreamingMessage({ content, isLoading }: StreamingMessageProps) {
  if (!isLoading && !content) return null;

  return (
    <div className="flex gap-3 justify-start">
      <div className="w-8 h-8 rounded-full bg-[hsl(var(--brand))]/10 flex items-center justify-center flex-shrink-0">
        <Bot className="w-4 h-4 text-[hsl(var(--brand))]" />
      </div>
      <div className="max-w-[75%] rounded-2xl px-4 py-3 text-sm bg-[hsl(var(--muted))]">
        {content ? (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
          </div>
        ) : (
          <div className="flex items-center gap-2 text-[hsl(var(--muted-foreground))]">
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>Thinking...</span>
          </div>
        )}
      </div>
    </div>
  );
}
