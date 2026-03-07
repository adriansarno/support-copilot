import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "change-me-in-production";

const client = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
  },
});

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Citation {
  source_index: number;
  chunk_id: string;
  title: string;
  source_type: string;
  content_snippet: string;
}

export interface Grade {
  relevance: number;
  faithfulness: number;
  completeness: number;
  explanation: string;
  low_confidence: boolean;
}

export interface Source {
  chunk_id: string;
  title: string;
  source_type: string;
  content: string;
  score: number;
}

export interface PromptMetadata {
  prompt_name: string;
  prompt_version: string;
  prompt_hash: string;
}

export interface ChatResponse {
  chat_id: string;
  message_id: string;
  answer: string;
  citations: Citation[];
  grade: Grade | null;
  sources: Source[];
  prompt_metadata: PromptMetadata | null;
}

export interface ChatListItem {
  chat_id: string;
  title: string;
  created_at: string;
  message_count: number;
}

export interface ChatHistory {
  chat_id: string;
  messages: { role: string; content: string }[];
  created_at: string;
}

export interface SuggestReplyResponse {
  reply: string;
  citations: Citation[];
  sources: Source[];
  prompt_metadata: PromptMetadata | null;
}

export interface FeedbackResponse {
  feedback_id: string;
  status: string;
}

// ---------------------------------------------------------------------------
// Chat API
// ---------------------------------------------------------------------------

export async function sendMessage(
  message: string,
  chatId?: string | null,
  options?: { top_k?: number; skip_grading?: boolean }
): Promise<ChatResponse> {
  const resp = await client.post<ChatResponse>("/chat/", {
    message,
    chat_id: chatId || undefined,
    top_k: options?.top_k ?? 10,
    skip_grading: options?.skip_grading ?? false,
  });
  return resp.data;
}

export async function listChats(): Promise<ChatListItem[]> {
  const resp = await client.get<ChatListItem[]>("/chat/");
  return resp.data;
}

export async function getChat(chatId: string): Promise<ChatHistory> {
  const resp = await client.get<ChatHistory>(`/chat/${chatId}`);
  return resp.data;
}

// ---------------------------------------------------------------------------
// Suggest Reply API
// ---------------------------------------------------------------------------

export async function suggestReply(
  ticketSubject: string,
  ticketBody: string,
  agentNotes?: string
): Promise<SuggestReplyResponse> {
  const resp = await client.post<SuggestReplyResponse>("/suggest-reply/", {
    ticket_subject: ticketSubject,
    ticket_body: ticketBody,
    agent_notes: agentNotes || "",
  });
  return resp.data;
}

// ---------------------------------------------------------------------------
// Feedback API
// ---------------------------------------------------------------------------

// ---------------------------------------------------------------------------
// Upload API
// ---------------------------------------------------------------------------

export interface UploadResponse {
  uploaded: string[];
  errors: string[];
  bucket?: string;
  message: string;
}

export async function uploadDocuments(files: File[]): Promise<UploadResponse> {
  const formData = new FormData();
  for (const file of files) {
    formData.append("files", file);
  }
  // Use fetch so browser sets multipart/form-data with boundary (axios default Content-Type would break this)
  const resp = await fetch(`${API_URL}/upload/`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
    body: formData,
  });
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({ detail: resp.statusText }));
    throw new Error(typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail));
  }
  return resp.json();
}

// ---------------------------------------------------------------------------
// Feedback API
// ---------------------------------------------------------------------------

export async function submitFeedback(
  chatId: string,
  messageId: string,
  rating: number,
  comment?: string
): Promise<FeedbackResponse> {
  const resp = await client.post<FeedbackResponse>("/feedback/", {
    chat_id: chatId,
    message_id: messageId,
    rating,
    comment: comment || "",
  });
  return resp.data;
}
