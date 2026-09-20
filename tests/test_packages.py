"""Balicky v packages.yml musi byt skutecne instalovatelne.

Kontroluje proti zivym metadatum: Fedora MDAPI pro bezna jmena,
HTTP dosazitelnost pro repo soubory, klice a RPM URL.
Bez site se test preskoci (bezi v CI, kde sit je).
"""
import os
import re
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

# Soubory, ze kterych se kontroluje dosazitelnost stahovacich URL.
# Schvalne jen stahovacky (build skripty, modely, proton) — uzivatelska
# nastaveni endpointu (Ollama URL, OpenAI base) sem nepatri.
DOWNLOAD_FILES = [
    "files/scripts/install-ollama.sh",
    "files/scripts/install-voice.sh",
    "files/system/usr/lib/kuclab/agent/voice.py",
    "files/system/usr/lib/kuclab/winshit/proton.py",
]
URL_RE = re.compile(r"https://[^\s\"'){}]+")


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
            except urllib.error.HTTPError as e:
                self.fail(f"{url} -> HTTP {e.code}")
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
                except urllib.error.HTTPError as e:
                    self.fail(f"balicek {entry} neni ve Fedore (HTTP {e.code})")
                except (urllib.error.URLError, socket.timeout) as e:
                    self.skipTest(f"sit neni dostupna: {e}")
                self.assertEqual(code, 200, f"balicek {entry} neni ve Fedore")

    def test_download_urls_reachable(self):
        urls = set()
        for rel in DOWNLOAD_FILES:
            with open(os.path.join(REPO, rel), encoding="utf-8") as f:
                for match in URL_RE.findall(f.read()):
                    if "$" in match or "{" in match:
                        continue  # parametrizovane, nekontrolujeme
                    urls.add(match.rstrip(".,;"))
        self.assertTrue(urls)
        for url in sorted(urls):
            try:
                code = fetch(url)
            except urllib.error.HTTPError as e:
                self.fail(f"{url} -> HTTP {e.code}")
            except (urllib.error.URLError, socket.timeout) as e:
                self.skipTest(f"sit neni dostupna: {e}")
            self.assertEqual(code, 200, url)


if __name__ == "__main__":
    unittest.main()
