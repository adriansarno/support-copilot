"use client";

import { FileText, Globe, Database, Ticket, ChevronRight } from "lucide-react";

interface CitationCardProps {
  sourceIndex: number;
  title: string;
  sourceType: string;
  contentSnippet: string;
  score?: number;
  onClick: () => void;
}

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText className="w-3.5 h-3.5" />,
  html: <Globe className="w-3.5 h-3.5" />,
  confluence: <Database className="w-3.5 h-3.5" />,
  ticket: <Ticket className="w-3.5 h-3.5" />,
};

export default function CitationCard({
  sourceIndex,
  title,
  sourceType,
  contentSnippet,
  score,
  onClick,
}: CitationCardProps) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left p-3 rounded-lg border border-[hsl(var(--border))]
                 hover:bg-[hsl(var(--muted))]/50 transition space-y-1.5 group"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs">
          <span className="px-1.5 py-0.5 bg-[hsl(var(--brand))]/10 text-[hsl(var(--brand))] rounded font-mono font-medium">
            {sourceIndex}
          </span>
          {SOURCE_ICONS[sourceType] || <FileText className="w-3.5 h-3.5" />}
          <span className="font-medium truncate">{title}</span>
        </div>
        <ChevronRight className="w-3.5 h-3.5 opacity-0 group-hover:opacity-100 transition" />
      </div>
      <p className="text-xs text-[hsl(var(--muted-foreground))] line-clamp-2">{contentSnippet}</p>
      {score !== undefined && (
        <div className="text-[10px] text-[hsl(var(--muted-foreground))]">
          Score: {score.toFixed(3)}
        </div>
      )}
    </button>
  );
}
