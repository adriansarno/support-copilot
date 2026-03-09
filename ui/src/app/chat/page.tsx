"use client";

import { useState, useCallback, useEffect } from "react";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import ChatWindow from "@/components/chat/ChatWindow";
import SuggestReplyButton from "@/components/chat/SuggestReplyButton";
import SourceTracePanel from "@/components/source-trace/SourceTracePanel";
import DocumentViewer from "@/components/documents/DocumentViewer";
import { sendMessage, listChats, ChatListItem, Source, PromptMetadata, ChatResponse } from "@/services/api";

interface UIMessage {
  role: "user" | "assistant";
  content: string;
  messageId?: string;
  citations?: ChatResponse["citations"];
  grade?: ChatResponse["grade"];
}

export default function ChatPage() {
  const [chatId, setChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [chatList, setChatList] = useState<ChatListItem[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [promptMeta, setPromptMeta] = useState<PromptMetadata | null>(null);
  const [traceCollapsed, setTraceCollapsed] = useState(false);
  const [viewingDoc, setViewingDoc] = useState<Source | null>(null);

  const refreshChatList = useCallback(async () => {
    try {
      const chats = await listChats();
      setChatList(chats);
    } catch {
      // ignore
    }
  }, []);

  useEffect(() => {
    refreshChatList();
  }, [refreshChatList]);

  const handleSendMessage = async (message: string) => {
    setMessages((prev) => [...prev, { role: "user", content: message }]);
    setIsLoading(true);

    try {
      const resp = await sendMessage(message, chatId);
      if (!chatId) setChatId(resp.chat_id);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: resp.answer,
          messageId: resp.message_id,
          citations: resp.citations,
          grade: resp.grade,
        },
      ]);
      setSources(resp.sources);
      setPromptMeta(resp.prompt_metadata);
      refreshChatList();
    } catch (err: unknown) {
      const detail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      const message =
        detail ||
        "Sorry, an error occurred. Please try again.";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: message,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleNewChat = () => {
    setChatId(null);
    setMessages([]);
    setSources([]);
    setPromptMeta(null);
    setViewingDoc(null);
  };

  const handleSelectChat = async (id: string) => {
    setChatId(id);
    setMessages([]);
    setSources([]);
    setViewingDoc(null);
  };

  const handleSuggestReply = (reply: string, replySources: Source[]) => {
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: `**Suggested Reply:**\n\n${reply}` },
    ]);
    setSources(replySources);
  };

  return (
    <div className="h-screen flex flex-col">
      <Header />
      <div className="flex-1 flex overflow-hidden">
        <Sidebar
          chats={chatList}
          activeChatId={chatId}
          onSelectChat={handleSelectChat}
          onNewChat={handleNewChat}
        />

        <main className="flex-1 flex flex-col">
          <div className="flex-1 flex overflow-hidden">
            <div className="flex-1 flex flex-col">
              <ChatWindow
                messages={messages}
                isLoading={isLoading}
                streamingContent=""
                onSendMessage={handleSendMessage}
                onCitationClick={(c) => {
                  const src = sources.find((s) => s.chunk_id === c.chunk_id);
                  if (src) setViewingDoc(src);
                }}
              />
              <div className="px-6 pb-3">
                <SuggestReplyButton onReplyGenerated={handleSuggestReply} />
              </div>
            </div>

            {viewingDoc ? (
              <div className="w-96">
                <DocumentViewer
                  title={viewingDoc.title}
                  content={viewingDoc.content}
                  sourceType={viewingDoc.source_type}
                  chunkId={viewingDoc.chunk_id}
                  onClose={() => setViewingDoc(null)}
                />
              </div>
            ) : (
              <SourceTracePanel
                sources={sources}
                promptMetadata={promptMeta}
                collapsed={traceCollapsed}
                onToggle={() => setTraceCollapsed(!traceCollapsed)}
                onSourceClick={(s) => setViewingDoc(s)}
              />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
