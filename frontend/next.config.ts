import type { NextConfig } from "next";
import path from "node:path";

const androidBuild = process.env.CAPACITOR_BUILD === "true";

if (androidBuild && !process.env.NEXT_PUBLIC_API_BASE_URL) {
  throw new Error(
    "Android exports require NEXT_PUBLIC_API_BASE_URL. Use npm run android:build from the project root.",
  );
}

const nextConfig: NextConfig = {
  turbopack: { root: path.resolve(__dirname) },
  output: androidBuild
    ? "export"
    : process.env.BUILD_STANDALONE === "true"
      ? "standalone"
      : undefined,
  // Website builds always retain their existing same-origin API proxy.
  env: {
    NEXT_PUBLIC_API_BASE_URL: androidBuild ? process.env.NEXT_PUBLIC_API_BASE_URL : "",
    NEXT_PUBLIC_PWA_ENABLED: androidBuild ? "false" : "true",
  },
  trailingSlash: androidBuild,
  poweredByHeader: false,
  // Let a local model warm up without the proxy ending the request first.
  experimental: { proxyTimeout: 310000 },
  ...(androidBuild
    ? {}
    : {
        async headers() {
          return [
            {
              source: "/sw.js",
              headers: [
                { key: "Cache-Control", value: "no-store, max-age=0" },
                { key: "Service-Worker-Allowed", value: "/" },
                { key: "Content-Type", value: "application/javascript; charset=utf-8" },
                { key: "Content-Security-Policy", value: "default-src 'self'; script-src 'self'" },
              ],
            },
            {
              source: "/manifest.webmanifest",
              headers: [{ key: "Cache-Control", value: "no-cache" }],
            },
            {
              source: "/api/:path*",
              headers: [{ key: "Cache-Control", value: "no-store" }],
            },
          ];
        },
        async rewrites() {
          return [
            {
              source: "/api/:path*",
              destination: `${process.env.BACKEND_URL ?? "http://127.0.0.1:8000"}/api/:path*`,
            },
          ];
        },
      }),
};
export default nextConfig;
