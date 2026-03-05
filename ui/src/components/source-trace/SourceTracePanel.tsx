"use client";

import { ChevronLeft, ChevronRight, Info } from "lucide-react";
import CitationCard from "./CitationCard";

interface Source {
  chunk_id: string;
  title: string;
  source_type: string;
  content: string;
  score: number;
}

interface PromptMetadata {
  prompt_name: string;
  prompt_version: string;
  prompt_hash: string;
}

interface SourceTracePanelProps {
  sources: Source[];
  promptMetadata?: PromptMetadata | null;
  collapsed: boolean;
  onToggle: () => void;
  onSourceClick: (source: Source) => void;
}

export default function SourceTracePanel({
  sources,
  promptMetadata,
  collapsed,
  onToggle,
  onSourceClick,
}: SourceTracePanelProps) {
  return (
    <div
      className={`border-l border-[hsl(var(--border))] flex flex-col transition-all duration-200
        ${collapsed ? "w-10" : "w-80"}`}
    >
      <div className="flex items-center justify-between px-3 py-3 border-b border-[hsl(var(--border))]">
        {!collapsed && <span className="text-sm font-semibold">Source Trace</span>}
        <button
          onClick={onToggle}
          className="p-1 rounded hover:bg-[hsl(var(--muted))] transition"
          aria-label={collapsed ? "Expand" : "Collapse"}
        >
          {collapsed ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>

      {!collapsed && (
        <div className="flex-1 overflow-y-auto p-3 space-y-3">
          {promptMetadata && (
            <div className="p-2 rounded-lg bg-[hsl(var(--muted))]/50 text-xs space-y-0.5">
              <div className="flex items-center gap-1 font-medium">
                <Info className="w-3 h-3" />
                Prompt Info
              </div>
              <div className="text-[hsl(var(--muted-foreground))]">
                {promptMetadata.prompt_name} / {promptMetadata.prompt_version}
              </div>
              <div className="font-mono text-[10px] text-[hsl(var(--muted-foreground))]">
                hash: {promptMetadata.prompt_hash}
              </div>
            </div>
          )}

          {sources.length === 0 ? (
            <p className="text-xs text-[hsl(var(--muted-foreground))] text-center py-8">
              No sources for this message.
            </p>
          ) : (
            sources.map((source, i) => (
              <CitationCard
                key={source.chunk_id}
                sourceIndex={i + 1}
                title={source.title}
                sourceType={source.source_type}
                contentSnippet={source.content}
                score={source.score}
                onClick={() => onSourceClick(source)}
              />
            ))
          )}
        </div>
      )}
    </div>
  );
}
