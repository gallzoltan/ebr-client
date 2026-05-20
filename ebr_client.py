import csv
import json
import re
import tempfile
from pathlib import Path
from typing import Any

import openpyxl
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

BASE_URL = "https://ebr42.gov.hu"
PALYAZAT_URL = f"{BASE_URL}/palyazat"

_RPP_SELECT = "form1:talalatiTablazat_rppDD"
_EXPORT_FULL = "form1:urlapokFullExport"   # összes rekord
_EXPORT_CURRENT = "form1:urlapokExport"    # szűrt/aktuális nézet


class EbrClient:
    def __init__(self, username: str, password: str, headless: bool = True):
        self.username = username
        self.password = password
        self.headless = headless
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> "EbrClient":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self.headless)
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        await self._login()
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    async def _login(self) -> None:
        assert self._page is not None
        await self._page.goto(PALYAZAT_URL)
        await self._page.wait_for_selector('[name="username"]', timeout=15000)
        await self._page.fill('[name="username"]', self.username)
        await self._page.fill('[name="password"]', self.password)
        await self._page.click('[type="submit"]')
        await self._page.wait_for_load_state("networkidle", timeout=20000)

    async def _navigate_to_list(self) -> None:
        assert self._page is not None
        html = await self._page.content()
        token_match = re.search(r'jakarta\.faces\.Token=([^&"\'<\s]+)', html)
        if not token_match:
            raise RuntimeError("Nem található jakarta.faces.Token.")
        token = token_match.group(1)
        url = f"{PALYAZAT_URL}/palyazatok/urlapok.xhtml?jakarta.faces.Token={token}&tipus=palyazat"
        await self._page.goto(url)
        await self._page.wait_for_load_state("networkidle", timeout=20000)

    async def _download_xlsx(self, export_btn_name: str) -> Path:
        """Letölti az xlsx exportot, ideiglenes fájlba menti, visszaadja az elérési utat."""
        assert self._page is not None
        async with self._page.expect_download(timeout=60000) as dl_info:
            await self._page.evaluate(
                f"() => document.querySelector(\"[name='{export_btn_name}']\").click()"
            )
        download = await dl_info.value
        tmp = Path(tempfile.mktemp(suffix=".xlsx"))
        await download.save_as(tmp)
        return tmp

    @staticmethod
    def _parse_xlsx(path: Path) -> list[dict]:
        """Beolvassa az xlsx fájlt, visszaadja a sorokat dict listáként."""
        wb = openpyxl.load_workbook(path)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()
        if not rows:
            return []
        headers = [str(h).strip() if h is not None else f"col_{i}" for i, h in enumerate(rows[0])]
        result = []
        for row in rows[1:]:
            if not any(v is not None for v in row):
                continue
            record = {headers[i]: (str(v).strip() if v is not None else "") for i, v in enumerate(row)}
            result.append(record)
        return result

    async def get_palyazatok(self, ev: int, nev: str | None = None) -> list[dict]:
        """Letölti az összes pályázatot xlsx-ként, majd Python-oldalon szűr."""
        await self._navigate_to_list()
        print("  xlsx letöltés...")
        xlsx_path = await self._download_xlsx(_EXPORT_FULL)
        all_data = self._parse_xlsx(xlsx_path)
        xlsx_path.unlink(missing_ok=True)
        print(f"  {len(all_data)} rekord kiolvasva az xlsx-ből")

        # Python-oldali szűrés
        result = [r for r in all_data if str(ev) in r.get("Év", "")]
        if nev:
            nev_lower = nev.lower()
            result = [r for r in result if nev_lower in r.get("Pályázat/Űrlap", "").lower()]
        return result

    async def download_raw_xlsx(self, filename: str = "export_full.xlsx") -> str:
        """Letölti a teljes xlsx exportot szűrés nélkül."""
        await self._navigate_to_list()
        xlsx_path = await self._download_xlsx(_EXPORT_FULL)
        Path(filename).unlink(missing_ok=True)
        Path(xlsx_path).rename(filename)
        print(f"xlsx mentve: {filename}")
        return filename

    def export_csv(self, data: list[dict], filename: str) -> None:
        if not data:
            print(f"Nincs adat: {filename}")
            return
        with open(filename, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0].keys()))
            writer.writeheader()
            writer.writerows(data)
        print(f"CSV: {filename} ({len(data)} sor)")

    def export_json(self, data: list[dict], filename: str) -> None:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"JSON: {filename} ({len(data)} rekord)")
