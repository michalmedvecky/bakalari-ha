# Přehled změn

Verze odpovídají souboru `custom_components/bakalari/manifest.json`. Značky vydání mají podobu `vMAJOR.MINOR.PATCH`.

## Připravuje se

- Omluvenky: `dry_run` vrací náhled a příjemce bez odeslání; funguje i v režimu pouze pro čtení a vyžaduje návratovou proměnnou.
- Volitelné párové časy `time_from` / `time_to` a vlastní předmět. Výchozí předmět je `Omluvenka DD.MM.RRRR`. Přesné zpracování časů školou zatím není ověřeno.
- Odpověď omluvenky nově obsahuje příjemce, příznaky náhledu/odeslání a ID zprávy, pokud ho POST skutečně vrátí. Původní odpověď zůstává v `result`.
- Přehled Komens vybírá nejnovější zprávy podle `SentDate` před zkrácením, nezávisle na pořadí API.
- Atributy `subject_id` a `average_text` odstraňují okolní mezery; unikátní ID entit zůstávají zachovaná.
- **Změna chování:** `send_message` nově dovoluje pouze `OBECNA` a `OMLUVENKA`, aby neodesílal školní publikační typy nabídnuté žákům. Automatizace s jinými typy je nutné upravit.
- Zaznamenáno instalační ověření verze 1.1.0 z 19. října; skutečné odesílání omluvenek zůstává neověřené.

## 1.1.0 — 2026-10-18

Samostatná akce pro odesílání omluvenek přes Komens přímo z Home Assistantu.

- Nová akce `bakalari.send_apology` přijímá účet `entry_id`, datum od `date_from`, datum do `date_to` a důvod absence `reason`.
- Obě data zahrnují celé dny v časovém pásmu Home Assistantu, včetně správného přechodu mezi letním a zimním časem.
- Příjemce se zjišťuje při každém volání z typu `OMLUVENKA`: vybere se jediný výchozí učitel, případně jediný povolený učitel. Nejednoznačný nebo chybějící příjemce zabrání odeslání.
- Neplatná data, obrácený rozsah nebo prázdný důvod se odmítnou před komunikací se školou. Akce respektuje režim **Pouze pro čtení**.
- Doplněné české názvy, popisy a chyby v editoru akcí, anglické náhradní překlady a český návod v README.
- Přiložený příklad `examples/omluvenka.yaml` obsahuje datové pomocníky, důvod absence a tlačítko pro odeslání. Příklady jsou součástí instalačního archivu.

### Použití

```yaml
action: bakalari.send_apology
data:
  entry_id: VASE_ENTRY_ID
  date_from: "2026-10-19"
  date_to: "2026-10-20"
  reason: "Prosím o omluvení absence z důvodu nemoci."
```

Zápis vyžaduje odpovídající práva účtu, obvykle rodičovského, a vypnutou volbu **Pouze pro čtení**. Akce odešle omluvenku učiteli; její následné uznání v evidenci absence provádí škola. Po nejasném výsledku spojení zkontrolujte odeslané zprávy před dalším pokusem. Důvod absence může být viditelný ve stopách automatizace.

### Aktualizace a ověření

V HACS aktualizujte integraci na **1.1.0** a restartujte Home Assistant. Stávající konfigurace účtů zůstává zachovaná.

Ověřeno 149 testy na HA Core **2026.3.4** a **2026.10.1**, včetně volby příjemce, validace, časového pásma a blokace zápisů. Skutečné odeslání omluvenky škole zatím nebylo ověřeno.

## 1.0.2 — 2026-10-17

Opravy podle dalšího reportu z přihlášeného školního účtu.

- Těla zpráv Komens se nikdy nevkládají do atributů, ani při `expose_details`. Zůstávají pouze vybraná metadata a počet příloh.
- Dodatečné atributy mají limit 8 KiB, texty 160 znaků a seznamy nejvýše deset položek. Známky obsahují stručný výběr polí bez popisu práce, tématu a údajů o podpisu. Příznaky zkrácení a celkové počty umožňují rozpoznat neúplný přehled.
- Senzor Nové známky počítá `IsNew: true` z `/marks`; původní `/marks/count-new` je v atributu `server_count`. Unikátní ID senzoru zůstává zachované.
- Průměry jsou číselné s třídou `measurement`, původní text je v `average_text`. Nejednoznačné a slovní hodnoty mají stav `unknown`; procentní jednotka se přidává jen u výslovného `%`.
- Kalendář pravidelně načítá aktuální i příští týden, takže může o víkendu zobrazit příští hodinu v atributech. Chyba příštího týdne nevyřadí aktuální rozvrh.
- Model zařízení nahrazuje prázdný či šablonový název školy obecným `Bakaláři API v3`.
- Diagnostika uvádí `skipped_modules` a `skipped_endpoints` s rozlišením chybějícího modulu, práv a vypnutí uživatelem.
- Doplněny regresní testy víkendu, soukromí, limitu atributů, číselných stavů a diagnostiky.

**Dříve zveřejněné nebo uložené texty tato aktualizace neodstraní.** Pokud obsahovaly platné heslo, je vhodné ho změnit a prověřit dřívější historii, zálohy a výstupy automatizací. Úplná data jsou nadále dostupná výslovnou akcí `query`.

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
