from __future__ import annotations

import json
from pathlib import Path


class PluginManifestError(ValueError):
    pass


REQUIRED_MANIFEST_FIELDS = {"name", "version", "description", "skills", "mcp_servers"}


def validate_plugin_manifest(manifest: dict, root: Path) -> dict:
    if not isinstance(manifest, dict):
        raise PluginManifestError("plugin manifest must be a dictionary")
    missing = REQUIRED_MANIFEST_FIELDS - set(manifest.keys())
    if missing:
        raise PluginManifestError(f"plugin manifest missing required fields: {sorted(missing)}")

    for field in ("name", "version", "description"):
        value = manifest.get(field)
        if not isinstance(value, str) or not value.strip():
            raise PluginManifestError(f"{field} must be a non-empty string")

    skills_config = manifest.get("skills")
    if not isinstance(skills_config, dict) or not isinstance(skills_config.get("directory"), str):
        raise PluginManifestError("skills must specify a directory string")
    skills_dir = root / skills_config["directory"]
    if not skills_dir.is_dir():
        raise PluginManifestError(f"skills directory not found: {skills_config['directory']}")

    mcp_servers = manifest.get("mcp_servers")
    if not isinstance(mcp_servers, dict) or not mcp_servers:
        raise PluginManifestError("mcp_servers must be a non-empty dictionary")
    for server_name, server_config in mcp_servers.items():
        if not isinstance(server_config, dict):
            raise PluginManifestError(f"mcp server {server_name} configuration must be a dictionary")
        command = server_config.get("command")
        if not isinstance(command, str) or not command.strip():
            raise PluginManifestError(f"mcp server {server_name} command must be a non-empty string")
        args = server_config.get("args")
        if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
            raise PluginManifestError(f"mcp server {server_name} args must be a list of strings")

    return manifest


def load_plugin_manifest(root: Path | str) -> dict:
    root_path = Path(root).resolve()
    manifest_path = root_path / "plugin.json"
    if not manifest_path.is_file():
        raise PluginManifestError(f"plugin.json not found in {root_path}")
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise PluginManifestError(f"failed to parse plugin.json: {error}") from error
    return validate_plugin_manifest(data, root_path)
