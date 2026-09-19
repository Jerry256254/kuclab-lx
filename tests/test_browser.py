"""Prohlizec: originalni Brave (RPM) s DuckDuckGo, zadny Firefox."""
import glob
import json
import os
import unittest

import yaml

REPO = os.path.join(os.path.dirname(__file__), "..")


class BrowserTest(unittest.TestCase):
    def test_brave_in_packages(self):
        with open(os.path.join(REPO, "recipes", "common", "packages.yml"), encoding="utf-8") as f:
            pkg = yaml.safe_load(f)
        self.assertIn("brave-browser", pkg["install"]["packages"])
        repos = pkg["repos"]["files"]["add"]
        self.assertTrue(any("brave-browser" in r and r.startswith("https://") for r in repos))
        self.assertTrue(any("brave-core.asc" in k for k in pkg["repos"]["keys"]))

    def test_no_firefox_in_flatpaks(self):
        with open(os.path.join(REPO, "recipes", "common", "flatpaks.yml"), encoding="utf-8") as f:
            flat = yaml.safe_load(f)
        for conf in flat["configurations"]:
            for app_id in conf.get("install") or []:
                self.assertNotIn("firefox", app_id.lower())
                self.assertNotIn("mozilla", app_id.lower())

    def test_brave_in_dock(self):
        with open(os.path.join(REPO, "files", "gschema-overrides", "zz1-kuclab.gschema.override"), encoding="utf-8") as f:
            content = f.read()
        self.assertIn("brave-browser.desktop", content)
        self.assertNotIn("firefox", content.lower())

    def test_brave_policy_duckduckgo(self):
        policy_path = os.path.join(REPO, "files", "system", "etc", "brave", "policies", "managed", "kuclab.json")
        with open(policy_path, encoding="utf-8") as f:
            policy = json.load(f)
        self.assertTrue(policy.get("DefaultSearchProviderEnabled"))
        self.assertEqual(policy.get("DefaultSearchProviderName"), "DuckDuckGo")
        self.assertIn("duckduckgo.com", policy.get("DefaultSearchProviderSearchURL", ""))
        self.assertFalse(policy.get("MetricsReportingEnabled"))

    def test_no_firefox_anywhere(self):
        hits = []
        for path in glob.glob(os.path.join(REPO, "recipes", "**", "*"), recursive=True) + glob.glob(
            os.path.join(REPO, "files", "**", "*"), recursive=True
        ):
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            if "firefox" in content.lower() or "mozilla" in content.lower():
                hits.append(os.path.relpath(path, REPO))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
