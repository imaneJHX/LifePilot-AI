"use client";

import Link from "next/link";
import {
  AlertCircle,
  ArrowRight,
  Compass,
  LoaderCircle,
  Moon,
  Sun,
} from "lucide-react";
import { useEffect, useState } from "react";
import { motion, useReducedMotion } from "framer-motion";

function applyTheme(dark: boolean) {
  document.documentElement.dataset.theme = dark ? "dark" : "light";
  document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => {
    meta.setAttribute("content", dark ? "#121b23" : "#f6f7f9");
  });
}

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <Link href="/" className="brand" aria-label="LifePilot AI home">
      <span className="brand-symbol">
        <Compass size={23} strokeWidth={1.7} />
      </span>
      {!compact && (
        <span>
          LifePilot<span className="brand-ai">AI</span>
        </span>
      )}
    </Link>
  );
}
export function ThemeToggle() {
  const [dark, setDark] = useState(false);
  useEffect(() => {
    let preference: string | null = null;
    try {
      preference = localStorage.getItem("lifepilot.theme");
    } catch {
      /* Optional preference. */
    }
    const isDark = preference
      ? preference === "dark"
      : window.matchMedia("(prefers-color-scheme: dark)").matches;
    applyTheme(isDark);
    // Update on mount after reading the browser preference.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDark(isDark);
  }, []);
  const toggle = () => {
    const next = !dark;
    setDark(next);
    applyTheme(next);
    try {
      localStorage.setItem("lifepilot.theme", next ? "dark" : "light");
    } catch {
      /* Optional preference. */
    }
  };
  return (
    <button
      className="icon-button"
      onClick={toggle}
      aria-label={`Switch to ${dark ? "light" : "dark"} mode`}
    >
      {dark ? <Sun size={19} /> : <Moon size={19} />}
    </button>
  );
}
export function Reveal({
  children,
  className = "",
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduced ? false : { opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
    >
      {children}
    </motion.div>
  );
}
export function ErrorNotice({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <div className="error-notice" role="alert">
      <AlertCircle size={20} />
      <div>
        <p>{message}</p>
        {retry && (
          <button className="text-button" onClick={retry}>
            Try again <ArrowRight size={14} />
          </button>
        )}
      </div>
    </div>
  );
}
export function Loading({
  text = "Finding your next possibility…",
}: {
  text?: string;
}) {
  return (
    <div className="loading-state" role="status">
      <LoaderCircle className="spin" size={25} />
      <span>{text}</span>
    </div>
  );
}
export function DemoNotice({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`demo-notice ${compact ? "compact" : ""}`}>
      <span className="status-dot amber" />
      <span>
        <strong>Demonstration data.</strong>{" "}
        {compact
          ? "Fictional programs and illustrative costs."
          : "All institutions, programs, costs, and indices are fictional. Ranking scores are not admission probabilities."}
      </span>
    </div>
  );
}
