import https from "node:https";
import http from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = fileURLToPath(new URL("../", import.meta.url));
const certPath = process.env.PWA_CERT_PATH || path.join(root, ".certificates/lifepilot.pem");
const keyPath = process.env.PWA_KEY_PATH || path.join(root, ".certificates/lifepilot-key.pem");
const port = Number(process.env.PWA_HTTPS_PORT || 3443);
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error("Invalid PWA_HTTPS_PORT");

// Local testing only: fixed loopback upstream, no public tunnel or open proxy.
const server = https.createServer({
  cert: readFileSync(certPath),
  key: readFileSync(keyPath),
  minVersion: "TLSv1.2",
}, (request, response) => {
  if (!request.url?.startsWith("/") || request.url.startsWith("//")) {
    response.writeHead(400).end("Invalid request path");
    return;
  }
  const upstream = http.request({
    hostname: "127.0.0.1",
    port: 3000,
    path: request.url,
    method: request.method,
    headers: {
      ...request.headers,
      "x-forwarded-proto": "https",
      "x-forwarded-host": request.headers.host || "localhost",
    },
  }, (upstreamResponse) => {
    response.writeHead(upstreamResponse.statusCode || 502, upstreamResponse.headers);
    upstreamResponse.pipe(response);
    upstreamResponse.on("error", () => response.destroy());
  });
  upstream.on("error", () => {
    if (!response.headersSent) {
      response.writeHead(502, { "Content-Type": "text/plain", "Cache-Control": "no-store" });
      response.end("Start the Next.js production server on port 3000, then retry.");
    } else response.destroy();
  });
  request.on("aborted", () => upstream.destroy());
  response.on("close", () => { if (!response.writableEnded) upstream.destroy(); });
  request.pipe(upstream);
});
server.listen(port, "0.0.0.0", () => {
  console.log(`LifePilot HTTPS testing: https://YOUR_PC_LAN_IP:${port}`);
  console.log("Trust the mkcert root CA on your iPhone; Next.js must be running on port 3000.");
});
