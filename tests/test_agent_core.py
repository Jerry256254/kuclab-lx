"""Jadro agenta bez GUI a site: config, policy, tools, llm chyby, daemon protokol."""
import json
import os
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "files", "system", "usr", "lib", "kuclab", "agent"))

import agent as agent_mod
import config
import daemon as daemon_mod
import llm as llm_mod
import policy as policy_mod
import tools


class ConfigTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.object(config, "CONFIG_DIR", os.path.join(home, "cfg")), mock.patch.object(
                config, "CONFIG_PATH", os.path.join(home, "cfg", "agent.json")
            ):
                cfg = config.load()
                self.assertEqual(cfg["provider"], "ollama")
                cfg["provider"] = "openai"
                config.save(cfg)
                self.assertEqual(config.load()["provider"], "openai")


class PolicyTest(unittest.TestCase):
    NAMES = ["read_file", "run_command"]

    def test_profiles(self):
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.object(config, "CONFIG_DIR", home), mock.patch.object(
                config, "POLICY_PATH", os.path.join(home, "p.json")
            ):
                full = policy_mod.apply_profile(self.NAMES, "full")
                self.assertEqual(full, {"read_file": "allow", "run_command": "allow"})
                cons = policy_mod.apply_profile(self.NAMES, "conservative")
                self.assertEqual(policy_mod.check(cons, "run_command"), "deny")

    def test_default_ask(self):
        self.assertEqual(policy_mod.check({}, "run_command"), "ask")


class ToolsTest(unittest.TestCase):
    def test_unknown(self):
        self.assertIn("Neznamy", tools.run("nope", {}))

    def test_system_info_json(self):
        data = json.loads(tools.run("system_info", {}))
        self.assertIn("system", data)

    def test_list_dir(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "a.txt"), "w") as f:
                f.write("x")
            self.assertIn("a.txt", tools.run("list_dir", {"path": d}))

    def test_write_read_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "f.txt")
            tools.run("write_file", {"path": p, "content": "ahoj"})
            self.assertEqual(tools.run("read_file", {"path": p}), "ahoj")


class LLMErrorTest(unittest.TestCase):
    def test_ollama_unreachable_raises(self):
        client = llm_mod.LLMClient({"provider": "ollama", "ollama_url": "http://127.0.0.1:1", "ollama_model": "x"})
        with self.assertRaises(llm_mod.LLMError):
            client.chat([{"role": "user", "content": "hi"}])


class DaemonProtocolTest(unittest.TestCase):
    def test_ask_with_confirm(self):
        with tempfile.TemporaryDirectory() as run:
            with mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": run}):
                fake = mock.Mock()
                fake.chat.side_effect = [
                    {"text": "", "tool_calls": [{"name": "system_info", "arguments": {}}]},
                    {"text": "hotovo", "tool_calls": []},
                ]
                with mock.patch.object(agent_mod, "Agent", return_value=mock.Mock(ask=self._ask_via(fake))):
                    import socket as _socket

                    path = config.socket_path()
                    try:
                        srv = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
                    except OSError as e:
                        self.skipTest(f"unix sockety nejsou dostupne: {e}")
                    srv.bind(path)
                    srv.listen(1)
                    server_conn = {}

                    def accept():
                        conn, _ = srv.accept()
                        server_conn["c"] = conn
                        daemon_mod._handle(conn)

                    t = threading.Thread(target=accept, daemon=True)
                    t.start()
                    client = daemon_mod.Client()
                    try:
                        confirms = []
                        result = client.ask(
                            [{"role": "user", "content": "info"}],
                            confirm=lambda tool, args: confirms.append(tool) or True,
                        )
                    finally:
                        client.close()
                        srv.close()
                self.assertEqual(result["text"], "hotovo")
                self.assertEqual(confirms, ["system_info"])

    @staticmethod
    def _ask_via(fake):
        def ask(history, on_token=None, confirm=None):
            first = fake.chat([], None, None)
            out = []
            for call in first["tool_calls"]:
                ok = confirm(call["name"], call["arguments"]) if confirm else False
                out.append(tools.run(call["name"], call["arguments"]) if ok else "denied")
            second = fake.chat([], None, None)
            return {"text": second["text"], "actions": out}

        return ask


if __name__ == "__main__":
    unittest.main()
