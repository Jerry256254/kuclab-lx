"""Opravneni nastroju: uzivatel ridi, co agent smi.

Kazdy nastroj ma rezim: "allow" (vzdyt Rovnou), "ask" (zeptat se),
"deny" (zakazat). Profily jednim klikem nastavi vsechno.
"""
import json
import os

import config

ALLOW = "allow"
ASK = "ask"
DENY = "deny"

PROFILES = {
    "conservative": "deny",
    "balanced": "ask",
    "full": "allow",
}


def default_policy(tool_names) -> dict:
    return {name: ASK for name in tool_names}


def load(tool_names) -> dict:
    policy = default_policy(tool_names)
    try:
        with open(config.POLICY_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        for name in tool_names:
            if saved.get(name) in (ALLOW, ASK, DENY):
                policy[name] = saved[name]
    except (OSError, ValueError):
        pass
    # cteni je vzdy bezpecne
    for name in tool_names:
        if name in ("system_info", "list_dir", "read_file"):
            policy.setdefault(name, ALLOW)
    return policy


def save(policy: dict) -> None:
    os.makedirs(config.CONFIG_DIR, exist_ok=True)
    tmp = config.POLICY_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(policy, f, indent=2, ensure_ascii=False)
    os.replace(tmp, config.POLICY_PATH)


def apply_profile(tool_names, profile: str) -> dict:
    mode = PROFILES.get(profile, ASK)
    policy = {name: mode for name in tool_names}
    save(policy)
    return policy


def check(policy: dict, tool: str) -> str:
    return policy.get(tool, ASK)
