from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from devharness.plugin import (
    CANONICAL_MCP_SCHEMA_V1,
    CANONICAL_PLUGIN_SCHEMA_V1,
    PluginManifestError,
    PluginMcpConfigError,
    expand_placeholders,
    load_plugin_manifest,
    load_plugin_package,
    validate_mcp_config,
    validate_plugin_manifest,
    validate_plugin_name,
)


class PluginManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "skills").mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_repo_root_package_is_valid_agent_plugin_v1(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        pkg = load_plugin_package(repo_root)
        self.assertEqual(pkg["name"], "ownhands")
        self.assertEqual(pkg["manifest"]["$schema"], CANONICAL_PLUGIN_SCHEMA_V1)
        self.assertIn("ownhands", pkg["mcp_servers"])
        self.assertEqual(pkg["mcp_servers"]["ownhands"]["type"], "stdio")
        self.assertGreaterEqual(len(pkg["skills"]), 5)

        # Also verify backward-compatible manifest dictionary
        manifest = load_plugin_manifest(repo_root)
        self.assertEqual(manifest["name"], "ownhands")
        self.assertEqual(manifest["skills"]["directory"], "skills")
        self.assertIn("ownhands", manifest["mcp_servers"])

    def test_missing_required_fields_raise(self) -> None:
        # missing $schema
        with self.assertRaises(PluginManifestError):
            validate_plugin_manifest({"name": "ownhands"})

        # missing name
        with self.assertRaises(PluginManifestError):
            validate_plugin_manifest({"$schema": CANONICAL_PLUGIN_SCHEMA_V1})

        # invalid schema
        with self.assertRaises(PluginManifestError):
            validate_plugin_manifest({"$schema": "https://example.com/other.json", "name": "ownhands"})

    def test_plugin_name_constraints(self) -> None:
        # Valid names
        for valid in ("my-plugin", "acme.tools", "lint3r", "a", "ownhands"):
            validate_plugin_name(valid)

        # Invalid names per §5.5
        invalid_names = [
            "My-Plugin",       # Uppercase
            "-start",          # Leading hyphen
            "end-",            # Trailing hyphen
            ".start",          # Leading dot
            "end.",            # Trailing dot
            "has--double",     # Consecutive hyphens
            "too.many..dots",  # Consecutive periods
            "",                # Empty
            "a" * 65,          # Length > 64
            "with spaces",     # Spaces
            "special$chars",   # Non-alphanumeric
        ]
        for invalid in invalid_names:
            with self.subTest(name=invalid):
                with self.assertRaises(PluginManifestError):
                    validate_plugin_name(invalid)

    def test_unknown_top_level_fields_are_ignored(self) -> None:
        manifest = {
            "$schema": CANONICAL_PLUGIN_SCHEMA_V1,
            "name": "test-plugin",
            "unknown_experimental_field": 123,
        }
        validated = validate_plugin_manifest(manifest, self.root)
        self.assertEqual(validated["name"], "test-plugin")
        self.assertNotIn("unknown_experimental_field", validated)

    def test_mcp_config_validation_and_placeholders(self) -> None:
        mcp_data = {
            "$schema": CANONICAL_MCP_SCHEMA_V1,
            "mcpServers": {
                "local-test": {
                    "type": "stdio",
                    "command": "python3",
                    "args": ["--root", "${PLUGIN_ROOT}", "--data", "${PLUGIN_DATA}/test"],
                    "env": {"TEST_DIR": "${PLUGIN_ROOT}/tests"},
                    "cwd": "${PLUGIN_ROOT}",
                },
                "remote-test": {
                    "type": "streamable-http",
                    "url": "https://api.example.com/mcp",
                    "headers": {"X-App": "test"},
                },
            },
        }
        plugin_data = self.root / ".data"
        validated = validate_mcp_config(mcp_data, self.root, plugin_data)

        local_server = validated["mcpServers"]["local-test"]
        self.assertEqual(local_server["type"], "stdio")
        self.assertEqual(local_server["args"][1], str(self.root.resolve()))
        self.assertEqual(local_server["args"][3], str(plugin_data.resolve() / "test"))
        self.assertEqual(local_server["env"]["TEST_DIR"], f"{self.root.resolve()}/tests")
        self.assertEqual(local_server["cwd"], str(self.root.resolve()))

        remote_server = validated["mcpServers"]["remote-test"]
        self.assertEqual(remote_server["type"], "streamable-http")
        self.assertEqual(remote_server["url"], "https://api.example.com/mcp")

    def test_mcp_config_invalid_transport_raises(self) -> None:
        bad_mcp = {
            "$schema": CANONICAL_MCP_SCHEMA_V1,
            "mcpServers": {
                "bad-server": {
                    "type": "unsupported-proto",
                }
            },
        }
        with self.assertRaises(PluginMcpConfigError):
            validate_mcp_config(bad_mcp, self.root)

    def test_mcp_config_env_cannot_override_reserved_vars(self) -> None:
        bad_mcp = {
            "$schema": CANONICAL_MCP_SCHEMA_V1,
            "mcpServers": {
                "bad-server": {
                    "type": "stdio",
                    "command": "python3",
                    "env": {"PLUGIN_ROOT": "/bad/path"},
                }
            },
        }
        with self.assertRaises(PluginMcpConfigError):
            validate_mcp_config(bad_mcp, self.root)

    def test_fixed_skills_discovery(self) -> None:
        # Create a skill
        skill_dir = self.root / "skills" / "demo-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text("---\nname: demo-skill\n---\nDemo content", encoding="utf-8")

        # Create a directory without SKILL.md (should NOT be discovered as skill)
        not_a_skill = self.root / "skills" / "not-a-skill"
        not_a_skill.mkdir(parents=True)
        (not_a_skill / "other.txt").write_text("not a skill", encoding="utf-8")

        # Create plugin.json
        (self.root / "plugin.json").write_text(
            json.dumps({"$schema": CANONICAL_PLUGIN_SCHEMA_V1, "name": "skill-test"}),
            encoding="utf-8",
        )

        pkg = load_plugin_package(self.root)
        self.assertEqual(len(pkg["skills"]), 1)
        self.assertEqual(pkg["skills"][0]["name"], "demo-skill")
