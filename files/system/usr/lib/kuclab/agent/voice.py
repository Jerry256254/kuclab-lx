"""Hlas: lokalni STT (whisper.cpp) a TTS (Piper), nahravani pres pw-cat.

Modely se stahuji pri prvnim pouziti do ~/.local/share/kuclab/models/.
"""
import os
import subprocess
import urllib.request

import config

WHISPER_BIN = os.path.join(config.BIN_DIR, "whisper-cli")
PIPER_BIN = os.path.join(config.BIN_DIR, "piper")

WHISPER_MODELS = {
    "cs": ("ggml-small.bin", "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin"),
    "en": ("ggml-small.en.bin", "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin"),
}
PIPER_VOICES = {
    "cs": ("cs_CZ-jirka-medium.onnx", "https://huggingface.co/rhasspy/piper-voices/resolve/main/cs/cs_CZ/jirka/medium/cs_CZ-jirka-medium.onnx"),
    "en": ("en_US-lessac-medium.onnx", "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"),
}


def available() -> tuple[bool, bool]:
    return os.path.exists(WHISPER_BIN), os.path.exists(PIPER_BIN)


def _model_dir(kind: str) -> str:
    d = os.path.join(config.DATA_DIR, "models", kind)
    os.makedirs(d, exist_ok=True)
    return d


def _download(url: str, dest: str) -> None:
    if os.path.exists(dest):
        return
    tmp = dest + ".part"
    urllib.request.urlretrieve(url, tmp)
    os.replace(tmp, dest)


def whisper_model(lang: str) -> str:
    name, url = WHISPER_MODELS.get(lang, WHISPER_MODELS["en"])
    dest = os.path.join(_model_dir("whisper"), name)
    _download(url, dest)
    return dest


def piper_voice(lang: str) -> str:
    name, url = PIPER_VOICES.get(lang, PIPER_VOICES["en"])
    dest = os.path.join(_model_dir("piper"), name)
    _download(url, dest)
    _download(url + ".json", dest + ".json")
    return dest


def start_recording(path: str):
    """Spusti nahravani mikrofonu (16 kHz mono). Vraci proces nebo None."""
    try:
        return subprocess.Popen(
            ["pw-cat", "--record", "--rate", "16000", "--channels", "1", path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return None


def stop_recording(proc) -> bool:
    """Ukonci nahravani. Vraci True, pokud vznikl soubor."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        try:
            proc.kill()
        except OSError:
            pass
    return True


def transcribe(wav_path: str, lang: str) -> str:
    model = whisper_model(lang)
    proc = subprocess.run(
        [WHISPER_BIN, "-m", model, "-f", wav_path, "-l", lang, "-nt", "-np"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    return proc.stdout.strip()


def speak(text: str, lang: str) -> bool:
    """Precte text nahlas. Vraci uspech."""
    try:
        voice = piper_voice(lang)
    except OSError:
        return False
    try:
        piper = subprocess.Popen(
            [PIPER_BIN, "--model", voice, "--output-raw"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        raw, _ = piper.communicate(text.encode("utf-8")[:2000], timeout=120)
        if not raw:
            return False
        play = subprocess.Popen(
            ["pw-cat", "--playback", "--rate", "22050", "--channels", "1", "-"],
            stdin=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        play.communicate(raw, timeout=120)
        return True
    except (OSError, subprocess.TimeoutExpired):
        return False
