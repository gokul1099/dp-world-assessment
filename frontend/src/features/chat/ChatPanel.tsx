"use client";

import { useEffect, useRef, useState } from "react";

import { ApiError } from "@/api/client";
import { askDocument } from "@/api/documents";
import type { SourceRef } from "@/types/licence";

import { SourceBadge } from "./SourceBadge";

interface ChatPanelProps {
  documentId: string;
  /** Holder's full name from the saved licence, used for the greeting. */
  holderName: string | null;
  onEditDetails: () => void;
}

type Message =
  | { role: "user"; text: string }
  | { role: "assistant"; text: string; found: boolean; sources: SourceRef[] }
  | { role: "error"; text: string };

const SUGGESTED_QUESTIONS = [
  "What is the licence expiry date?",
  "What vehicles am I authorised to drive?",
  "What is the licence number?",
];

const MAX_QUESTION_LENGTH = 500;

/** "JANE MARIE TESTER" → "Jane" */
function firstName(fullName: string | null): string | null {
  const first = fullName?.trim().split(/\s+/)[0];
  if (!first) return null;
  return first.charAt(0).toUpperCase() + first.slice(1).toLowerCase();
}

// Feature 5 — ask questions answered only from the uploaded document.
export function ChatPanel({ documentId, holderName, onEditDetails }: ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const name = firstName(holderName);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, asking]);

  async function ask(text: string) {
    const trimmed = text.trim();
    if (!trimmed || asking) return;

    setMessages((prev) => [...prev, { role: "user", text: trimmed }]);
    setQuestion("");
    setAsking(true);
    try {
      const response = await askDocument(documentId, trimmed);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: response.answer,
          found: response.found,
          sources: response.sources,
        },
      ]);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Something went wrong. Please try again.";
      setMessages((prev) => [...prev, { role: "error", text: message }]);
    } finally {
      setAsking(false);
      inputRef.current?.focus();
    }
  }

  function handleKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter adds a new line.
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      ask(question);
    }
  }

  return (
    <section
      aria-labelledby="chat-title"
      className="flex w-full flex-col rounded-2xl border border-zinc-200 bg-white shadow-sm dark:border-zinc-800 dark:bg-zinc-950"
    >
      <header className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-200 px-6 py-5 dark:border-zinc-800">
        <div>
          <h2 id="chat-title" className="text-xl font-semibold">
            {name ? `Welcome, ${name}!` : "Welcome!"}
          </h2>
          <p className="mt-1 text-sm text-zinc-600 dark:text-zinc-400">
            Your licence details are saved. Ask me anything about your driving licence.
          </p>
        </div>
        <button
          type="button"
          onClick={onEditDetails}
          className="text-sm font-medium text-blue-700 underline-offset-4 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:text-blue-400"
        >
          Edit details
        </button>
      </header>

      <div
        className="flex min-h-72 flex-col gap-4 overflow-y-auto px-6 py-5 sm:max-h-[28rem]"
        aria-live="polite"
      >
        {messages.length === 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-zinc-600 dark:text-zinc-400">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED_QUESTIONS.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => ask(q)}
                  className="rounded-full border border-zinc-300 px-3 py-1.5 text-sm transition-colors hover:bg-zinc-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 dark:border-zinc-700 dark:hover:bg-zinc-900"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <ChatMessage key={index} message={message} />
        ))}

        {asking && (
          <div className="flex items-center gap-2 text-sm text-zinc-500" role="status">
            <span
              aria-hidden="true"
              className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-300 border-t-zinc-900 dark:border-zinc-700 dark:border-t-zinc-100"
            />
            Looking through your licence…
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form
        className="flex items-end gap-2 border-t border-zinc-200 p-4 dark:border-zinc-800"
        onSubmit={(e) => {
          e.preventDefault();
          ask(question);
        }}
      >
        <label htmlFor="chat-question" className="sr-only">
          Ask a question about your licence
        </label>
        <textarea
          id="chat-question"
          ref={inputRef}
          rows={1}
          value={question}
          maxLength={MAX_QUESTION_LENGTH}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your licence, e.g. When does it expire?"
          className="max-h-32 min-h-10 flex-1 resize-none rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 placeholder:text-zinc-400 focus:border-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-600/20 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-100"
        />
        <button
          type="submit"
          disabled={asking || !question.trim()}
          className="inline-flex h-10 items-center justify-center rounded-lg bg-zinc-900 px-4 text-sm font-medium text-white transition-colors hover:bg-zinc-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Send
        </button>
      </form>
    </section>
  );
}

function ChatMessage({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="self-end rounded-2xl rounded-br-sm bg-zinc-900 px-4 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900">
        {message.text}
      </div>
    );
  }

  if (message.role === "error") {
    return (
      <div className="self-start rounded-2xl rounded-bl-sm border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200">
        {message.text}
      </div>
    );
  }

  return (
    <div
      className={`flex max-w-[85%] flex-col gap-2 self-start rounded-2xl rounded-bl-sm px-4 py-2 text-sm ${
        message.found
          ? "bg-zinc-100 text-zinc-900 dark:bg-zinc-800 dark:text-zinc-100"
          : "border border-dashed border-amber-400 bg-amber-50 text-amber-900 dark:border-amber-700 dark:bg-amber-950 dark:text-amber-100"
      }`}
    >
      <p className="whitespace-pre-wrap">{message.text}</p>
      {message.sources.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.sources.map((source, i) => (
            <SourceBadge key={`${source.page}-${i}`} source={source} />
          ))}
        </div>
      )}
    </div>
  );
}
