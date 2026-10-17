# Přehled změn

Verze odpovídají souboru `custom_components/bakalari/manifest.json`. Značky vydání mají podobu `vMAJOR.MINOR.PATCH`.

## Připravuje se

Zatím bez dalších změn.

## 1.0.1 — 2026-10-17

Opravné vydání podle instalačního a vývojářského reportu z HA Green.

- Akce se registrují v `async_setup` a zůstávají dostupné po odpojení posledního účtu. Nenačtený účet vrací chybu místo zmizení definice akce.
- Názvy entit používají `translation_key`; předmět se vkládá pomocí překladového parametru. Překlady akcí a polí jsou doplněné v češtině i angličtině. Unikátní ID entit zůstávají stejná.
- Diagnostika načítá skutečnou verzi z loaderu integrace.
- Odstraněn nepoužívaný atribut `coordinator.successful`.
- Volitelný režim pouze pro čtení blokuje zápisy i webové přihlášení a vypne úpravy seznamu úkolů. Výchozí chování stávajících účtů se nemění.
- Výjimky používají zápis se závorkami; nastavení Ruffu a test syntaxe zabraňují návratu zápisu PEP 758. Minimum HA zůstává 2026.3, které již používá Python 3.14.
- CI ověřuje HA 2026.3.4 i 2026.10.1. Testy HTTP používají lokální server namísto knihovny závislé na interním rozhraní aiohttp.
- Dokumentace výslovně popisuje zápisy do školního systému a rozlišuje instalační ověření od funkčního ověření přihlášeného účtu.

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
