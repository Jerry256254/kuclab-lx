"""KucLab Manager: system, sluzby, balicky, disky.

Odebrat jde vse krome chraneneho zakladu (PROTECTED) — system tak zustane
vzdy bootovatelny a desktop funkcni.
"""
import json
import os
import shutil
import subprocess

# Balicky a aplikace, bez kterych by system nefungoval. Tyto Manager nenabidne.
PROTECTED_RPM = {
    "kernel", "kernel-core", "ostree", "rpm-ostree", "bootc", "systemd",
    "gnome-shell", "gnome-session", "gnome-control-center", "mutter",
    "ptyxis", "flatpak", "NetworkManager", "pipewire", "wireplumber",
}
PROTECTED_FLATPAK = set()  # flatpaky nejsou kriticke, vsechny jdou odebrat


def run(cmd: list, timeout=60) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except (OSError, subprocess.TimeoutExpired) as e:
        return 1, str(e)


def system_info() -> dict:
    info = {}
    try:
        with open("/etc/os-release", encoding="utf-8") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    info["os"] = line.split("=", 1)[1].strip().strip('"')
    except OSError:
        info["os"] = "KucLab LX"
    try:
        with open("/proc/cpuinfo", encoding="utf-8") as f:
            for line in f:
                if line.startswith("model name"):
                    info["cpu"] = line.split(":", 1)[1].strip()
                    break
    except OSError:
        pass
    try:
        with open("/proc/meminfo", encoding="utf-8") as f:
            mem = {}
            for line in f:
                k, _, v = line.partition(":")
                if k in ("MemTotal", "MemAvailable"):
                    mem[k] = int(v.strip().split()[0]) // 1024
            info["ram_total_mb"] = mem.get("MemTotal", 0)
            info["ram_avail_mb"] = mem.get("MemAvailable", 0)
    except OSError:
        pass
    return info


def disk_usage() -> list:
    _, out = run(["df", "-h", "--output=source,size,used,avail,pcent,target", "-x", "tmpfs", "-x", "devtmpfs"])
    rows = []
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 6:
            rows.append({"device": parts[0], "size": parts[1], "used": parts[2], "avail": parts[3], "pct": parts[4], "mount": parts[5]})
    return rows


def block_devices() -> list:
    _, out = run(["lsblk", "-J", "-o", "NAME,SIZE,TYPE,MOUNTPOINT,MODEL"])
    try:
        return json.loads(out or "{}").get("blockdevices", [])
    except ValueError:
        return []


def services() -> list:
    _, out = run(["systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--plain"])
    svcs = []
    for line in out.splitlines():
        name = line.split()[0] if line.split() else ""
        if name.endswith(".service"):
            svcs.append(name)
    return sorted(svcs)


def service_action(name: str, action: str) -> str:
    if action not in ("stop", "restart"):
        return "nepodporovano"
    rc, out = run(["systemctl", action, name], timeout=30)
    return "" if rc == 0 else out[-500:]


def flatpak_apps() -> list:
    rc, out = run(["flatpak", "list", "--app", "--columns=application,name,version,installation"])
    apps = []
    if rc != 0:
        return apps
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            apps.append({"id": parts[0].strip(), "name": (parts[1] if len(parts) > 1 else parts[0]).strip(), "kind": "flatpak", "protected": parts[0].strip() in PROTECTED_FLATPAK})
    return apps


def layered_rpm() -> list:
    rc, out = run(["rpm-ostree", "status", "--json"])
    pkgs = []
    if rc != 0:
        return pkgs
    try:
        data = json.loads(out)
        for dep in data.get("deployments", [])[:1]:
            for p in dep.get("requested-packages", []):
                pkgs.append({"id": p, "name": p, "kind": "rpm", "protected": p in PROTECTED_RPM})
    except ValueError:
        pass
    return pkgs


def remove_package(kind: str, pkg_id: str) -> str:
    if kind == "flatpak":
        if pkg_id in PROTECTED_FLATPAK:
            return "Chraneny balicek."
        rc, out = run(["flatpak", "uninstall", "-y", pkg_id], timeout=300)
        return "" if rc == 0 else out[-1000:]
    if pkg_id in PROTECTED_RPM:
        return "Chraneny systemovy balicek."
    rc, out = run(["rpm-ostree", "override", "remove", pkg_id], timeout=600)
    if rc == 0:
        return "OK-REBOOT"
    return out[-1000:]
