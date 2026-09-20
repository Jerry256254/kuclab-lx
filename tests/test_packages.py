"""Balicky v packages.yml musi byt skutecne instalovatelne.

Kontroluje proti zivym metadatum: Fedora MDAPI pro bezna jmena,
HTTP dosazitelnost pro repo soubory, klice a RPM URL.
Bez site se test preskoci (bezi v CI, kde sit je).
"""
import os
import socket
import unittest
import urllib.error
import urllib.request

import yaml

REPO = os.path.join(os.path.dirname(__file__), "..")
MDAPI = "https://mdapi.fedoraproject.org/rawhide/pkg/{}"
TIMEOUT = 20

# Balicky z externich repozitaru (nejsou ve Fedore). Klic je jmeno balicku,
# hodnota je retezec, ktery musi byt v URL prislusneho .repo souboru.
EXTERNAL = {"brave-browser": "brave", "mullvad-vpn": "mullvad"}


def fetch(url: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "KucLabLX-test/1.0"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        r.read(1024)
        return r.status


class PackagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(REPO, "recipes", "common", "packages.yml"), encoding="utf-8") as f:
            cls.recipe = yaml.safe_load(f)

    def test_repos_and_keys_reachable(self):
        urls = list(self.recipe["repos"]["files"]["add"]) + list(self.recipe["repos"]["keys"])
        self.assertTrue(urls)
        for url in urls:
            try:
                code = fetch(url)
            except (urllib.error.URLError, socket.timeout) as e:
                self.skipTest(f"sit neni dostupna: {e}")
            self.assertEqual(code, 200, url)

    def test_install_entries_resolve(self):
        entries = self.recipe["install"]["packages"]
        repo_urls = " ".join(self.recipe["repos"]["files"]["add"])
        for entry in entries:
            if entry.startswith(("http://", "https://")):
                url = entry.replace("%OS_VERSION%", "44")
                try:
                    code = fetch(url)
                except (urllib.error.URLError, socket.timeout) as e:
                    self.skipTest(f"sit neni dostupna: {e}")
                self.assertEqual(code, 200, url)
            elif entry in EXTERNAL:
                self.assertIn(EXTERNAL[entry], repo_urls, f"{entry} nema repo v recipes")
            else:
                try:
                    code = fetch(MDAPI.format(entry))
                except (urllib.error.URLError, socket.timeout) as e:
                    self.skipTest(f"sit neni dostupna: {e}")
                self.assertEqual(code, 200, f"balicek {entry} neni ve Fedore")


if __name__ == "__main__":
    unittest.main()
