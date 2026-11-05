import type { Metadata, Viewport } from "next";
import { Providers } from "@/components/providers";
import { PwaRegistration } from "@/components/pwa-registration";
import "./globals.css";

export const metadata: Metadata = {
  applicationName: "LifePilot AI",
  // Next.js 16 emits mobile-web-app-capable from appleWebApp; retain older iOS support.
  other: { "apple-mobile-web-app-capable": "yes" },
  manifest: "/manifest.webmanifest",
  appleWebApp: {
    capable: true,
    title: "LifePilot AI",
    statusBarStyle: "default",
  },
  icons: {
    icon: [{ url: "/icons/icon-192.png", sizes: "192x192", type: "image/png" }],
    apple: [{ url: "/icons/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
  },
  title: {
    default: "LifePilot AI — Your next chapter, with clarity",
    template: "%s | LifePilot AI",
  },
  description:
    "Explore study possibilities, compare what matters, and plan your next chapter with an explainable decision-support workspace.",
};
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
  colorScheme: "light dark",
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f6f7f9" },
    { media: "(prefers-color-scheme: dark)", color: "#121b23" },
  ],
};
export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <PwaRegistration />
        <a href="#main-content" className="skip-link">
          Skip to content
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
