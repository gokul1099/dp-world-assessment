import type { SourceRef } from "@/types/licence";

interface SourceBadgeProps {
  source: SourceRef;
  /** When given, the badge becomes a button that shows that page in the viewer. */
  onShowPage?: (page: number) => void;
}

const badgeClass =
  "inline-flex items-center rounded-full bg-zinc-200/70 px-2 py-0.5 text-xs font-medium text-zinc-700 dark:bg-zinc-700/60 dark:text-zinc-200";

// Citation chip shown next to an answer or extracted field.
export function SourceBadge({ source, onShowPage }: SourceBadgeProps) {
  if (!onShowPage) {
    return (
      <span className={badgeClass} title={source.snippet ?? undefined}>
        Page {source.page}
      </span>
    );
  }
  return (
    <button
      type="button"
      onClick={() => onShowPage(source.page)}
      title={source.snippet ? `Source: ${source.snippet}` : `Show page ${source.page}`}
      aria-label={`Show page ${source.page} of the document`}
      className={`${badgeClass} transition-colors hover:bg-blue-100 hover:text-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:hover:bg-blue-900 dark:hover:text-blue-100`}
    >
      Page {source.page}
    </button>
  );
}
