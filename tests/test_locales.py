"""Kompilace prekladu: nas mini-msgfmt musi vyrobit citelne .mo."""
import gettext
import os
import shutil
import subprocess
import tempfile
import unittest

REPO = os.path.join(os.path.dirname(__file__), "..")


class LocalesTest(unittest.TestCase):
    def test_compile_en_mo(self):
        script = os.path.join(REPO, "files", "scripts", "compile-locales.sh")
        po_src = os.path.join(REPO, "files", "system", "usr", "share", "kuclab", "po")
        with tempfile.TemporaryDirectory() as tmp:
            po_dir = os.path.join(tmp, "po")
            shutil.copytree(po_src, po_dir)
            localedir = os.path.join(tmp, "locale")
            env = dict(os.environ, PO_DIR_OVERRIDE=po_dir, LOCALEDIR_OVERRIDE=localedir)
            proc = subprocess.run(["bash", script], capture_output=True, text=True, env=env, timeout=60)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            mo = os.path.join(localedir, "en", "LC_MESSAGES", "kuclab.mo")
            self.assertTrue(os.path.exists(mo))
            with open(mo, "rb") as f:
                trans = gettext.GNUTranslations(f)
            self.assertEqual(trans.gettext("Odebrat"), "Remove")
            self.assertEqual(trans.gettext("Nalezeno: %d"), "Found: %d")
            # pokryti: vsechny msgid ze zdrojaku musi byt v .po
            import ast
            import glob

            missing = []
            for py in glob.glob(os.path.join(REPO, "files", "system", "usr", "lib", "kuclab", "**", "*.py"), recursive=True):
                for node in ast.walk(ast.parse(open(py).read())):
                    if (
                        isinstance(node, ast.Call)
                        and getattr(node.func, "id", "") == "_"
                        and node.args
                        and isinstance(node.args[0], ast.Constant)
                    ):
                        msgid = node.args[0].value
                        if msgid not in trans._catalog:
                            missing.append(f"{msgid} ({py})")
            self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
