"use client";

import { useState } from "react";
import { Zap, X } from "lucide-react";
import { suggestReply, SuggestReplyResponse } from "@/services/api";

interface SuggestReplyButtonProps {
  onReplyGenerated: (reply: string, sources: SuggestReplyResponse["sources"]) => void;
}

export default function SuggestReplyButton({ onReplyGenerated }: SuggestReplyButtonProps) {
  const [open, setOpen] = useState(false);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    if (!subject.trim() || !body.trim()) return;
    setLoading(true);
    try {
      const result = await suggestReply(subject, body, notes);
      onReplyGenerated(result.reply, result.sources);
      setOpen(false);
      setSubject("");
      setBody("");
      setNotes("");
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg
                   border border-[hsl(var(--border))] hover:bg-[hsl(var(--muted))] transition"
      >
        <Zap className="w-3.5 h-3.5" />
        Suggest Reply
      </button>
    );
  }

  return (
    <div className="rounded-xl border border-[hsl(var(--border))] p-4 space-y-3 bg-[hsl(var(--background))]">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">Suggest Reply</h3>
        <button onClick={() => setOpen(false)} className="p-1 hover:bg-[hsl(var(--muted))] rounded">
          <X className="w-4 h-4" />
        </button>
      </div>
      <input
        value={subject}
        onChange={(e) => setSubject(e.target.value)}
        placeholder="Ticket subject"
        className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))]
                   bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--ring))]"
      />
      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="Customer message"
        rows={4}
        className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))]
                   bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--ring))] resize-none"
      />
      <input
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        placeholder="Agent notes (optional)"
        className="w-full px-3 py-2 text-sm rounded-lg border border-[hsl(var(--border))]
                   bg-[hsl(var(--background))] focus:outline-none focus:ring-2 focus:ring-[hsl(var(--ring))]"
      />
      <button
        onClick={handleSubmit}
        disabled={loading || !subject.trim() || !body.trim()}
        className="w-full py-2 text-sm font-medium rounded-lg bg-[hsl(var(--brand))] text-white
                   hover:opacity-90 disabled:opacity-50 transition"
      >
        {loading ? "Generating..." : "Generate Reply"}
      </button>
    </div>
  );
}
