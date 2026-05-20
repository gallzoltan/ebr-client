import asyncio
import os
import sys
from dotenv import load_dotenv
from ebr_client import EbrClient

load_dotenv()
sys.stdout.reconfigure(encoding="utf-8")
EBR_USER = os.getenv("EBR_USER")
EBR_PASS = os.getenv("EBR_PASS")
BASE_URL = os.getenv("BASE_URL")


async def main() -> None:
    if not EBR_USER or not EBR_PASS:
        print("Add meg a belépési adatokat:")
        print("  $env:EBR_USER = 'felhasznalonev'")
        print("  $env:EBR_PASS = 'jelszo'")
        return

    async with EbrClient(BASE_URL, EBR_USER, EBR_PASS, headless=False) as client:
        # Nyers xlsx letöltés – a tartalom vizsgálatához
        # await client.download_raw_xlsx("raw_export.xlsx")

        # Táblázatos kinyerés + CSV mentés
        # print("Lekérdezés: 2026, minden pályázat...")
        # palyazatok = await client.get_palyazatok(ev=2026)
        # client.export_csv(palyazatok, "palyazatok_2026.csv")
        # client.export_json(palyazatok, "palyazatok_2026.json")

        # Szűrés év + pályázat neve szerint
        print("Lekérdezés: 2026, 'Vis maior' névszűrővel...")
        szurt = await client.get_palyazatok(ev=2026, nev="Vis maior")
        client.export_csv(szurt, "palyazatok_2026_vis_maior.csv")
        client.export_json(szurt, "palyazatok_2026_vis_maior.json")


if __name__ == "__main__":
    asyncio.run(main())
