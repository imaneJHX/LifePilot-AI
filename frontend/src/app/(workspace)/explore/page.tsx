"use client";

import { useState } from "react";
import DemoProgramExplorer from "@/components/demo-program-explorer";
import { RealProgramExplorer } from "@/components/real-program-explorer";

export default function ExplorePage() {
  const [mode, setMode] = useState<"demo" | "real">("demo");
  return (
    <>
      <nav className="explorer-modes" aria-label="Explorer mode">
        <button type="button" aria-pressed={mode === "demo"} onClick={() => setMode("demo")}>
          Demo Recommendations
        </button>
        <button type="button" aria-pressed={mode === "real"} onClick={() => setMode("real")}>
          Real Programs
        </button>
      </nav>
      {mode === "real" ? <RealProgramExplorer /> : <DemoProgramExplorer />}
    </>
  );
}
