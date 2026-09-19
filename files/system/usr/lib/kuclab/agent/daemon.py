"""Daemon agenta: JSON protokol pres unix socket.

Zpravy klient -> server (jeden JSON + \\n na radek):
  {"cmd": "ask", "history": [...], "id": N}
  {"cmd": "ping", "id": N}
  {"type": "confirm_reply", "id": N, "ok": true|false}

Zpravy server -> klient:
  {"id": N, "type": "token", "text": "..."}
  {"id": N, "type": "confirm", "tool": "...", "args": {...}}
  {"id": N, "type": "done", "text": "...", "actions": [...]}
  {"id": N, "type": "error", "text": "..."}
"""
import json
import os
import socket
import threading

import agent as agent_mod
import config


class Client:
    def __init__(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.connect(config.socket_path())
        self._file = self.sock.makefile("r", encoding="utf-8")
        self._seq = 0
        self._lock = threading.Lock()

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    def _send(self, obj: dict):
        data = (json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8")
        with self._lock:
            self.sock.sendall(data)

    def ping(self) -> bool:
        try:
            self._send({"cmd": "ping", "id": 0})
            line = self._file.readline()
            return bool(line)
        except OSError:
            return False

    def ask(self, history: list, on_token=None, confirm=None) -> dict:
        self._seq += 1
        rid = self._seq
        self._send({"cmd": "ask", "history": history, "id": rid})
        text, actions = "", []
        while True:
            line = self._file.readline()
            if not line:
                raise ConnectionError("Daemon ukoncil spojeni.")
            msg = json.loads(line)
            if msg.get("id") != rid:
                continue
            kind = msg.get("type")
            if kind == "token":
                text += msg.get("text", "")
                if on_token:
                    on_token(msg.get("text", ""))
            elif kind == "confirm":
                ok = confirm(msg["tool"], msg.get("args", {})) if confirm else False
                self._send({"type": "confirm_reply", "id": rid, "ok": bool(ok)})
            elif kind == "done":
                return {"text": msg.get("text", text), "actions": msg.get("actions", actions)}
            elif kind == "error":
                raise ConnectionError(msg.get("text", "Chyba daemonu."))


def _handle(conn: socket.socket):
    ag = agent_mod.Agent(config.load())
    fp = conn.makefile("r", encoding="utf-8")
    send_lock = threading.Lock()

    def send(obj: dict):
        with send_lock:
            conn.sendall((json.dumps(obj, ensure_ascii=False) + "\n").encode("utf-8"))

    pending: dict[int, bool | None] = {}
    cond = threading.Condition()

    def reader():
        try:
            for line in fp:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("type") == "confirm_reply":
                    with cond:
                        pending[msg.get("id")] = bool(msg.get("ok"))
                        cond.notify_all()
                elif msg.get("cmd") == "ping":
                    send({"id": msg.get("id", 0), "type": "pong"})
                elif msg.get("cmd") == "ask":
                    threading.Thread(target=do_ask, args=(msg,), daemon=True).start()
        except OSError:
            pass

    def do_ask(msg):
        rid = msg.get("id", 0)
        try:
            def confirm(tool, args):
                with cond:
                    pending[rid] = None
                send({"id": rid, "type": "confirm", "tool": tool, "args": args})
                with cond:
                    while pending.get(rid) is None:
                        cond.wait(timeout=300)
                    return bool(pending.pop(rid, False))

            result = ag.ask(
                msg.get("history", []),
                on_token=lambda t: send({"id": rid, "type": "token", "text": t}),
                confirm=confirm,
            )
            send({"id": rid, "type": "done", "text": result["text"], "actions": result["actions"]})
        except Exception as e:  # noqa: BLE001 - chyba jde klientovi
            try:
                send({"id": rid, "type": "error", "text": str(e)})
            except OSError:
                pass

    reader()


def run_server() -> None:
    path = config.socket_path()
    try:
        os.unlink(path)
    except OSError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(path)
    srv.listen(8)
    print(f"KucLab agent daemon: {path}")
    while True:
        conn, _ = srv.accept()
        threading.Thread(target=_handle, args=(conn,), daemon=True).start()
