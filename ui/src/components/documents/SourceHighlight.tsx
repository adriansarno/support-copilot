"use client";

interface SourceHighlightProps {
  content: string;
  highlightTerms?: string[];
}

export default function SourceHighlight({ content, highlightTerms = [] }: SourceHighlightProps) {
  if (highlightTerms.length === 0) {
    return <span className="whitespace-pre-wrap">{content}</span>;
  }

  const pattern = new RegExp(`(${highlightTerms.map(escapeRegex).join("|")})`, "gi");
  const parts = content.split(pattern);

  return (
    <span className="whitespace-pre-wrap">
      {parts.map((part, i) => {
        const isMatch = highlightTerms.some(
          (term) => part.toLowerCase() === term.toLowerCase()
        );
        return isMatch ? (
          <mark key={i} className="bg-yellow-200 dark:bg-yellow-800/50 rounded px-0.5">
            {part}
          </mark>
        ) : (
          <span key={i}>{part}</span>
        );
      })}
    </span>
  );
}

function escapeRegex(str: string): string {
  return str.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}
