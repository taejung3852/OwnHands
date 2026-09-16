from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

from devharness.mcp.server import McpServer
from devharness.plugin import load_plugin_manifest


def run_m45_slice(data_root: Path | str, target_project: Path | str) -> dict:
    repo_root = Path(__file__).resolve().parents[3]
    manifest = load_plugin_manifest(repo_root)
    server = McpServer(data_root=data_root)

    request = {
        "jsonrpc": "2.0",
        "id": "slice-eval",
        "method": "tools/call",
        "params": {
            "name": "context.lint",
            "arguments": {
                "root": str(Path(target_project).resolve()),
                "sources": [
                    {
                        "source_id": "src:agents",
                        "path": "AGENTS.md",
                        "source_type": "agents_instruction",
                    }
                ],
                "task_id": "m45-observed-slice",
            },
        },
    }
    response = server.handle_request(request)
    envelope = json.loads(response["result"]["content"][0]["text"])

    summary = {
        "plugin_name": manifest["name"],
        "plugin_version": manifest["version"],
        "tool_invoked": "context.lint",
        "status": envelope["status"],
        "decision": envelope["decision"],
        "evidence_id": envelope["evidence_id"],
        "findings_count": len(envelope["data"].get("findings", [])),
    }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OwnHands M4.5 Minimal Vertical Slice")
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True)
    arguments = parser.parse_args()

    result = run_m45_slice(arguments.data_root, arguments.project)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
