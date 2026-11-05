"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Compass,
  CornerDownLeft,
  LoaderCircle,
  MessageSquarePlus,
  Send,
  ShieldCheck,
  Sparkles,
} from "lucide-react";
import { useProfile } from "@/components/providers";
import { ErrorNotice, Reveal } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

const prompts = [
  "Help me think through cost versus academic depth.",
  "What should I verify before applying abroad?",
  "How should I choose my ranking priorities?",
];

export default function AssistantPage() {
  const { profile } = useProfile();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastFailed, setLastFailed] = useState<ChatMessage[] | null>(null);
  const [model, setModel] = useState<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const textarea = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    bottom.current?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
        ? "instant"
        : "smooth",
      block: "nearest",
    });
  }, [messages, busy]);
  const request = async (history: ChatMessage[]) => {
    setBusy(true);
    setError(null);
    setLastFailed(null);
    try {
      // Keep bounded context: 9 prior exchanges + current question, <=20 messages.
      const response = await api.chat(history.slice(-19), profile?.id);
      setMessages([...history, response.message]);
      setModel(response.model);
    } catch (error) {
      setError(errorMessage(error));
      setLastFailed(history);
    } finally {
      setBusy(false);
      textarea.current?.focus();
    }
  };
  const send = async (text: string) => {
    const content = text.trim();
    if (!content || busy) return;
    const history: ChatMessage[] = [...messages, { role: "user", content }];
    setMessages(history);
    setInput("");
    await request(history);
  };
  return (
    <Reveal>
      <div className="page-heading">
        <div>
          <span className="eyebrow">A LITTLE ROOM TO THINK</span>
          <h1>You don’t have to figure it out alone.</h1>
          <p>
            Talk through the possibilities with your local AI thinking partner.
          </p>
        </div>
        <button
          className="button button-outline button-small"
          disabled={busy || messages.length === 0}
          onClick={() => {
            setMessages([]);
            setError(null);
            setLastFailed(null);
            setInput("");
            textarea.current?.focus();
          }}
        >
          <MessageSquarePlus size={16} />
          New conversation
        </button>
      </div>
      <div className="assistant-layout">
        <section className="chat-panel panel">
          <div className="chat-header">
            <span className="assistant-avatar">
              <Compass size={23} />
            </span>
            <div>
              <strong>LifePilot assistant</strong>
              <small>
                {model
                  ? `Connected · ${model}`
                  : "Powered by your local Ollama model"}
              </small>
            </div>
            <span className="tag">AI · local</span>
          </div>
          <div
            className="chat-messages"
            role="log"
            aria-label="Conversation"
            aria-live="polite"
            aria-relevant="additions text"
          >
            {messages.length === 0 && (
              <div className="chat-welcome">
                <span className="chat-welcome-icon">
                  <Sparkles size={30} strokeWidth={1.4} />
                </span>
                <h2>
                  Let’s put things
                  <br />
                  into perspective.
                </h2>
                <p>
                  A question, a tradeoff, a possibility.
                  <br />
                  What’s on your mind about studying abroad?
                </p>
                <div className="prompt-list">
                  {prompts.map((prompt) => (
                    <button
                      key={prompt}
                      disabled={busy}
                      onClick={() => void send(prompt)}
                    >
                      {prompt}
                      <ArrowRight size={15} />
                    </button>
                  ))}
                </div>
              </div>
            )}
            {messages.map((message, i) => (
              <div className={`chat-message ${message.role}`} key={i}>
                <span className="message-avatar">
                  {message.role === "assistant" ? (
                    <Compass size={17} />
                  ) : (
                    (profile?.name[0].toUpperCase() ?? "Y")
                  )}
                </span>
                <div>
                  <strong>
                    {message.role === "assistant" ? "LifePilot" : "You"}
                  </strong>
                  <p>{message.content}</p>
                </div>
              </div>
            ))}
            {busy && (
              <div className="chat-thinking" role="status">
                <LoaderCircle size={17} className="spin" />
                Thinking through your question…
              </div>
            )}
            {error && (
              <ErrorNotice
                message={error}
                retry={lastFailed ? () => void request(lastFailed) : undefined}
              />
            )}
            <div ref={bottom} />
          </div>
          <form
            className="chat-composer"
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
          >
            <label className="sr-only" htmlFor="message">
              Message LifePilot
            </label>
            <textarea
              id="message"
              ref={textarea}
              rows={2}
              maxLength={4000}
              value={input}
              disabled={busy}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing
                ) {
                  e.preventDefault();
                  void send(input);
                }
              }}
              placeholder="What would you like to think through?"
            />
            <div>
              <span>
                <CornerDownLeft size={12} />
                Enter to send · Shift + Enter for a new line
              </span>
              <button
                type="submit"
                className="send-button"
                disabled={busy || !input.trim()}
                aria-label="Send message"
              >
                {busy ? (
                  <LoaderCircle size={18} className="spin" />
                ) : (
                  <Send size={18} />
                )}
              </button>
            </div>
          </form>
          <p className="chat-disclaimer">
            AI can make mistakes. Verify facts with official sources. All
            catalog data is synthetic.
          </p>
        </section>
        <aside className="chat-aside">
          <div className="panel">
            <span className="eyebrow">YOUR CONTEXT</span>
            <h3>
              {profile
                ? `A little about ${profile.name}.`
                : "Make this more personal."}
            </h3>
            <p>
              {profile
                ? `Exploring ${profile.study_area} with a ${new Intl.NumberFormat("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 }).format(profile.annual_budget_eur)} annual budget.`
                : "A profile helps your assistant understand your field, priorities, and budget."}
            </p>
            <Link href="/profile" className="text-button">
              {profile ? "Review your profile" : "Build your profile"}
              <ArrowRight size={15} />
            </Link>
          </div>
          <div className="assistant-boundaries">
            <ShieldCheck size={21} />
            <h3>A thinking partner, with clear limits.</h3>
            <p>
              Your chat is sent to the configured Ollama server. Conversations
              stay in memory on this page and clear when you leave.
            </p>
            <p>
              The assistant can discuss your profile and the fictional catalog.
              Live web research and verified admission data are planned for a
              future phase.
            </p>
            <p>
              Program exploration and mathematical rankings remain available
              when the local model is offline.
            </p>
          </div>
        </aside>
      </div>
    </Reveal>
  );
}
