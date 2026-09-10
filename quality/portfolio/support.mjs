import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { once } from "node:events";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const packageDir = path.dirname(fileURLToPath(import.meta.url));
export const repoRoot = path.resolve(packageDir, "../..");
export const artifactsDir = path.join(packageDir, "artifacts");
export const prototypeDir = path.join(repoRoot, "docs/superpowers/prototypes");
export const defaultPath = "/portfolio-startseite.html";

async function unusedPort() {
  const server = createServer();
  server.listen(0, "127.0.0.1");
  await once(server, "listening");
  const { port } = server.address();
  server.close();
  await once(server, "close");
  return port;
}

export async function target() {
  if (process.env.PORTFOLIO_AUDIT_URL) {
    return { url: process.env.PORTFOLIO_AUDIT_URL, stop: async () => {} };
  }

  const port = await unusedPort();
  const child = spawn("python3", ["-m", "http.server", String(port), "--bind", "127.0.0.1"], {
    cwd: prototypeDir,
    stdio: "ignore",
  });
  const url = `http://127.0.0.1:${port}${defaultPath}`;
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return { url, stop: async () => child.kill("SIGTERM") };
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  child.kill("SIGTERM");
  throw new Error(`Local audit server did not become ready at ${url}`);
}

export function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / 1024 ** 2).toFixed(2)} MiB`;
}

export function markdownTable(rows) {
  return [
    "| Check | Result | Detail |",
    "|---|---:|---|",
    ...rows.map((row) => `| ${row.name} | ${row.pass ? "PASS" : "FAIL"} | ${String(row.detail).replaceAll("|", "\\|")} |`),
  ].join("\n");
}
