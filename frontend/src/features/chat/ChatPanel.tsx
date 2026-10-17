"use client";

interface ChatPanelProps {
  documentId: string;
}

// Feature 5 — ask questions answered only from the uploaded document (askDocument).
export function ChatPanel(_props: ChatPanelProps) {
  return <section aria-label="Ask the document">Chat panel</section>;
}
