# KucLab LX

Čistá, rychlá a jednoduchá linuxová distribuce postavená na [BlueBuild](https://blue-build.org)
a základu Universal Blue (Fedora Atomic + GNOME).

**Chceš to rozjet?** Postup krok za krokem je v [docs/INSTALACE.md](docs/INSTALACE.md)
(ISO se staví samo na GitHubu, pak flashnout na USB nebo připojit do VirtualBoxu).

- **Základ:** Bluefin (GNOME, RPM/ostree) — moderní, atomický, bez bloatwaru
- **Cíl:** plynulý systém do 4 GB RAM (bez lokálních AI modelů), vše funguje bez řešení driverů
- **Vlastní aplikace:** AI agent, Store, Manager, WinShit
- **Jazyky:** vícejazyčné (gettext, výchozí CS/EN)

## Struktura

```
recipes/                     BlueBuild recept (recipe.yml + common/*.yml)
files/system/usr/lib/kuclab/ zdrojáky vlastních aplikací (Python + GTK4/libadwaita)
files/system/usr/share/      .desktop soubory, ikony, rozsireni GNOME
files/scripts/               build skripty (Ollama, hlas, locales)
files/systemd/               systemd unity
files/gschema-overrides/     vychozi nastaveni GNOME
docs/                        architektura a rozhodnutí
.github/workflows/           CI build obrazu
```

Zdrojáky aplikací jsou přímo ve `files/system/`, aby je `files` modul
při buildu zkopíroval do obrazu 1:1 (bez kopírovací magie).

## Build

```sh
# lokální build (vyžaduje bluebuild CLI)
bluebuild build recipes/recipe.yml

# ISO pro instalaci
bluebuild generate-iso recipes/recipe.yml

# python testy (bez závislostí)
python3 -m unittest discover -s tests
```

Nový jazyk = nový soubor `files/system/usr/share/kuclab/po/<lang>.po`
(vzor viz `en.po`). Pokrytí hlídá `tests/test_locales.py`.

## Vlastní aplikace

| Aplikace | Popis |
|---|---|
| Agent (`org.kuclab.AgentChat`) | lokální AI agent (Ollama + libovolné API), popup chat, hlas (Whisper STT + Piper TTS), oprávnění pod kontrolou uživatele |
| Store (`org.kuclab.Store`) | rychlý obchod s aplikacemi (Flathub + další remotes) |
| Manager (`org.kuclab.Manager`) | správce systému, disků a balíčků (odebere vše kromě chráněného základu) |
| WinShit (`org.kuclab.WinShit`) | lehký běh Windows aplikací přes Wine/Proton (umu) |

Detaily viz [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
