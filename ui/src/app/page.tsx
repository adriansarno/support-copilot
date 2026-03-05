"use client";

import { useRouter } from "next/navigation";
import { MessageSquare, Zap, FileText, ThumbsUp } from "lucide-react";

export default function Home() {
  const router = useRouter();

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
            <button
              onClick={() => router.push("/chat")}
              className="mt-4 px-6 py-3 bg-[hsl(var(--brand))] text-white rounded-lg font-medium
                         hover:opacity-90 transition text-sm"
            >
              Start Chatting
            </button>
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
