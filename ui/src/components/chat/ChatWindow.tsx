"use client";

import { useState, useRef, useEffect } from "react";
import { Send } from "lucide-react";
import MessageBubble, { MessageProps } from "./MessageBubble";
import StreamingMessage from "./StreamingMessage";
import ThumbsUpDown from "../feedback/ThumbsUpDown";

interface ChatWindowProps {
  messages: MessageProps[];
  isLoading: boolean;
  streamingContent: string;
  onSendMessage: (message: string) => void;
  onCitationClick?: (citation: any) => void;
}

export default function ChatWindow({
  messages,
  isLoading,
  streamingContent,
  onSendMessage,
  onCitationClick,
}: ChatWindowProps) {
  const [input, setInput] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isLoading) return;
    setInput("");
    onSendMessage(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="flex-1 flex items-center justify-center h-full">
            <p className="text-[hsl(var(--muted-foreground))] text-sm">
              Start a conversation by typing a message below.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <MessageBubble
            key={i}
            {...msg}
            onCitationClick={onCitationClick}
            feedbackSlot={
              msg.role === "assistant" && msg.messageId ? (
                <ThumbsUpDown chatId="" messageId={msg.messageId} />
              ) : undefined
            }
          />
        ))}

        {(isLoading || streamingContent) && (
          <StreamingMessage content={streamingContent} isLoading={isLoading} />
        )}

        <div ref={messagesEndRef} />
      </div>

      <div className="border-t border-[hsl(var(--border))] px-6 py-3">
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask a question about products, policies, or procedures..."
            rows={1}
            className="flex-1 resize-none px-4 py-2.5 text-sm rounded-xl border border-[hsl(var(--border))]
                       bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--ring))]
                       max-h-32"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading}
            className="p-2.5 rounded-xl bg-[hsl(var(--brand))] text-white hover:opacity-90
                       disabled:opacity-40 transition"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
