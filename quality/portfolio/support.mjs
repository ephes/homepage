import { spawn } from "node:child_process";
import { createServer } from "node:net";
import { once } from "node:events";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { targetProfiles } from "./contracts.mjs";

export const packageDir = path.dirname(fileURLToPath(import.meta.url));
export const repoRoot = path.resolve(packageDir, "../..");
export const artifactsDir = path.join(packageDir, "artifacts");
export const prototypeDir = path.join(repoRoot, "docs/superpowers/prototypes");

const pagePathEnvironment = Object.freeze({
  homepage: "PORTFOLIO_AUDIT_HOMEPAGE_PATH",
  error: "PORTFOLIO_AUDIT_ERROR_PATH",
  project: "PORTFOLIO_AUDIT_PROJECT_PATH",
  imprint: "PORTFOLIO_AUDIT_IMPRINT_PATH",
  privacy: "PORTFOLIO_AUDIT_PRIVACY_PATH",
});

function configuredProfile(profile) {
  return {
    ...profile,
    pages: Object.fromEntries(
      Object.entries(profile.pages).map(([name, page]) => [
        name,
        { ...page, path: process.env[pagePathEnvironment[name]] || page.path },
      ]),
    ),
  };
}

function resolvePages(baseUrl, profile) {
  return Object.fromEntries(
    Object.entries(profile.pages).map(([name, page]) => [
      name,
      {
        url: new URL(page.path, baseUrl).href,
        expectedStatus: page.expectedStatus,
      },
    ]),
  );
}

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
  const profileName = process.env.PORTFOLIO_AUDIT_TARGET || "prototype";
  const declaredProfile = targetProfiles[profileName];
  if (!declaredProfile) {
    throw new Error(
      `Unknown PORTFOLIO_AUDIT_TARGET '${profileName}'. Expected one of: ${Object.keys(targetProfiles).join(", ")}`,
    );
  }
  const profile = configuredProfile(declaredProfile);

  if (process.env.PORTFOLIO_AUDIT_URL) {
    const suppliedUrl = new URL(process.env.PORTFOLIO_AUDIT_URL);
    const baseUrl = profileName === "prototype" ? new URL(".", suppliedUrl).href : suppliedUrl.origin;
    const pages = resolvePages(baseUrl, profile);
    if (profileName === "prototype" && !process.env.PORTFOLIO_AUDIT_HOMEPAGE_PATH) {
      pages.homepage = { url: suppliedUrl.href, expectedStatus: profile.pages.homepage.expectedStatus };
    }
    return {
      profile: profile.name,
      url: pages.homepage.url,
      pages,
      stop: async () => {},
    };
  }

  if (profileName !== "prototype") {
    throw new Error(
      "The Wagtail target currently requires PORTFOLIO_AUDIT_URL for an already running site; an isolated Wagtail server is not part of this slice.",
    );
  }

  const port = await unusedPort();
  const child = spawn("python3", ["-m", "http.server", String(port), "--bind", "127.0.0.1"], {
    cwd: prototypeDir,
    stdio: "ignore",
  });
  const baseUrl = `http://127.0.0.1:${port}/`;
  const pages = resolvePages(baseUrl, profile);
  for (let attempt = 0; attempt < 50; attempt += 1) {
    try {
      const response = await fetch(pages.homepage.url);
      if (response.status === pages.homepage.expectedStatus) {
        return {
          profile: profile.name,
          url: pages.homepage.url,
          pages,
          stop: async () => child.kill("SIGTERM"),
        };
      }
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 100));
  }
  child.kill("SIGTERM");
  throw new Error(`Local audit server did not become ready at ${pages.homepage.url}`);
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
