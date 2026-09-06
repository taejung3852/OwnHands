from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class PluginManifestError(ValueError):
    pass


class PluginMcpConfigError(ValueError):
    pass


CANONICAL_PLUGIN_SCHEMA_V1 = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
CANONICAL_MCP_SCHEMA_V1 = "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"

SUPPORTED_PLUGIN_SCHEMAS = {CANONICAL_PLUGIN_SCHEMA_V1}
SUPPORTED_MCP_SCHEMAS = {CANONICAL_MCP_SCHEMA_V1}

ALLOWED_MANIFEST_FIELDS = {
    "$schema",
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
    "extensions",
}

VALID_MCP_TRANSPORTS = {"stdio", "streamable-http", "sse"}


def validate_plugin_name(name: str) -> None:
    if not isinstance(name, str) or not (1 <= len(name) <= 64):
        raise PluginManifestError("plugin name must be a string between 1 and 64 characters")
    if not re.fullmatch(r"^[a-z0-9.-]+$", name):
        raise PluginManifestError(
            f"plugin name '{name}' contains invalid characters; only lowercase ASCII letters, digits, hyphens, and periods are permitted"
        )
    if not (name[0].isalnum() and name[-1].isalnum()):
        raise PluginManifestError(f"plugin name '{name}' must start and end with an alphanumeric character")
    if "--" in name or ".." in name:
        raise PluginManifestError(f"plugin name '{name}' cannot contain consecutive hyphens or periods")


def validate_plugin_manifest(manifest: dict, root: Path | None = None) -> dict:
    if not isinstance(manifest, dict):
        raise PluginManifestError("plugin manifest must be a dictionary")

    # Required fields per Agent Plugins 1.0.0 (§5.3)
    if "$schema" not in manifest:
        raise PluginManifestError("plugin manifest missing required '$schema' field")
    schema = manifest["$schema"]
    if not isinstance(schema, str) or schema not in SUPPORTED_PLUGIN_SCHEMAS:
        raise PluginManifestError(f"unsupported or invalid plugin manifest schema: {schema}")

    if "name" not in manifest:
        raise PluginManifestError("plugin manifest missing required 'name' field")
    validate_plugin_name(manifest["name"])

    # Optional metadata type checks (§5.4)
    if "version" in manifest and not isinstance(manifest["version"], str):
        raise PluginManifestError("version must be a string")
    if "description" in manifest and not isinstance(manifest["description"], str):
        raise PluginManifestError("description must be a string")
    if "homepage" in manifest and not isinstance(manifest["homepage"], str):
        raise PluginManifestError("homepage must be a string")
    if "repository" in manifest and not isinstance(manifest["repository"], str):
        raise PluginManifestError("repository must be a string")
    if "license" in manifest and not isinstance(manifest["license"], str):
        raise PluginManifestError("license must be a string")
    if "keywords" in manifest:
        if not isinstance(manifest["keywords"], list) or not all(isinstance(k, str) for k in manifest["keywords"]):
            raise PluginManifestError("keywords must be a list of strings")
    if "author" in manifest:
        author = manifest["author"]
        if not isinstance(author, dict):
            raise PluginManifestError("author must be an object")
        allowed_author_keys = {"name", "email", "url"}
        if set(author.keys()) - allowed_author_keys:
            raise PluginManifestError(f"author contains unknown fields: {sorted(set(author.keys()) - allowed_author_keys)}")
        for key in ("name", "email", "url"):
            if key in author and not isinstance(author[key], str):
                raise PluginManifestError(f"author.{key} must be a string")

    # Extensions (§8.1)
    if "extensions" in manifest:
        extensions = manifest["extensions"]
        if not isinstance(extensions, dict):
            # Non-fatal per §8.1: ignore and continue
            manifest = {k: v for k, v in manifest.items() if k != "extensions"}

    # Unknown top-level fields: non-fatal per §5.2 (report and ignore)
    unknown_fields = set(manifest.keys()) - ALLOWED_MANIFEST_FIELDS
    if unknown_fields:
        # Permitted to continue, but clean manifest object
        manifest = {k: v for k, v in manifest.items() if k in ALLOWED_MANIFEST_FIELDS}

    return manifest


def expand_placeholders(value: str, plugin_root: Path, plugin_data: Path) -> str:
    """Non-recursive single-pass textual replacement of ${PLUGIN_ROOT} and ${PLUGIN_DATA}."""
    return value.replace("${PLUGIN_ROOT}", str(plugin_root)).replace("${PLUGIN_DATA}", str(plugin_data))


def validate_mcp_config(
    mcp_config: dict,
    root: Path,
    plugin_data_dir: Path | None = None,
) -> dict:
    if not isinstance(mcp_config, dict):
        raise PluginMcpConfigError("mcp configuration must be a dictionary")

    # Required top-level fields (§7.2.1)
    if "$schema" not in mcp_config:
        raise PluginMcpConfigError("mcp configuration missing required '$schema' field")
    if mcp_config["$schema"] not in SUPPORTED_MCP_SCHEMAS:
        raise PluginMcpConfigError(f"unsupported mcp schema: {mcp_config['$schema']}")

    if "mcpServers" not in mcp_config:
        raise PluginMcpConfigError("mcp configuration missing required 'mcpServers' field")
    mcp_servers = mcp_config["mcpServers"]
    if not isinstance(mcp_servers, dict):
        raise PluginMcpConfigError("mcpServers must be an object")

    extra_top = set(mcp_config.keys()) - {"$schema", "mcpServers"}
    if extra_top:
        raise PluginMcpConfigError(f"mcp configuration contains unknown top-level fields: {sorted(extra_top)}")

    root_resolved = root.resolve()
    data_resolved = (plugin_data_dir or (root / ".plugin_data")).resolve()

    validated_servers: dict[str, dict[str, Any]] = {}
    for server_name, server in mcp_servers.items():
        if not isinstance(server, dict):
            raise PluginMcpConfigError(f"server '{server_name}' configuration must be an object")

        server_type = server.get("type")
        if server_type not in VALID_MCP_TRANSPORTS:
            raise PluginMcpConfigError(f"server '{server_name}' has invalid or unsupported type: {server_type}")

        if server_type == "stdio":
            command = server.get("command")
            if not isinstance(command, str) or not command.strip():
                raise PluginMcpConfigError(f"stdio server '{server_name}' command must be a non-empty string")
            if " " in command.strip() and not command.startswith(("./", "/")):
                # Must be a single executable token
                raise PluginMcpConfigError(f"stdio server '{server_name}' command must be a single executable token")

            args = server.get("args", [])
            if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
                raise PluginMcpConfigError(f"stdio server '{server_name}' args must be a list of strings")

            env = server.get("env", {})
            if not isinstance(env, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in env.items()):
                raise PluginMcpConfigError(f"stdio server '{server_name}' env must be an object of strings")
            if "PLUGIN_ROOT" in env or "PLUGIN_DATA" in env:
                raise PluginMcpConfigError(f"stdio server '{server_name}' env cannot override PLUGIN_ROOT or PLUGIN_DATA")

            cwd = server.get("cwd")
            if cwd is not None and not isinstance(cwd, str):
                raise PluginMcpConfigError(f"stdio server '{server_name}' cwd must be a string")

            # Perform expansion
            expanded_args = [expand_placeholders(a, root_resolved, data_resolved) for a in args]
            expanded_env = {k: expand_placeholders(v, root_resolved, data_resolved) for k, v in env.items()}
            expanded_cwd = (
                expand_placeholders(cwd, root_resolved, data_resolved) if cwd else str(root_resolved)
            )

            # Path containment check on cwd
            resolved_cwd = Path(expanded_cwd).resolve()
            if not (root_resolved in resolved_cwd.parents or resolved_cwd == root_resolved or data_resolved in resolved_cwd.parents or resolved_cwd == data_resolved):
                raise PluginMcpConfigError(f"stdio server '{server_name}' cwd escapes package root and data directory")

            validated_servers[server_name] = {
                "type": "stdio",
                "command": command,
                "args": expanded_args,
                "env": expanded_env,
                "cwd": expanded_cwd,
            }

        elif server_type in {"streamable-http", "sse"}:
            url = server.get("url")
            if not isinstance(url, str) or not url.startswith(("http://", "https://")):
                raise PluginMcpConfigError(f"server '{server_name}' url must be an absolute http or https URL")
            headers = server.get("headers", {})
            if not isinstance(headers, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in headers.items()):
                raise PluginMcpConfigError(f"server '{server_name}' headers must be an object of strings")

            validated_servers[server_name] = {
                "type": server_type,
                "url": url,
                "headers": headers,
            }

    return {
        "$schema": mcp_config["$schema"],
        "mcpServers": validated_servers,
    }


def discover_skills(root: Path) -> list[dict[str, Any]]:
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return []

    discovered = []
    for item in sorted(skills_dir.iterdir()):
        if item.is_dir():
            skill_md = item / "SKILL.md"
            if skill_md.is_file():
                discovered.append({
                    "name": item.name,
                    "directory": f"skills/{item.name}",
                    "skill_file": str(skill_md),
                })
    return discovered


def load_plugin_package(root: Path | str, plugin_data_dir: Path | str | None = None) -> dict[str, Any]:
    root_path = Path(root).resolve()
    manifest_file = root_path / "plugin.json"
    if not manifest_file.is_file():
        raise PluginManifestError(f"plugin.json not found in {root_path}")

    try:
        raw_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise PluginManifestError(f"failed to parse plugin.json: {error}") from error

    manifest = validate_plugin_manifest(raw_manifest, root_path)

    # Fixed discovery for skills (§6.1, §7.1)
    skills = discover_skills(root_path)

    # Fixed discovery for MCP configuration (§6.1, §7.2)
    mcp_file = root_path / "mcp.json"
    mcp_config = None
    mcp_servers: dict[str, Any] = {}
    if mcp_file.is_file():
        try:
            raw_mcp = json.loads(mcp_file.read_text(encoding="utf-8"))
            validated_mcp = validate_mcp_config(raw_mcp, root_path, Path(plugin_data_dir) if plugin_data_dir else None)
            mcp_config = validated_mcp
            mcp_servers = validated_mcp["mcpServers"]
        except (json.JSONDecodeError, OSError) as error:
            raise PluginMcpConfigError(f"failed to parse mcp.json: {error}") from error

    return {
        "manifest": manifest,
        "name": manifest["name"],
        "version": manifest.get("version", "0.0.0"),
        "description": manifest.get("description", ""),
        "skills": skills,
        "mcp_servers": mcp_servers,
        "mcp_config": mcp_config,
        "plugin_root": str(root_path),
        "plugin_data": str(plugin_data_dir) if plugin_data_dir else str(root_path / ".plugin_data"),
    }


def load_plugin_manifest(root: Path | str) -> dict[str, Any]:
    """Load plugin package and return manifest dictionary.
    
    Provides backward-compatibility by guaranteeing manifest dictionary contains:
    - 'name', 'version', 'description'
    - 'skills': {'directory': 'skills', 'items': [...]}
    - 'mcp_servers': {...}
    """
    pkg = load_plugin_package(root)
    manifest = dict(pkg["manifest"])
    # Supply compatibility projections
    manifest["skills"] = {
        "directory": "skills",
        "items": pkg["skills"],
    }
    manifest["mcp_servers"] = pkg["mcp_servers"]
    return manifest
