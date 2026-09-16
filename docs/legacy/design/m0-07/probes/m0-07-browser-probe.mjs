#!/usr/bin/env node

import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import process from "node:process";
import { fileURLToPath, pathToFileURL } from "node:url";

const probeDir = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.resolve(probeDir, "../index.html");
const chromePath = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const profileDir = fs.mkdtempSync(path.join(os.tmpdir(), "devharness-m0-07-chrome-"));
const writeScreenshots = process.argv.includes("--write-screenshots");
const captures = [];
const paletteTokens = ["--page", "--surface", "--text", "--muted", "--brand", "--brand-soft", "--brand-ink", "--focus", "--button-fill", "--success"];
const expectedPalettes = {
  "signal-light": ["#f5f7f7", "#ffffff", "#151a1c", "#536166", "#006d73", "#d9f3f2", "#004d51", "#008b92", "#006d73", "#176c45"],
  "ledger-light": ["#f7f6f2", "#fffefa", "#1d1d23", "#5d5c66", "#4a49a8", "#e8e7fb", "#353478", "#5c5bc2", "#4a49a8", "#176c45"],
  "slate-light": ["#f4f6f8", "#ffffff", "#171923", "#555d6d", "#6639a6", "#eee5fa", "#482478", "#7950b7", "#6639a6", "#176c45"],
  "signal-dark": ["#0d1214", "#141a1d", "#f1f5f5", "#aeb9bc", "#68dadd", "#12373a", "#a7f0f1", "#68dadd", "#006d73", "#81d9ad"],
  "ledger-dark": ["#111116", "#18181f", "#f4f3f8", "#b7b4c0", "#b3b1ff", "#2b2a58", "#dfdeff", "#b3b1ff", "#4a49a8", "#81d9ad"],
  "slate-dark": ["#101219", "#171a23", "#f3f4f8", "#b3b8c7", "#c6a6ff", "#34254d", "#eadfff", "#c6a6ff", "#6639a6", "#81d9ad"]
};

for (const brand of ["signal", "ledger", "slate"]) {
  for (const theme of ["light", "dark"]) {
    for (const screen of ["task", "harness", "evidence"]) {
      captures.push(`capture-${brand}-${theme}-${screen}`);
    }
  }
}

let chrome;
let cleanPromise;

function cleanUp() {
  if (cleanPromise) return cleanPromise;
  cleanPromise = (async () => {
    if (chrome && chrome.exitCode === null) {
      chrome.kill("SIGTERM");
      await Promise.race([
        new Promise((resolve) => chrome.once("exit", resolve)),
        new Promise((resolve) => setTimeout(resolve, 2000))
      ]);
      if (chrome.exitCode === null) chrome.kill("SIGKILL");
    }
    if (path.basename(profileDir).startsWith("devharness-m0-07-chrome-")) {
      fs.rmSync(profileDir, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
    }
  })();
  return cleanPromise;
}

function browserEndpoint(child) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error("Chrome DevTools endpoint timeout")), 10000);
    child.stderr.setEncoding("utf8");
    child.stderr.on("data", (chunk) => {
      const match = chunk.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (!match) return;
      clearTimeout(timeout);
      resolve(match[1]);
    });
    child.once("exit", (code) => {
      clearTimeout(timeout);
      reject(new Error(`Chrome exited before DevTools was ready: ${code}`));
    });
  });
}

function cdp(socket) {
  let nextId = 1;
  const pending = new Map();
  socket.addEventListener("message", ({ data }) => {
    const message = JSON.parse(data);
    if (!message.id || !pending.has(message.id)) return;
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  });
  return (method, params = {}) => new Promise((resolve, reject) => {
    const id = nextId++;
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function main() {
  if (!fs.existsSync(chromePath)) throw new Error(`Chrome not found: ${chromePath}`);
  chrome = spawn(chromePath, [
    "--headless=new",
    "--disable-gpu",
    "--disable-background-networking",
    "--remote-debugging-port=0",
    `--user-data-dir=${profileDir}`,
    "about:blank"
  ], { stdio: ["ignore", "ignore", "pipe"] });

  const browserWs = await browserEndpoint(chrome);
  const endpoint = new URL(browserWs);
  const targets = await fetch(`http://${endpoint.hostname}:${endpoint.port}/json/list`).then((response) => response.json());
  const page = targets.find((target) => target.type === "page");
  if (!page) throw new Error("No Chrome page target found");

  const socket = new WebSocket(page.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {
    socket.addEventListener("open", resolve, { once: true });
    socket.addEventListener("error", reject, { once: true });
  });
  const send = cdp(socket);
  await send("Page.enable");
  await send("Runtime.enable");

  const widths = [320, 390, 1440];
  let rootOverflowFailures = 0;
  let hiddenScreenFailures = 0;
  let initiallyOpenDetailFailures = 0;
  let focusableMinimum = Number.POSITIVE_INFINITY;
  const overflowDetails = [];
  const paletteFailures = [];
  const computedPalettes = new Map();

  for (const width of widths) {
    await send("Emulation.setDeviceMetricsOverride", {
      width,
      height: width < 600 ? 844 : 1800,
      deviceScaleFactor: 1,
      mobile: false
    });
    for (const capture of captures) {
      const targetUrl = `${pathToFileURL(htmlPath).href}#${capture}`;
      await send("Page.navigate", { url: targetUrl });
      await new Promise((resolve) => setTimeout(resolve, 80));
      const { result } = await send("Runtime.evaluate", {
        returnByValue: true,
        expression: `(() => {
          const root = document.documentElement;
          const capture = location.hash.slice(1).split('-');
          const expected = capture.at(-1);
          const panels = [...document.querySelectorAll('.screen')]
            .filter((element) => getComputedStyle(element).display !== 'none')
            .map((element) => element.id.replace('-panel', ''));
          const style = getComputedStyle(document.querySelector('.prototype'));
          return {
            rootOverflow: root.scrollWidth > root.clientWidth + 1,
            scrollWidth: root.scrollWidth,
            clientWidth: root.clientWidth,
            expected,
            panels,
            openDetails: document.querySelectorAll('details[open]').length,
            focusable: document.querySelectorAll('a[href], input:not([disabled]), summary').length,
            positiveTabindex: document.querySelectorAll('[tabindex]:not([tabindex="-1"]):not([tabindex="0"])').length,
            palette: ${JSON.stringify(paletteTokens)}.map((token) => style.getPropertyValue(token).trim().toLowerCase()),
            offenders: [...document.querySelectorAll('body *')]
              .filter((element) => element.getBoundingClientRect().right > innerWidth + 1)
              .slice(0, 8)
              .map((element) => ({
                tag: element.tagName.toLowerCase(),
                className: typeof element.className === 'string' ? element.className : '',
                right: Math.round(element.getBoundingClientRect().right),
                width: Math.round(element.getBoundingClientRect().width)
              }))
          };
        })()`
      });
      const measurement = result.value;
      if (writeScreenshots && width === 1440) {
        const { data } = await send("Page.captureScreenshot", {
          format: "png",
          fromSurface: true,
          captureBeyondViewport: false
        });
        const filename = `${capture.replace("capture-", "")}.png`;
        fs.writeFileSync(path.resolve(probeDir, `../screenshots/${filename}`), Buffer.from(data, "base64"));
      }
      if (measurement.rootOverflow) {
        rootOverflowFailures += 1;
        overflowDetails.push(`${capture}@${width}:${measurement.scrollWidth}/${measurement.clientWidth}:${JSON.stringify(measurement.offenders)}`);
      }
      if (measurement.panels.length !== 1 || measurement.panels[0] !== measurement.expected) hiddenScreenFailures += 1;
      if (measurement.openDetails !== 0) initiallyOpenDetailFailures += 1;
      if (measurement.positiveTabindex !== 0) throw new Error(`Positive tabindex found in ${capture}`);
      if (width === 1440) {
        const paletteKey = capture.split("-").slice(1, 3).join("-");
        const actual = JSON.stringify(measurement.palette);
        const expected = JSON.stringify(expectedPalettes[paletteKey]);
        computedPalettes.set(capture, actual);
        if (actual !== expected) paletteFailures.push(`${capture}: expected=${expected} actual=${actual}`);
      }
      focusableMinimum = Math.min(focusableMinimum, measurement.focusable);
    }
  }

  await send("Page.navigate", { url: pathToFileURL(htmlPath).href });
  await new Promise((resolve) => setTimeout(resolve, 80));
  const { result: disclosureResult } = await send("Runtime.evaluate", {
    returnByValue: true,
    expression: `(() => {
      const detail = document.querySelector('.progressive-detail');
      const summary = detail?.querySelector('summary');
      if (!detail || !summary) return { opened: false, closed: false };
      summary.click();
      const opened = detail.open;
      summary.click();
      return { opened, closed: !detail.open };
    })()`
  });

  socket.close();
  if (rootOverflowFailures > 0) throw new Error(`Document overflow failures: ${rootOverflowFailures} (${overflowDetails.join(", ")})`);
  if (hiddenScreenFailures > 0) throw new Error(`Screen selection failures: ${hiddenScreenFailures}`);
  if (initiallyOpenDetailFailures > 0) throw new Error(`Initially open detail failures: ${initiallyOpenDetailFailures}`);
  if (paletteFailures.length > 0) throw new Error(`Capture palette failures: ${paletteFailures.length} (${paletteFailures.join(", ")})`);
  const distinctComputedPalettes = new Set(computedPalettes.values()).size;
  if (distinctComputedPalettes !== 6) throw new Error(`Expected 6 distinct direction/theme palettes, found ${distinctComputedPalettes}`);
  if (!disclosureResult.value.opened || !disclosureResult.value.closed) throw new Error("Progressive disclosure did not toggle");

  console.log("M0-07 browser probe: PASSED");
  console.log(`capture_states=${captures.length}`);
  console.log(`viewport_widths=${widths.join(",")}`);
  console.log(`layout_checks=${captures.length * widths.length}`);
  console.log("document_horizontal_overflow=0");
  console.log("screen_selection_failures=0");
  console.log(`capture_palette_checks=${computedPalettes.size}`);
  console.log(`distinct_computed_palettes=${distinctComputedPalettes}`);
  console.log("initially_open_details=0");
  console.log("progressive_disclosure_toggle=passed");
  console.log(`focusable_elements_minimum=${focusableMinimum}`);
  console.log("positive_tabindex=0");
  if (writeScreenshots) console.log(`screenshots_written=${captures.length}`);
}

process.on("SIGINT", () => cleanUp().finally(() => process.exit(130)));
process.on("SIGTERM", () => cleanUp().finally(() => process.exit(143)));

main()
  .catch((error) => {
    console.error(`M0-07 browser probe: FAILED\n${error.message}`);
    process.exitCode = 1;
  })
  .finally(() => cleanUp());
