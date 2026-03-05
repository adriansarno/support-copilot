"use client";

import { X, FileText, Globe, Database, Ticket } from "lucide-react";

interface DocumentViewerProps {
  title: string;
  content: string;
  sourceType: string;
  chunkId: string;
  onClose: () => void;
}

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  pdf: <FileText className="w-4 h-4" />,
  html: <Globe className="w-4 h-4" />,
  confluence: <Database className="w-4 h-4" />,
  ticket: <Ticket className="w-4 h-4" />,
};

export default function DocumentViewer({
  title,
  content,
  sourceType,
  chunkId,
  onClose,
}: DocumentViewerProps) {
  return (
    <div className="h-full flex flex-col border-l border-[hsl(var(--border))]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[hsl(var(--border))]">
        <div className="flex items-center gap-2">
          {SOURCE_ICONS[sourceType] || <FileText className="w-4 h-4" />}
          <h3 className="font-medium text-sm truncate">{title}</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-[hsl(var(--muted))] transition"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="mb-3 flex items-center gap-2 text-xs text-[hsl(var(--muted-foreground))]">
          <span className="px-2 py-0.5 rounded-full bg-[hsl(var(--muted))]">{sourceType}</span>
          <span className="font-mono">{chunkId}</span>
        </div>
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <SourceHighlight content={content} />
        </div>
      </div>
    </div>
  );
}

function SourceHighlight({ content }: { content: string }) {
  return (
    <div className="whitespace-pre-wrap text-sm leading-relaxed">
      {content}
    </div>
  );
}
