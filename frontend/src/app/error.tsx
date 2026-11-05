"use client";
import { ErrorNotice } from "@/components/ui";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <main id="main-content" className="standalone-state">
      <h1>Let’s try that again.</h1>
      <ErrorNotice
        message="This page could not be displayed. Your saved profile is still available."
        retry={reset}
      />
    </main>
  );
}
