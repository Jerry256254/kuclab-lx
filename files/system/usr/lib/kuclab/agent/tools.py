"""Nastroje agenta: co muze delat v systemu.

Kazdy nastroj ma JSON schema (pro function calling) a funkci run().
Spousteni ridi policy (allow/ask/deny) — viz agent.py.
"""
import json
import os
import shutil
import subprocess
import urllib.request

MAX_READ = 32_000
CMD_TIMEOUT = 120


def _tool(name, description, properties, required=None):
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required or [],
        },
    }


def tool_schemas() -> list:
    return [
        _tool("system_info", "Vrati zakladni info o systemu (verze, RAM, disk, uptime).", {}),
        _tool("list_dir", "Vypise obsah adresare.", {"path": {"type": "string"}}, ["path"]),
        _tool(
            "read_file",
            "Precte textovy soubor (max 32 kB).",
            {"path": {"type": "string"}},
            ["path"],
        ),
        _tool(
            "write_file",
            "Zapise text do souboru (prepise ho). Adresar musi existovat.",
            {"path": {"type": "string"}, "content": {"type": "string"}},
            ["path", "content"],
        ),
        _tool(
            "run_command",
            "Spusti shell prikaz jako uzivatel (bez roota). Vhodne i pro flatpak, systemctl --user atd.",
            {"command": {"type": "string"}},
            ["command"],
        ),
        _tool(
            "open_app",
            "Otevre aplikaci podle .desktop id nebo jmena (napr. brave-browser).",
            {"app": {"type": "string"}},
            ["app"],
        ),
        _tool(
            "install_flatpak",
            "Nainstaluje Flatpak aplikaci z Flathubu podle app ID.",
            {"app_id": {"type": "string"}},
            ["app_id"],
        ),
        _tool(
            "remove_flatpak",
            "Odebere Flatpak aplikaci podle app ID.",
            {"app_id": {"type": "string"}},
            ["app_id"],
        ),
        _tool(
            "web_get",
            "Stahne text webove stranky (max 32 kB).",
            {"url": {"type": "string"}},
            ["url"],
        ),
    ]


def tool_names() -> list:
    return [t["name"] for t in tool_schemas()]


def run(name: str, args: dict) -> str:
    fn = _IMPL.get(name)
    if fn is None:
        return f"Neznamy nastroj: {name}"
    try:
        return fn(args or {})
    except Exception as e:  # noqa: BLE001 - vysledek jde zpet modelu
        return f"Chyba: {e}"


def _system_info(_args) -> str:
    out = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    out["system"] = line.split("=", 1)[1].strip().strip('"')
    except OSError:
        out["system"] = "neznamy"
    try:
        mem = {}
        with open("/proc/meminfo", encoding="utf-8") as f:
            for line in f:
                k, _, v = line.partition(":")
                if k in ("MemTotal", "MemAvailable"):
                    mem[k] = v.strip()
        out.update(mem)
    except OSError:
        pass
    try:
        total, used, free = shutil.disk_usage(os.path.expanduser("~"))
        out["disk_home"] = f"celkem {total // 2**30} GB, volno {free // 2**30} GB"
    except OSError:
        pass
    try:
        with open("/proc/uptime", encoding="utf-8") as f:
            out["uptime_s"] = int(float(f.read().split()[0]))
    except OSError:
        pass
    return json.dumps(out, ensure_ascii=False)


def _list_dir(args) -> str:
    path = os.path.expanduser(args.get("path", "~"))
    items = sorted(os.listdir(path))
    return "\n".join(items[:200]) or "(prazdne)"


def _read_file(args) -> str:
    path = os.path.expanduser(args["path"])
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read(MAX_READ)


def _write_file(args) -> str:
    path = os.path.expanduser(args["path"])
    with open(path, "w", encoding="utf-8") as f:
        f.write(args.get("content", ""))
    return f"Zapsano: {path}"


def _run_command(args) -> str:
    proc = subprocess.run(
        args["command"],
        shell=True,
        capture_output=True,
        text=True,
        timeout=CMD_TIMEOUT,
    )
    out = (proc.stdout + proc.stderr).strip()
    return f"(navrat {proc.returncode})\n{out[:8000]}" if out else f"(navrat {proc.returncode})"


def _open_app(args) -> str:
    target = args["app"]
    if not target.endswith(".desktop"):
        target += ".desktop"
    for d in ("/usr/share/applications", os.path.expanduser("~/.local/share/applications")):
        if os.path.exists(os.path.join(d, target)):
            subprocess.Popen(["gtk-launch", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Otevreno: {target}"
    return f"Aplikace nenalezena: {args['app']}"


def _flatpak(args, op: str) -> str:
    cmd = ["flatpak", op, "-y", args["app_id"]] if op == "install" else ["flatpak", op, "-y", args["app_id"]]
    if op == "install":
        cmd = ["flatpak", "install", "-y", "flathub", args["app_id"]]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    out = (proc.stdout + proc.stderr).strip()
    return (out[-3000:] or "Hotovo.") if proc.returncode == 0 else f"Chyba: {out[-3000:]}"


def _install_flatpak(args) -> str:
    return _flatpak(args, "install")


def _remove_flatpak(args) -> str:
    return _flatpak(args, "uninstall")


def _web_get(args) -> str:
    req = urllib.request.Request(args["url"], headers={"User-Agent": "KucLabLX/1.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(MAX_READ).decode("utf-8", "replace")


_IMPL = {
    "system_info": _system_info,
    "list_dir": _list_dir,
    "read_file": _read_file,
    "write_file": _write_file,
    "run_command": _run_command,
    "open_app": _open_app,
    "install_flatpak": _install_flatpak,
    "remove_flatpak": _remove_flatpak,
    "web_get": _web_get,
}
