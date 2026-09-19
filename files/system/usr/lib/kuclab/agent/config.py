"""Cesty a konfigurace agenta."""
import json
import os

APP_ID = "org.kuclab.AgentChat"

CONFIG_DIR = os.path.join(os.path.expanduser("~/.config"), "kuclab")
DATA_DIR = os.path.join(os.path.expanduser("~/.local/share"), "kuclab")
CONFIG_PATH = os.path.join(CONFIG_DIR, "agent.json")
POLICY_PATH = os.path.join(CONFIG_DIR, "agent-policy.json")

BIN_DIR = "/usr/lib/kuclab/bin"
OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "qwen3:4b"

DEFAULTS = {
    "provider": "ollama",  # ollama | openai
    "ollama_url": OLLAMA_URL,
    "ollama_model": DEFAULT_MODEL,
    "openai_base_url": "https://api.openai.com/v1",
    "openai_api_key": "",
    "openai_model": "gpt-4o-mini",
    "voice_enabled": True,
    "voice_lang": "cs",  # cs | en
    "system_prompt": "",
}


def load() -> dict:
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg: dict) -> None:
    os.makedirs(CONFIG_DIR, exist_ok=True)
    tmp = CONFIG_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
    os.replace(tmp, CONFIG_PATH)


def socket_path() -> str:
    run = os.environ.get("XDG_RUNTIME_DIR", "/tmp")
    return os.path.join(run, "kuclab-agent.sock")
