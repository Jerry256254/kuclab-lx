# KucLab LX — architektura

## Rozhodnutí (potvrzeno)

| Volba | Výběr | Proč |
|---|---|---|
| Základ | Bluefin (GNOME, Fedora Atomic) | Drivery, firmware a akmods v ceně; RPM/ostree |
| Lokální LLM | Ollama | Nejjednodušší běh modelů + OpenAI-kompatibilní API |
| WinShit | Wine/Proton vrstva (umu + Proton-GE) | Lehké, bez Windows licence; VM by žrala RAM |
| UI toolkit | Python + GTK4/libadwaita | Nativní pro GNOME, malé, rychlé, bez Electronu |

## Vrstvy obrazu

1. `base.yml` — kargs, fstrim.
2. `drivers.yml` — akmods (gamepady, Razer, Framework, v4l2loopback) + NVIDIA open driver.
3. `desktop.yml` — gschema overrides (dock, tmavý režim, Inter) + fonty.
4. `packages.yml` — ptyxis, Brave (oficiální RPM repo), Mullvad VPN, wine/umu, GTK knihovny; pryč `gnome-software`.
5. `flatpaks.yml` — jen příprava Flathub repa (prohlížeč je nativní Brave s DuckDuckGo přes `/etc/brave/policies`).
6. `kuclab.yml` — naše soubory, binárky (Ollama, whisper, Piper), locales, služby.
7. `branding.yml` — `/etc/os-release` (schválně poslední).

## AI agent

- **Daemon** `kuclab-agent.service` (user): JSON přes unix socket
  `~/.run/kuclab-agent.sock`. Nástroje: info o systému, soubory,
  příkazy, aplikace, flatpaky, web.
- **Oprávnění** `~/.config/kuclab/agent-policy.json`: každý nástroj
  `allow/ask/deny` + profily (konzervativní / vyvážený / plná důvěra).
- **Modely**: primárně lokální Ollama (`qwen3:4b` výchozí),
  alternativně libovolné OpenAI-kompatibilní API (adresa + klíč + model).
- **Chat**: `org.kuclab.AgentChat` — první v docku (favorites), panel
  tlačítko + `Super+K` přes rozšíření `kuclab-agent@kuclab.lx`.
- **Hlas**: whisper.cpp STT + Piper TTS, vše lokálně; modely se stahují
  až při prvním použití do `~/.local/share/kuclab/models/`.

## Store / Manager / WinShit

- **Store**: AppStream katalog (rychlé lokální hledání) + Flatpak
  transakce; předchystané zdroje Flathub Beta, GNOME Nightly, Fedora.
- **Manager**: přehled systému, běžící služby, odebrání aplikací
  (flatpak okamžitě, vrstvené RPM s restartem). Chráněné jádro
  (`PROTECTED_RPM`) odebrat nejde — systém zůstane bootovatelný.
- **WinShit**: `umu-run` + Proton-GE (stahuje se při prvním spuštění),
  prefixy v `~/.local/share/winshit/prefixes`.

## RAM rozpočet (bez AI modelů)

Bluefin idle ~1,2–1,6 GB. Naše vrstva přidává: Ollama bez modelu
~100 MB, agent ~60 MB, aplikace jen při běhu. Cíl ≤ 4 GB s rezervou.
Modely (LLM/STT/TTS) se do limitu nepočítají — stahují se na vyžádání
a Ollama je po 10 minutách nečinnosti uvolní (`OLLAMA_KEEP_ALIVE=10m`).

## Jazyky

Zdrojové řetězce jsou česky, překlad v
`files/system/usr/share/kuclab/po/<lang>.po`, kompilace při buildu
vlastním msgfmt (bez závislostí). Nový jazyk = nový `.po` soubor.
Test `tests/test_locales.py` hlídá 100% pokrytí.

## Build a testy

```sh
bluebuild build recipes/recipe.yml     # obraz
bluebuild generate-iso recipes/recipe.yml  # instalacni ISO
python3 -m unittest discover -s tests  # python testy
```

## Co zbývá před vydáním

1. Build v CI + nabootovat ISO na 2–3 strojích (Intel/AMD/NVIDIA).
2. Změřit idle RAM a doladit služby.
3. Doplnit němčinu/překlady dle potřeby.
4. Podepsat obraz (cosign klíče v CI secrets).
