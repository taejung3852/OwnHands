from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from devharness.plugin import PluginManifestError, load_plugin_manifest, validate_plugin_manifest


class PluginManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "skills").mkdir()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_repo_root_manifest_is_valid(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        manifest = load_plugin_manifest(repo_root)
        self.assertEqual(manifest["name"], "ownhands")
        self.assertEqual(manifest["skills"]["directory"], "skills")
        self.assertIn("ownhands", manifest["mcp_servers"])

    def test_missing_required_fields_raise(self) -> None:
        incomplete = {
            "name": "ownhands",
            "version": "0.1.0",
            # missing description, skills, mcp_servers
        }
        with self.assertRaises(PluginManifestError):
            validate_plugin_manifest(incomplete, self.root)

    def test_missing_skills_directory_raises(self) -> None:
        manifest = {
            "name": "ownhands",
            "version": "0.1.0",
            "description": "Agent harness",
            "skills": {"directory": "non_existent_skills"},
            "mcp_servers": {
                "ownhands": {
                    "command": "python3",
                    "args": ["-m", "devharness", "mcp-server"],
                }
            },
        }
        with self.assertRaises(PluginManifestError):
            validate_plugin_manifest(manifest, self.root)

    def test_invalid_mcp_servers_entry_raises(self) -> None:
        manifest = {
            "name": "ownhands",
            "version": "0.1.0",
            "description": "Agent harness",
            "skills": {"directory": "skills"},
            "mcp_servers": {
                "ownhands": {
                    "command": "",  # empty command
                    "args": [],
                }
            },
        }
        with self.assertRaises(PluginManifestError):
            validate_plugin_manifest(manifest, self.root)
