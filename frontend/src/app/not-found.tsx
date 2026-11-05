import Link from "next/link";
export default function NotFound() {
  return (
    <main id="main-content" className="standalone-state">
      <span className="eyebrow">404 · A SMALL DETOUR</span>
      <h1>This path doesn’t lead anywhere.</h1>
      <p>Let’s get you back to your next chapter.</p>
      <Link className="button button-primary" href="/">
        Back to LifePilot
      </Link>
    </main>
  );
}
