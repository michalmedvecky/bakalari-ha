# Přehled změn

Verze odpovídají souboru `custom_components/bakalari/manifest.json`. Značky vydání mají podobu `vMAJOR.MINOR.PATCH`.

## Připravuje se

Zatím bez dalších změn.

## 1.0.0 — 2026-10-17

První veřejné vydání integrace Bakalářů pro Home Assistant.

### Funkce

- Konfigurace v uživatelském rozhraní, více účtů a opětovné přihlášení.
- Asynchronní klient API v3 se synchronizovanou obnovou tokenů.
- Známky a průměry, domácí úkoly, absence, Komens, přehledy a třídní fond.
- Kalendáře rozvrhu a školních akcí, seznam úkolů a přítomnost ve škole.
- Deset akcí pro dotazy API, aktualizaci, Komens, dokončení úkolů, podpis a předvídání známek, třídní knihu, přílohy a webové přihlášení.
- Volitelné podrobné atributy a diagnostika bez školních dat a přihlašovacích údajů.
- Český návod, formuláře, popisy akcí a šablony pro spolupráci.
- Automatické testy, kontrola formátu a sestavení instalačního ZIPu při vydání.

### Ověření a omezení

Automatické testy vycházejí z Home Assistantu 2026.3.4 a simulovaných odpovědí. Kompatibilita se skutečným účtem konkrétní školy zatím nebyla ověřena. Dostupnost modulů závisí na verzi API, licenci a oprávněních účtu. Podrobnosti popisuje `docs/API_COVERAGE.md`.
