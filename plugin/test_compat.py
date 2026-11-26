#!/usr/bin/env python3
"""Standalone fixtures for the read-only P2P compatibility checker."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

CHECKER = Path(__file__).with_name("p2p-compat-check")


class CompatibilityCheckerTests(unittest.TestCase):
    def run_checker(self, version_contents=None, kernel="6.18.60-Unraid", missing=False, manifest_directory=False, manifest_contents=None):
        with tempfile.TemporaryDirectory() as directory:
            version_file = Path(directory) / "unraid-version"
            if not missing and version_contents is not None:
                version_file.write_text(version_contents, encoding="utf-8")
            checker = CHECKER
            if manifest_directory or manifest_contents is not None:
                checker = Path(directory) / "p2p-compat-check"
                shutil.copy2(CHECKER, checker)
                manifest = Path(directory) / "compatibility.tsv"
                if manifest_directory:
                    manifest.mkdir()
                else:
                    assert manifest_contents is not None
                    manifest.write_text(manifest_contents, encoding="utf-8")
            return subprocess.run(
                [str(checker), str(version_file), kernel],
                check=False,
                text=True,
                capture_output=True,
            )

    def test_exact_supported_target_matches(self):
        result = self.run_checker('version="7.4.0"\n')
        self.assertEqual(result.returncode, 0)
        self.assertIn("status=match", result.stdout)
        self.assertIn("artifacts=v1.0.0", result.stdout)

    def test_known_different_target_mismatches(self):
        result = self.run_checker('version="7.4.1"\n', "6.18.64-Unraid")
        self.assertEqual(result.returncode, 1)
        self.assertIn("status=mismatch", result.stdout)
        self.assertIn("6.18.64-Unraid", result.stdout)

    def test_unparseable_target_is_unknown(self):
        result = self.run_checker('not-a-version\n')
        self.assertEqual(result.returncode, 2)
        self.assertIn("status=unknown", result.stdout)

    def test_missing_version_file_is_unavailable(self):
        result = self.run_checker(missing=True)
        self.assertEqual(result.returncode, 3)
        self.assertIn("status=unavailable", result.stdout)

    def test_directory_manifest_is_unavailable(self):
        result = self.run_checker('version="7.4.0"\n', manifest_directory=True)
        self.assertEqual(result.returncode, 3)
        self.assertIn("status=unavailable", result.stdout)

    def test_empty_manifest_is_unavailable(self):
        result = self.run_checker('version="7.4.0"\n', manifest_contents="")
        self.assertEqual(result.returncode, 3)
        self.assertIn("status=unavailable", result.stdout)

    def test_malformed_manifest_is_unavailable(self):
        result = self.run_checker('version="7.4.0"\n', manifest_contents="7.4.0\t6.18.60-Unraid\n")
        self.assertEqual(result.returncode, 3)
        self.assertIn("status=unavailable", result.stdout)


if __name__ == "__main__":
    unittest.main()
