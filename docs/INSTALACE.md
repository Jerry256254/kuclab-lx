# Jak rozjet KucLab LX

ISO s instalátorem se staví automaticky na GitHubu. Na svém počítači
k tomu nepotřebuješ Linux ani nic instalovat — stačí prohlížeč.

## Cesta A: ISO z GitHubu (doporučeno)

1. Vytvoř nové **public** repo na GitHubu (např. `kuclab-lx`) a pushni
   do něj obsah tohoto adresáře:
   ```sh
   git init && git add -A && git commit -m "KucLab LX" \
     && git branch -M main \
     && git remote add origin git@github.com:<uzivatel>/kuclab-lx.git \
     && git push -u origin main
   ```
2. V repo jdi na **Actions** a počkej na workflow **KucLab LX image**
   (postaví obraz, cca 20–40 minut).
3. Po jeho úspěchu se samo spustí **KucLab LX ISO**. Kdybys chtěl
   ISO znovu, spusť ho ručně: **Actions → KucLab LX ISO → Run workflow**.
4. Hotové ISO stáhni z detailu běhu, sekce **Artifacts → kuclab-lx-iso**
   (soubor `kuclab-lx.iso`, cca 4–7 GB).

Pozn.: první build obrazu vyžaduje secret `COSIGN_PRIVATE_KEY`
(vygeneruješ příkazem `cosign generate-key-pair`, přidáš v
**Settings → Secrets → Actions**). Bez něj obraz neprojde signing krokem.

## Cesta B: build na vlastním linuxovém PC

Potřebuješ Fedoru (40+), ~30 GB volného místa a cca hodinu času:

```sh
# 1. CLI (oficialni zpusob)
docker run --pull always --rm ghcr.io/blue-build/cli:latest-installer | sudo bash

# 2. ISO primo z receptu (postavi obraz i ISO najednou)
cd /cesta/k/tomuto/repu
sudo bluebuild generate-iso --iso-name kuclab-lx.iso recipe recipes/recipe.yml
```

Výsledek je `kuclab-lx.iso` v aktuálním adresáři.

## Instalace na PC (USB)

1. ISO flashni na USB (8 GB+) přes
   [Fedora Media Writer](https://www.fedoraproject.org/en/workstation/download),
   Rufus, nebo Ventoy.
2. Nabootuj z USB, projdi instalátorem (jazyk, disk, uživatel).
3. Po restartu se přihlas — agent je první ikonka v dolním docku.

Tip: pokud máš Secure Boot a instalátor si stěžuje, dočasně ho vypni
v BIOSu. Podpora klíčů pro Secure Boot se doladí po prvním otestování.

## Vyzkoušení ve VirtualBoxu

1. Nový virtuální stroj: typ **Fedora (64-bit)**, **4 GB RAM** (bez AI
   modelů stačí), 2 CPU, disk **25 GB VDI**, zapni **EFI** (Nastavení →
   Systém → Povolit EFI).
2. Do optické mechaniky vlož stažené `kuclab-lx.iso` a spusť.
3. Projdi instalátorem, po restartu odpoj ISO a nabootuj z disku.

## Po instalaci

- Lokální AI model se stáhne sám při prvním dotazu agentovi
  (výchozí `qwen3:4b`, cca 2,5 GB).
- Hlasové modely a Proton-GE pro WinShit se stahují až při prvním
  použití — obraz i instalace jsou proto malé a rychlé.
