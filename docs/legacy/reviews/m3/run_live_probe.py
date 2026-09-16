from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from devharness.m3_review import (
    M3ReviewError,
    claim_live_attempt,
    execute_live_probe,
    record_attempt_outcome,
    validate_live_preflight,
)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description="Run the single fail-closed ownhands M3 disposable live probe"
    )
    result.add_argument("--repository", type=Path, required=True)
    result.add_argument("--data-root", type=Path, required=True)
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--codex-bin", required=True)
    result.add_argument("--model", required=True)
    result.add_argument("--timeout", type=float, required=True)
    result.add_argument("--live", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    arguments = parser().parse_args(argv)
    try:
        preflight = validate_live_preflight(
            arguments.repository,
            arguments.data_root,
            arguments.output,
            arguments.codex_bin,
            arguments.model,
            arguments.timeout,
            live=arguments.live,
        )
        attempt = claim_live_attempt(
            preflight["data_root"],
            {
                "repository": str(preflight["repository"]),
                "model": preflight["model"],
                "timeout": preflight["timeout"],
            },
            repository=preflight["repository"],
        )
        try:
            packet = execute_live_probe(preflight)
        except Exception as error:
            record_attempt_outcome(attempt, "failed", f"{type(error).__name__}: {error}")
            raise
        record_attempt_outcome(attempt, "completed", packet["runtime_gate"]["result"])
    except M3ReviewError as error:
        print(f"M3 live probe refused or failed: {error}", file=sys.stderr)
        return 2
    except Exception as error:
        print(f"M3 live probe failed: {type(error).__name__}: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"packet": str(preflight["output"]), "gate": packet["runtime_gate"]}, ensure_ascii=False, indent=2))
    return 0 if packet["runtime_gate"]["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
