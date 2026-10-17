import type { SourceRef } from "@/types/licence";

// Citation chip shown next to an answer or extracted field.
export function SourceBadge({ source }: { source: SourceRef }) {
  return (
    <span
      className="inline-flex items-center rounded-full bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-800 dark:text-zinc-300"
      title={source.snippet ?? undefined}
    >
      Page {source.page}
    </span>
  );
}
