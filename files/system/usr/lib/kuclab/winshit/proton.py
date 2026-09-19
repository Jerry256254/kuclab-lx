"""WinShit backend: Proton-GE (stazeni pri prvnim spusteni), prefixy, beh pres umu."""
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request

DATA = os.path.join(os.path.expanduser("~/.local/share"), "winshit")
PROTON_DIR = os.path.join(DATA, "proton")
PREFIXES = os.path.join(DATA, "prefixes")
HISTORY = os.path.join(DATA, "history.json")
DEFAULT_PREFIX = os.path.join(PREFIXES, "default")

GE_API = "https://api.github.com/repos/GloriousEggroll/proton-ge-custom/releases/latest"


def _direct_opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def proton_ready() -> bool:
    return os.path.exists(os.path.join(PROTON_DIR, "proton"))

def umu_available() -> bool:
    return shutil.which("umu-run") is not None


def fetch_proton_ge(on_progress) -> str:
    """Stahne a rozbali nejnovejsi Proton-GE. Vraci chybu nebo ''."""
    os.makedirs(DATA, exist_ok=True)
    try:
        with _direct_opener().open(GE_API, timeout=30) as r:
            release = json.load(r)
        url = ""
        for asset in release.get("assets", []):
            if asset.get("name", "").endswith(".tar.gz"):
                url = asset["browser_download_url"]
                break
        if not url:
            return "Proton-GE release nenalezen."
        tmp = os.path.join(DATA, "proton-ge.tar.gz")

        def hook(blocks, block_size, total):
            if total > 0:
                on_progress(min(1.0, blocks * block_size / total))

        urllib.request.urlretrieve(url, tmp, reporthook=hook)
        if os.path.exists(PROTON_DIR):
            shutil.rmtree(PROTON_DIR)
        os.makedirs(PROTON_DIR, exist_ok=True)
        with tarfile.open(tmp) as tar:
            # tarball obsahuje jednu korenovou slozku -> presuneme obsah
            top = tar.getnames()[0].split("/")[0]
            tar.extractall(DATA)
            src = os.path.join(DATA, top)
            for item in os.listdir(src):
                shutil.move(os.path.join(src, item), PROTON_DIR)
            shutil.rmtree(src, ignore_errors=True)
        os.unlink(tmp)
        return ""
    except Exception as e:  # noqa: BLE001
        return str(e)


def ensure_prefix(name: str = "default") -> str:
    path = DEFAULT_PREFIX if name == "default" else os.path.join(PREFIXES, name)
    os.makedirs(path, exist_ok=True)
    return path


def run_exe(exe_path: str, prefix: str | None = None) -> subprocess.Popen:
    prefix = prefix or ensure_prefix()
    env = dict(os.environ)
    env["WINEPREFIX"] = prefix
    env["PROTONPATH"] = PROTON_DIR
    env["UMU_LOG"] = "0"
    return subprocess.Popen(
        ["umu-run", exe_path],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def load_history() -> list:
    try:
        with open(HISTORY, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def save_history(items: list) -> None:
    os.makedirs(DATA, exist_ok=True)
    tmp = HISTORY + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(items[-30:], f, ensure_ascii=False, indent=1)
    os.replace(tmp, HISTORY)


def remember(exe_path: str) -> None:
    items = [i for i in load_history() if i.get("path") != exe_path]
    items.append({"path": exe_path, "name": os.path.basename(exe_path)})
    save_history(items)
