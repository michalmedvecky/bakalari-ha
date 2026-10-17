# Bakaláři pro Home Assistant

[![Kontroly kvality](https://github.com/michalmedvecky/bakalari-ha/actions/workflows/test.yml/badge.svg)](https://github.com/michalmedvecky/bakalari-ha/actions/workflows/test.yml)
[![Verze](https://img.shields.io/github/v/release/michalmedvecky/bakalari-ha?label=verze)](https://github.com/michalmedvecky/bakalari-ha/releases)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2026.3%2B-18BCF2)](https://www.home-assistant.io/)
[![Licence MIT](https://img.shields.io/badge/licence-MIT-green)](LICENSE)

**[Instalace](#instalace) · [Funkce](#entity) · [Akce](#akce) · [Pokrytí API](docs/API_COVERAGE.md) · [Vydání](https://github.com/michalmedvecky/bakalari-ha/releases) · [Podpora](SUPPORT.md)**

Vlastní asynchronní integrace školního systému Bakaláři API v3. Konfigurace probíhá v rozhraní Home Assistantu. Pro každé přihlášení se vytvoří samostatné zařízení; lze přidat více škol a účtů.

Implementace vychází z [bakalari-api/bakalari-api-v3](https://github.com/bakalari-api/bakalari-api-v3), revize `d4b12ddda3cd7c65c6c1b14723b432a1a2da906f`. Jde o komunitně zdokumentované API, dostupnost se liší podle verze serveru, licence školy a práv uživatele. Projekt není produktem společnosti Bakaláři.

**Požadavky:** Home Assistant 2026.3 nebo novější, webová adresa Bakalářů školy a funkční přihlašovací údaje. Automatické testy pokrývají Home Assistant 2026.3.4 a 2026.10.1 s Pythonem 3.14. Integrace nevyžaduje externí Python knihovnu.

## Instalace

### Přes HACS

1. V HACS otevřete nabídku **Vlastní repozitáře / Custom repositories**.
2. Přidejte `https://github.com/michalmedvecky/bakalari-ha` jako typ **Integrace / Integration**.
3. Vyhledejte **Bakaláři**, stáhněte integraci a restartujte Home Assistant.
4. V **Nastavení → Zařízení a služby → Přidat integraci** vyberte **Bakaláři** a zadejte údaje školy.

Repozitář je určený pro přidání jako vlastní repozitář; není součástí výchozího katalogu HACS.

### Ruční instalace

Stáhněte instalační ZIP z [nejnovějšího vydání](https://github.com/michalmedvecky/bakalari-ha/releases/latest) a rozbalte ho. Pak:

1. Zkopírujte složku `custom_components/bakalari` do adresáře `/config/custom_components/bakalari` ve své instalaci Home Assistantu. Nekopírujte vývojová virtuální prostředí.
2. Restartujte Home Assistant.
3. Otevřete **Nastavení → Zařízení a služby → Přidat integraci → Bakaláři**.
4. Zadejte URL školy, uživatelské jméno a heslo. URL může zahrnovat podsložku, například `https://school.example/baka`. Koncové `/login` se odstraní automaticky. Použijte stejnou adresu, na které funguje školní web.
5. Pro další dítě nebo jiný účet přidejte další instanci integrace. Stejný účet na stejné URL nelze přidat dvakrát.

Pro HACS používejte tento repozitář `michalmedvecky/bakalari-ha`. Odkazovaný repozitář `bakalari-api/bakalari-api-v3` slouží jako zdroj dokumentace rozhraní.

## Entity

Entity vznikají po prvním úspěšném načtení příslušného endpointu, také při pozdějším zotavení modulu. Neúspěšný modul nepředstírá nulové počty; již vytvořené entity se stanou nedostupné. Práva a povolené moduly se znovu ověřují při každé aktualizaci.

| Platforma | Data |
| --- | --- |
| Sensor | Nové známky podle čítače serveru; průměr a počet známek pro každý předmět |
| Sensor | Počet otevřených úkolů serveru a nedokončených otevřených úkolů v načteném období |
| Sensor | Počet přijatých zpráv a zpráv na nástěnce; obě počítadla nepřečtených zpráv |
| Sensor | Součty omluvených, neomluvených a nevyřešených absencí |
| Sensor | Počet změn rozvrhu, předmětů, vysvědčení a výchovných opatření; zůstatek třídního fondu |
| Binary sensor | Přítomnost žáka ve škole, pokud škola poskytuje přístupový systém a oprávnění |
| Calendar | Aktuální rozvrh s učiteli, učebnami, tématy a změnami; školní akce |
| To-do | Domácí úkoly a přepínání příznaku dokončení žákem přímo v Bakalářích |
| Button | Ruční aktualizace dat účtu |

Průměry pocházejí ze školy. Integrace zachovává `AverageText` jako text včetně procentuálního/bodového hodnocení; nepočítá vlastní průměr ani ho nepřevádí na známku. Čítač nových známek může podle dokumentace vracet nulu i u nedávno přidaných známek.

Úkoly se načítají od 30 dnů zpět do 90 dnů dopředu. Toto období je výběr podle pravidel API, nikoli úplná historie všech nedokončených úkolů. Starší úkoly jsou dostupné akcí `query` s vlastními daty. Studentovo dokončení odpovídá `Finished`; `Done` a `Closed` popisují pracovní postup učitele. Starší servery bez `Finished` zobrazí úkol jako nedokončený. Změna názvu, termínu, vytváření a mazání úkolů nejsou podporované.

Kalendář rozvrhu načítá týdny podle skutečně vyžádaného období (maximálně 93 dnů v jednom dotazu); výsledky krátce ukládá do paměti. Zrušené a odstraněné hodiny vynechává. Školní časy interpretuje v pásmu Europe/Prague včetně přechodů letního času. Celodenní události mají podle Home Assistantu výlučný konec. Historická data mimo školní rok mohou být omezena samotným serverem.

## Nastavení a přihlašovací údaje

V nabídce integrace **Konfigurovat** nastavíte interval 300–86400 sekund (výchozí 900), načítané moduly a zveřejnění podrobností v atributech. Změny integraci znovu načtou. Vypnutí modulu ponechá registrované entity jako nedostupné; znovu je zpřístupní jeho zapnutí a úspěšné načtení.

Načítání respektuje `EnabledModules` i dokumentovaná oprávnění. Chybí-li seznam modulů úplně, například o prázdninách, integrace endpointy zkusí a zpracuje odpověď serveru. HTTP 403/404 ani přechodná chyba jednoho modulu nezastaví ostatní moduly. Oprávnění u pokročilých jednorázových dotazů a zápisů ověřuje server.

Heslo je uložené ve standardním úložišti konfiguračních záznamů Home Assistantu. Tokeny zůstávají pouze v paměti. Po restartu se klient znovu přihlásí heslem. Obnova tokenů je synchronizovaná, obnovovací token se rotuje a odmítnutý token se zkusí obnovit právě jednou. Neplatné přihlašovací údaje spustí opětovné přihlášení v Home Assistantu. Pro změnu hesla lze také použít **Znovu nakonfigurovat**. Změna identity účtu nebo serveru vyžaduje novou instanci integrace.

Podrobnosti zpráv a známek se standardně do atributů nevkládají. Povolíte-li je, mohou se osobní údaje ukládat do Recorderu a zobrazovat dalším uživatelům Home Assistantu. Seznamy atributů jsou omezeny na 50 položek; úplná data lze získat přes `query`. Názvy entit a zařízení identifikují školní účet i při vypnutých podrobnostech. Diagnostika obsahuje jen stav integrace a chyby endpointů, bez údajů žáků, URL, hesel a tokenů. HTTP přesměrování se automaticky nenásledují; nastavte přímo cílovou adresu školy.

## Režim pouze pro čtení a zápisy do školy

V **Nastavení → Zařízení a služby → Bakaláři → Konfigurovat** lze pro každý účet zapnout **Pouze pro čtení**. Výchozí stav je vypnutý, aby aktualizace zachovala fungování dosavadních automatizací.

Při zapnutí zůstanou dostupné senzory, kalendáře, čtení úkolů, příloh a dokumentované dotazy API včetně čtecích POST seznamů Komens. Zůstává i předvídání průměru, které neukládá známky. Integrace odmítne označení zprávy za přečtenou, změnu dokončení úkolu, odeslání Komens či omluvenky, podpis známek, zápis třídní knihy a vytvoření webové přihlašovací URL. Seznam úkolů v rozhraní nenabízí změnu stavu. Blokace se kontroluje i při přímém zavolání akce.

**Mimo tento režim zápisové akce mění skutečná data na serveru školy.** Přepnutí úkolu v seznamu To-do se propíše do Bakalářů; `send_message` odesílá zprávy, `write_classbook` zapisuje třídní knihu a `confirm_marks` podepisuje známky. `web_login` vrací jednorázový přístup k účtu. Běžná automatická aktualizace žádnou z těchto operací nespouští. Přihlašování a obnova přístupového tokenu probíhají také v režimu pouze pro čtení, protože jsou nutné k načtení dat.

## Akce

Akce jsou zaregistrované po načtení integrace i v době, kdy účet není dostupný nebo byl odpojený. Jejich zavolání pro nenačtený účet vrátí srozumitelnou chybu. Všechny akce vyžadují `entry_id` konkrétního účtu. V editoru akcí je pro něj výběr konfiguračního záznamu. Akce `query`, `predict_marks`, `get_attachment` a `web_login` vyžadují návratovou proměnnou; vrací slovník s klíčem `result`. Akce zápisu se provádějí až při jejich explicitním zavolání. Běžné načítání dat zprávy neoznačuje jako přečtené ani nepodepisuje známky.

| Akce | Účel / další pole |
| --- | --- |
| `bakalari.refresh` | Aktualizovat účet |
| `bakalari.query` | Dokumentovaný dotaz: `endpoint`, případně `id`, `parameters` |
| `bakalari.mark_message_read` | Označit zprávu za přečtenou: `message_id` |
| `bakalari.set_homework_done` | Změnit dokončení úkolu: `homework_id`, `done` |
| `bakalari.confirm_marks` | Podepsat seznam známek: `mark_ids` |
| `bakalari.predict_marks` | Vrátit předpověď serveru pro seznam `marks` |
| `bakalari.send_message` | Odeslat Komens: `message_type`, `title`, `text`, `recipient_type`, `recipients`, případně `options` |
| `bakalari.write_classbook` | Učitelský zápis: `record_id`, `record`; `record.Id` musí odpovídat ID v cestě |
| `bakalari.get_attachment` | Příloha Komens nebo úkolu: `attachment_id`; výsledek obsahuje `content_base64` a `content_type`, limit 5 MiB |
| `bakalari.web_login` | Vrací jednorázovou přihlašovací URL do webu školy; neukládejte ji do entit ani historie |

ID zadávejte v původním tvaru včetně mezer a speciálních znaků; klient je zakóduje. Typy zpráv a aktuální příjemce zjistíte dotazem `message_types`. `send_message` podporuje i omluvenky zadáním příslušného typu zprávy a polí `DateFrom`/`DateTo` v `options`. Přílohy lze předat jako již existující objekty podle API; upload nového souboru dokumentace nepopisuje. Zápisy vyžadují příslušná rodičovská nebo učitelská práva.

```yaml
# Akce ve skriptu nebo automatizaci: načtení známek
- action: bakalari.query
  data:
    entry_id: VASE_ENTRY_ID
    endpoint: marks
  response_variable: klasifikace

# Úkoly pro jiné období
- action: bakalari.query
  data:
    entry_id: VASE_ENTRY_ID
    endpoint: homeworks
    parameters:
      from: '2026-09-01'
      to: '2026-12-31'
  response_variable: ukoly

# Změna žákovského dokončení
- action: bakalari.set_homework_done
  data:
    entry_id: VASE_ENTRY_ID
    homework_id: 'UKOL[123'
    done: true
```

Přehled všech identifikátorů dotazů a hranic pokrytí je v [docs/API_COVERAGE.md](docs/API_COVERAGE.md). Pokročilé dotazy vracejí původní odpovědi API včetně osobních údajů; texty Komens mohou obsahovat HTML.

## Řešení potíží

- **Integrace není v seznamu:** zkontrolujte cestu `/config/custom_components/bakalari/manifest.json`, verzi HA a restartujte server.
- **Nelze se připojit:** ověřte přesnou URL, případnou podsložku, dostupnost ze serveru HA a platnost certifikátu. TLS ověřování je zapnuté. Přesměrování na jiný host nebo přihlašovací portál nemusí být použitelné jako základní URL API.
- **Neplatné přihlášení:** ověřte údaje ve webové či mobilní aplikaci Bakalářů a dokončete opětovné přihlášení v HA.
- **Některá entita chybí:** účet nebo škola nemusí daný modul poskytovat. Podívejte se do stažené diagnostiky na kódy endpointů (403 = zamítnutý přístup, 404 = nedostupná cesta). Modul se při příští aktualizaci zkusí znovu.
- **Chyba 429:** prodlužte interval načítání. Integrace neopakuje zápisy při chybách serveru.
- **Přítomnost není okamžitá:** odpovídá poslednímu načtení přístupového systému v nastaveném intervalu.

Odinstalace: odstraňte všechny instance integrace v Zařízeních a službách, smažte složku komponenty a restartujte HA. Historii v Recorderu spravuje Home Assistant.

## Vývoj a ověření

```sh
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
.venv/bin/python scripts/build_release.py
```

Testy používají skutečné třídy Home Assistantu a simulované HTTP odpovědi nebo klienty; pokrývají autentizaci, souběh, chyby, formuláře, akce, entity a převody kalendáře. Neověřují dostupnost modulů konkrétní školy ani skutečné odeslání Komens či učitelského zápisu. Bez přístupu k živému účtu nelze potvrdit end-to-end kompatibilitu konkrétní instalace školy. CI provádí stejné kontroly na Linuxu proti oběma uvedeným verzím HA. Skript sestavení vytvoří instalovatelný ZIP v `dist/` pouze ze souborů komponenty a návodu.

## Spolupráce a licence

Chyby a návrhy hlaste přes [české formuláře](https://github.com/michalmedvecky/bakalari-ha/issues/new/choose). Postup vývoje a vydávání popisuje [CONTRIBUTING.md](CONTRIBUTING.md), změny jednotlivých verzí [CHANGELOG.md](CHANGELOG.md). Pro bezpečnostní problémy použijte postup v [SECURITY.md](SECURITY.md).

Výsledek instalačního ověření a hranice funkčního testování shrnuje [ověřovací protokol](docs/OVERENI.md).

Zdrojový kód je dostupný pod [licencí MIT](LICENSE). Český přehled podmínek najdete v [dokumentaci licence](docs/LICENCE.md). Projekt je nezávislý na společnosti Bakaláři a nevztahuje se na něj její oficiální podpora.
