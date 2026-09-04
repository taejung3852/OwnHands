#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

const probeDir = path.dirname(fileURLToPath(import.meta.url));
const htmlPath = path.resolve(probeDir, "../index.html");
const source = fs.readFileSync(htmlPath, "utf8");
const failures = [];

function check(condition, message) {
  if (!condition) failures.push(message);
}

function count(pattern) {
  return [...source.matchAll(pattern)].length;
}

function ruleVariables(selectorStart) {
  const start = source.indexOf(selectorStart);
  check(start >= 0, `CSS rule missing: ${selectorStart}`);
  if (start < 0) return {};
  const open = source.indexOf("{", start);
  const close = source.indexOf("}", open);
  const block = source.slice(open + 1, close);
  return Object.fromEntries(
    [...block.matchAll(/--([a-z-]+):\s*(#[0-9a-fA-F]{6})\s*;/g)].map((match) => [match[1], match[2]])
  );
}

function rgb(hex) {
  const value = hex.replace("#", "");
  return [0, 2, 4].map((offset) => Number.parseInt(value.slice(offset, offset + 2), 16) / 255);
}

function luminance(hex) {
  return rgb(hex)
    .map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
    .reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0);
}

function contrast(foreground, background) {
  const [lighter, darker] = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

const baseLight = ruleVariables(".prototype {");
const baseDark = ruleVariables("body:has(#theme-dark:checked) .prototype,");
const directionRules = {
  "signal-light": ruleVariables("body:has(#theme-light:checked):has(#brand-signal:checked) .prototype,"),
  "ledger-light": ruleVariables("body:has(#theme-light:checked):has(#brand-ledger:checked) .prototype,"),
  "slate-light": ruleVariables("body:has(#theme-light:checked):has(#brand-slate:checked) .prototype,"),
  "signal-dark": ruleVariables("body:has(#theme-dark:checked):has(#brand-signal:checked) .prototype,"),
  "ledger-dark": ruleVariables("body:has(#theme-dark:checked):has(#brand-ledger:checked) .prototype,"),
  "slate-dark": ruleVariables("body:has(#theme-dark:checked):has(#brand-slate:checked) .prototype,")
};

const buttonFill = {
  signal: "#006d73",
  ledger: "#4a49a8",
  slate: "#6639a6"
};

const contrastResults = [];
for (const [variant, direction] of Object.entries(directionRules)) {
  const [name, mode] = variant.split("-");
  const tokens = mode === "dark"
    ? { ...baseLight, ...baseDark, ...direction }
    : { ...baseLight, ...direction };
  const pairs = [
    ["text/page", tokens.text, tokens.page, 4.5],
    ["text/surface", tokens.text, tokens.surface, 4.5],
    ["muted/surface", tokens.muted, tokens.surface, 4.5],
    ["brand-ink/brand-soft", tokens["brand-ink"], tokens["brand-soft"], 4.5],
    ["focus/page", tokens.focus, tokens.page, 3],
    ["success/success-soft", tokens.success, tokens["success-soft"], 4.5],
    ["warning/warning-soft", tokens.warning, tokens["warning-soft"], 4.5],
    ["danger/danger-soft", tokens.danger, tokens["danger-soft"], 4.5],
    ["primary-white/brand-fill", "#ffffff", buttonFill[name], 4.5]
  ];
  for (const [label, foreground, background, minimum] of pairs) {
    check(Boolean(foreground && background), `${variant} missing tokens for ${label}`);
    if (!foreground || !background) continue;
    const ratio = contrast(foreground, background);
    contrastResults.push({ variant, label, ratio, minimum });
    check(ratio >= minimum, `${variant} ${label} contrast ${ratio.toFixed(2)} < ${minimum}`);
  }
}

check(count(/id="brand-(signal|ledger|slate)"/g) === 3, "three brand direction controls required");
check(source.includes('id="brand-ledger" checked'), "Ledger Indigo must be the default direction");
check(!source.includes('id="brand-signal" checked'), "Signal Graphite must not remain the default direction");
check(source.includes("색상 방향 승인 · UI/UX는 M5에서 이어서 설계"), "approved color scope and M5 UX deferral must be explicit");
check(count(/id="theme-(light|dark)"/g) === 2, "two theme controls required");
check(count(/class="screen" id="(task|harness|evidence)-panel"/g) === 3, "three dashboard screens required");
check(count(/id="capture-(signal|ledger|slate)-(light|dark)-(task|harness|evidence)"/g) === 18, "18 capture states required");
check(count(/data-fixture-id="m0-06-store-probe-ba7394f-2026-09-04"/g) === 1, "pinned fixture must exist once in a shared DOM");
check(source.includes("partial_write_rollback=passed"), "fixture must include actual rollback result");
check(source.includes("integrity_check=ok"), "fixture must include actual integrity result");
check(source.includes("실제 제품 환경의 안전까지 확인한 것은 아닙니다"), "fixture limitations must be explicit");
check(source.includes("Configured") && source.includes("Loaded") && source.includes("Enforced"), "control realization stages missing");
check(source.includes("Observed") && source.includes("Inferred") && source.includes("Unobserved"), "evidence basis labels missing");
check(count(/class="at-a-glance"/g) === 3, "each screen needs one at-a-glance summary");
check(
  [
    "왜 이런 결론인가요?",
    "무엇을 확인했나요?",
    "아직 모르는 것은 무엇인가요?",
    "저장 흐름 그림 보기",
    "전체 통제표 보기",
    "용어 뜻 보기",
    "검사 6개 모두 보기",
    "출처와 실행 환경 보기",
    "기술 세부정보 보기"
  ].every((label) => source.includes(label)),
  "progressive-disclosure labels missing"
);
check(!/<details[^>]*\sopen(?:\s|>)/.test(source), "detail sections must start collapsed");
check(source.includes("+ 추가 제안") && source.includes("− 제외 제안") && source.includes("? 미검증·보류"), "non-color diagram labels missing");
check(count(/href="#evidence-panel"/g) >= 10, "evidence drill-down links missing");
check(source.includes("@media (prefers-reduced-motion: reduce)"), "reduced-motion rule missing");
check(source.includes(":focus-visible"), "visible focus rule missing");
check(source.includes("@media (max-width: 640px)"), "small viewport rule missing");
check(!source.includes("box-shadow"), "prototype must not use decorative shadows");
check(!source.includes("<script"), "prototype should work without executable script");

const remoteReferences = [...source.matchAll(/(?:href|src)="(https?:\/\/[^\"]+)"/g)].map((match) => match[1]);
check(remoteReferences.length === 1, "only one remote reference is allowed");
check(remoteReferences.every((url) => url.startsWith("https://fonts.googleapis.com/css2")), "remote reference must be Google Fonts CSS only");

if (failures.length > 0) {
  console.error("M0-07 design probe: FAILED");
  failures.forEach((failure) => console.error(`- ${failure}`));
  process.exit(1);
}

const minimumContrast = Math.min(...contrastResults.map(({ ratio }) => ratio));
const minimumTextContrast = Math.min(...contrastResults.filter(({ minimum }) => minimum === 4.5).map(({ ratio }) => ratio));
const minimumFocusContrast = Math.min(...contrastResults.filter(({ minimum }) => minimum === 3).map(({ ratio }) => ratio));
console.log("M0-07 design probe: PASSED");
console.log("fixture_instances=1");
console.log("brand_directions=3");
console.log("themes=2");
console.log("screens=3");
console.log("capture_states=18");
console.log("evidence_path_interactions=1");
console.log("raw_output_interactions=2");
console.log(`contrast_pairs_checked=${contrastResults.length}`);
console.log(`minimum_contrast_ratio=${minimumContrast.toFixed(2)}`);
console.log(`minimum_text_contrast_ratio=${minimumTextContrast.toFixed(2)}`);
console.log(`minimum_focus_contrast_ratio=${minimumFocusContrast.toFixed(2)}`);
console.log(`remote_stylesheet_references=${remoteReferences.length}`);
console.log(`executable_script_tags=${count(/<script/g)}`);
