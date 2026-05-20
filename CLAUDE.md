# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```powershell
# Környezet létrehozása és függőségek telepítése
uv venv
uv sync

# Playwright böngésző telepítése (első alkalommal)
uv run playwright install chromium

# Futtatás
uv run python example.py

# Szerveren (Linux): böngésző + rendszerfüggőségek
uv run playwright install chromium --with-deps
```

Belépési adatok környezeti változóból:
```powershell
$env:EBR_USER = "felhasznalonev"
$env:EBR_PASS = "jelszo"
```

## Architektúra

**Célrendszer:** `https://ebr42.gov.hu/palyazat` – PrimeFaces 12 / Jakarta EE alapú kormányzati webalkalmazás, Keycloak SSO autentikációval. Nincs REST API.

**Fő osztály:** `EbrClient` (`ebr_client.py`) – async context manager, Playwright Chromium böngészőt vezérel.

**Adatkinyerési folyamat:**
1. Keycloak bejelentkezés (`/palyazat` → átirányít → form kitöltés)
2. `jakarta.faces.Token` kinyerése az index oldal HTML-jéből regex-szel (sessionfüggő, minden bejelentkezés után más)
3. Navigálás: `/palyazat/palyazatok/urlapok.xhtml?jakarta.faces.Token=...&tipus=palyazat`
4. Az `urlapokFullExport` gomb JS-sel kattintva letölti az összes rekordot xlsx-ben (`expect_download`)
5. xlsx beolvasás `openpyxl`-lel, majd Python-oldali szűrés

**Miért nem szerver-oldali szűrés:** A PrimeFaces TreeTable oszlopszűrői (AutoComplete widget + AJAX overlay) Playwright-tel nem triggerelhetők megbízhatóan. Az xlsx export (~1400 sor, ~64KB) egy lépésben megkapja az összes adatot.

**Kritikus részlet:** `openpyxl.load_workbook(path)` – kötelezően `read_only=False` (az alapértelmezett). `read_only=True`-val csak 1 sor/oszlop érkezik vissza.

**xlsx oszlopok:** `Igénylésazonosító`, `Ksh azonosító`, `Év`, `Pályázat/Űrlap`, `Önkormányzat`, `Vármegye`, `Állapot`
