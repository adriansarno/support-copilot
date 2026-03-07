"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { MessageSquare, Zap, FileText, ThumbsUp, Upload } from "lucide-react";
import UploadModal from "@/components/upload/UploadModal";

export default function Home() {
  const router = useRouter();
  const [showUpload, setShowUpload] = useState(false);

  const features = [
    {
      icon: <MessageSquare className="w-6 h-6" />,
      title: "Agent-Style Chat",
      description: "Ask questions about products, policies, and procedures. Get cited answers from your knowledge base.",
    },
    {
      icon: <Zap className="w-6 h-6" />,
      title: "Suggest Reply",
      description: "Paste a ticket and get a draft customer-facing reply grounded in documentation.",
    },
    {
      icon: <FileText className="w-6 h-6" />,
      title: "Source Trace",
      description: "See exactly which documents were used to generate each answer. Click to view the full source.",
    },
    {
      icon: <ThumbsUp className="w-6 h-6" />,
      title: "Feedback Loop",
      description: "Rate answers with thumbs up/down to continuously improve the system.",
    },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <div className="flex-1 flex items-center justify-center p-8">
        <div className="max-w-3xl w-full space-y-12">
          <div className="text-center space-y-4">
            <h1 className="text-4xl font-bold tracking-tight">Support Copilot</h1>
            <p className="text-lg text-[hsl(var(--muted-foreground))]">
              AI-powered customer support assistant with RAG retrieval, citations, and answer grading.
            </p>
            <div className="mt-4 flex gap-3 justify-center">
              <button
                onClick={() => router.push("/chat")}
                className="px-6 py-3 bg-[hsl(var(--brand))] text-white rounded-lg font-medium
                           hover:opacity-90 transition text-sm"
              >
                Start Chatting
              </button>
              <button
                onClick={() => setShowUpload(true)}
                className="px-6 py-3 border border-[hsl(var(--border))] rounded-lg font-medium
                           hover:bg-[hsl(var(--muted))] transition text-sm flex items-center gap-2"
              >
                <Upload className="w-4 h-4" />
                Upload Documents
              </button>
            </div>
            {showUpload && <UploadModal onClose={() => setShowUpload(false)} />}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {features.map((f) => (
              <div
                key={f.title}
                className="p-5 rounded-xl border border-[hsl(var(--border))] space-y-2
                           hover:shadow-md transition"
              >
                <div className="text-[hsl(var(--brand))]">{f.icon}</div>
                <h3 className="font-semibold">{f.title}</h3>
                <p className="text-sm text-[hsl(var(--muted-foreground))]">{f.description}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
