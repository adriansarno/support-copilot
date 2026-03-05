"use client";

import { Plus, MessageCircle } from "lucide-react";

interface ChatItem {
  chat_id: string;
  title: string;
  created_at: string;
  message_count: number;
}

interface SidebarProps {
  chats: ChatItem[];
  activeChatId: string | null;
  onSelectChat: (chatId: string) => void;
  onNewChat: () => void;
}

export default function Sidebar({ chats, activeChatId, onSelectChat, onNewChat }: SidebarProps) {
  return (
    <aside className="w-64 border-r border-[hsl(var(--border))] flex flex-col h-full bg-[hsl(var(--muted))]/30">
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
                     border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))] transition"
        >
          <Plus className="w-4 h-4" />
          New Chat
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 space-y-1">
        {chats.map((chat) => (
          <button
            key={chat.chat_id}
            onClick={() => onSelectChat(chat.chat_id)}
            className={`w-full text-left px-3 py-2 rounded-lg text-sm flex items-center gap-2 transition
              ${
                chat.chat_id === activeChatId
                  ? "bg-[hsl(var(--brand))]/10 text-[hsl(var(--brand))] font-medium"
                  : "hover:bg-[hsl(var(--muted))]"
              }`}
          >
            <MessageCircle className="w-3.5 h-3.5 flex-shrink-0" />
            <span className="truncate">{chat.title || "Untitled"}</span>
          </button>
        ))}
      </nav>
    </aside>
  );
}
