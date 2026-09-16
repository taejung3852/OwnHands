#!/usr/bin/env bash

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
baseline_commit="e2b7308b0de99a9f9f263348cac15f9b067602b6"

cd "$repo_root"

git cat-file -e "${baseline_commit}^{commit}"

check_hash() {
  local path="$1"
  local expected="$2"
  local actual

  actual="$(git show "${baseline_commit}:${path}" | shasum -a 256 | awk '{print $1}')"
  if [[ "$actual" != "$expected" ]]; then
    printf 'baseline_hash_mismatch=%s\n' "$path" >&2
    return 1
  fi
}

check_hash "docs/product/Design_Rationale.md" "feb54daab5c5641517319ccfaa32872871b06fc3ad1bc8ee16f7946f3fb57030"
check_hash "docs/product/Control_layer.md" "7c43d869603e2e514d26ed6e26528a7029061d70200a607eb6bb01ef2fca73a8"
check_hash "docs/product/Dashboard_layer.md" "98d0a5927fd71ce5b066da91ec7b22f84676ff49810f99fba4e557b05ea494da"
check_hash "docs/product/향후계획.md" "c2301e6c4b0f99b0b3e95147102da4efcb78e3adc5bcb42eea46d8e4c7a7c3a1"

python3 - "$repo_root" <<'PY'
from pathlib import Path
import re
import sys
from urllib.parse import unquote

root = Path(sys.argv[1])
scan_roots = [root / "docs" / name for name in ("product", "adr", "spikes", "design")]
link_pattern = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
missing = []
checked = 0

for scan_root in scan_roots:
    for document in sorted(scan_root.rglob("*.md")):
        for line_number, line in enumerate(document.read_text(encoding="utf-8").splitlines(), 1):
            for match in link_pattern.finditer(line):
                target = match.group(1).strip().split()[0].strip("<>")
                if not target or target.startswith(("#", "mailto:")) or "://" in target:
                    continue
                target_path = unquote(target.split("#", 1)[0])
                if not target_path:
                    continue
                checked += 1
                resolved = (document.parent / target_path).resolve()
                if not resolved.exists():
                    missing.append(f"{document.relative_to(root)}:{line_number} -> {target_path}")

if missing:
    print("internal_links=failed", file=sys.stderr)
    for item in missing:
        print(item, file=sys.stderr)
    raise SystemExit(1)

print(f"internal_links=passed ({checked})")
PY

for ignored_path in ".dev-harness/example" ".codex-log/example" "docs/spikes/raw/example"; do
  if ! git check-ignore -q "$ignored_path"; then
    printf 'raw_evidence_ignore=failed (%s)\n' "$ignored_path" >&2
    exit 1
  fi
done

printf 'baseline_commit=%s\n' "$baseline_commit"
printf 'baseline_hashes=passed (4)\n'
printf 'raw_evidence_ignore=passed (3)\n'
