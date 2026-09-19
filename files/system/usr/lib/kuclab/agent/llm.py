"""LLM klient: Ollama (lokalne) + libovolne OpenAI-kompatibilni API.

Bez externich zavislosti, jen stdlib (urllib). Podporuje stream.
"""
import json
import urllib.request


class LLMError(Exception):
    pass


class LLMClient:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        # lokalni Ollama vzdy naprimo (i kdyz je nastavena systemova proxy)
        self._direct = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    @property
    def provider(self) -> str:
        return self.cfg.get("provider", "ollama")

    def chat(self, messages: list, tools: list | None = None, on_token=None) -> dict:
        """Vrati {"text": str, "tool_calls": [{"name": str, "arguments": dict}]}."""
        if self.provider == "openai":
            return self._openai(messages, tools, on_token)
        return self._ollama(messages, tools, on_token)

    def models(self) -> list:
        if self.provider == "openai":
            return [self.cfg.get("openai_model", "")]
        try:
            with self._direct.open(
                self.cfg.get("ollama_url", "") + "/api/tags", timeout=5
            ) as r:
                data = json.load(r)
            return [m["name"] for m in data.get("models", [])]
        except OSError:
            return []

    # -- Ollama (nativni /api/chat, OpenAI-like tool calling) --

    def _ollama(self, messages, tools, on_token) -> dict:
        url = self.cfg.get("ollama_url", "") + "/api/chat"
        body = {
            "model": self.cfg.get("ollama_model", ""),
            "messages": messages,
            "stream": True,
        }
        if tools:
            body["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]
        req = urllib.request.Request(
            url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
        )
        text_parts: list[str] = []
        tool_calls: list[dict] = []
        try:
            with self._direct.open(req, timeout=300) as r:
                for line in r:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                    except ValueError:
                        continue
                    msg = chunk.get("message", {})
                    token = msg.get("content", "")
                    if token:
                        text_parts.append(token)
                        if on_token:
                            on_token(token)
                    for call in msg.get("tool_calls", []):
                        fn = call.get("function", {})
                        tool_calls.append(
                            {"name": fn.get("name", ""), "arguments": fn.get("arguments", {})}
                        )
        except OSError as e:
            raise LLMError(f"Ollama neni dostupna ({e}). Bezi sluzba ollama?") from e
        return {"text": "".join(text_parts), "tool_calls": tool_calls}

    # -- OpenAI-kompatibilni API (OpenAI, Mistral, Groq, LM Studio, ...) --

    def _openai(self, messages, tools, on_token) -> dict:
        base = self.cfg.get("openai_base_url", "").rstrip("/")
        key = self.cfg.get("openai_api_key", "")
        body = {
            "model": self.cfg.get("openai_model", ""),
            "messages": messages,
            "stream": True,
        }
        if tools:
            body["tools"] = [
                {"type": "function", "function": t} for t in tools
            ]
        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"
        req = urllib.request.Request(
            base + "/chat/completions", data=json.dumps(body).encode(), headers=headers
        )
        text_parts: list[str] = []
        calls: dict[int, dict] = {}
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                for raw in r:
                    line = raw.decode("utf-8", "replace").strip()
                    if not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except ValueError:
                        continue
                    for choice in chunk.get("choices", []):
                        delta = choice.get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            text_parts.append(token)
                            if on_token:
                                on_token(token)
                        for call in delta.get("tool_calls", []):
                            idx = call.get("index", 0)
                            slot = calls.setdefault(idx, {"name": "", "args": ""})
                            fn = call.get("function", {})
                            if fn.get("name"):
                                slot["name"] = fn["name"]
                            slot["args"] += fn.get("arguments", "")
        except OSError as e:
            raise LLMError(f"API neni dostupne ({e}).") from e
        tool_calls = []
        for slot in calls.values():
            try:
                args = json.loads(slot["args"] or "{}")
            except ValueError:
                args = {}
            tool_calls.append({"name": slot["name"], "arguments": args})
        return {"text": "".join(text_parts), "tool_calls": tool_calls}
