# Ověření integrace

## Instalační report uživatele — 17. října 2026

Uživatel otestoval verzi `v1.0.0` na **Home Assistant Green, HA Core 2026.10.1, Python 3.14.6**, instalovanou přes vlastní repozitář HACS.

Potvrzené kroky:

- Stažení přes HACS, kontrola konfigurace a restart HA proběhly v pořádku.
- Po restartu nebyla v logu chyba ani traceback integrace; objevilo se jen standardní upozornění na vlastní komponentu neotestovanou projektem Home Assistant.
- Konfigurační formulář zobrazil URL, uživatelské jméno a heslo.

Formulář byl zrušen bez vytvoření účtu. Tento report tedy nepotvrzuje přihlášení ke škole, načtení modulů ani zápisy do Bakalářů.

## Reakce ve verzi 1.0.1

Opravné vydání upravuje registraci akcí, lokalizaci, verzi diagnostiky a nepoužívaný kód. Přidává režim pouze pro čtení a výslovný popis zápisových operací. Názvy zařízení nadále vycházejí z načteného profilu; model zařízení obsahuje název školy.

Syntaxe výjimek nově používá závorky. Minimum `2026.3` zůstává platné: [HA 2026.3 již přešlo na Python 3.14](https://www.home-assistant.io/blog/2026/03/04/release-20263/#running-on-python-314-).

## Automatické testy

Testovací matice na GitHubu zahrnuje **HA 2026.3.4 a 2026.10.1 s Pythonem 3.14**. Používá skutečné třídy HA a místní HTTP server se smyšlenými daty. Kontroluje také načtení českých a anglických překladů pomocí loaderu HA, trvalou dostupnost akcí při odpojení účtu, blokaci zápisů a soulad verze vydání.

Výsledky konkrétních běhů jsou dostupné v [GitHub Actions](https://github.com/michalmedvecky/bakalari-ha/actions/workflows/test.yml). Testy nekomunikují se skutečnou školou. Rozsah uživatelského ověření přihlášeného účtu popisuje následující doplnění; úplné ověření všech modulů a zápisových akcí k dispozici není.

## Doplnění z reálného účtu — 17. října 2026

Uživatel následně přidal skutečný účet a ohlásil zobrazení známek, zpráv Komens a rozvrhu. Report identifikoval chybějící výhled kalendáře na příští týden, šablonový název školy, textové průměry a nejasné vynechání modulů. Při zapnutých podrobnostech zaznamenal příliš velké atributy zpráv a citlivé přihlašovací údaje v těle jedné školní zprávy. Zároveň doložil rozdíl mezi serverovým čítačem nových známek a příznaky `IsNew`.

Verze 1.0.2 proto omezuje zveřejňované atributy, vynechává těla zpráv, převádí jednoznačné průměry na číselné stavy, načítá následující týden a doplňuje diagnostiku vynechání. Regresní testy používají pouze smyšlená data včetně zástupných citlivých textů; skutečné zprávy ani přihlašovací údaje uživatelova účtu nebyly do repozitáře vloženy.

Tento report potvrzuje částečný provoz přihlášené integrace na konkrétní škole. Nepotvrzuje funkčnost všech modulů, oprávnění jiných účtů ani provedení všech zápisových akcí. Opravenou verzi vůči skutečné škole ověří až následná aktualizace uživatelovy instalace.


## Ověření verze 1.1.0 — 19. října 2026

Uživatel nasadil verzi přes HACS na HA Core 2026.10.1 po vytvoření zálohy. Účet se načetl, diagnostika uvedla verzi 1.1.0 bez chyb endpointů a log neobsahoval záznamy integrace. Akce omluvenky byla zapojena do skriptu pro zpoždění vlaku, který z kalendáře vyhledává první hodinu dne. Příjemce byl zkontrolován pouze čtecím dotazem `message_types`; skutečná omluvenka škole odeslána nebyla.

Report vedl k doplnění náhledu, volitelných časů, předmětu a údajů o příjemci v odpovědi. Také potvrdil potřebu řadit Komens před zkrácením a ořezávat mezery v zobrazovaných atributech předmětů. Nabídka publikačních typů zpráv žákovskému účtu není důkazem práva publikovat; akce `send_message` je proto omezena na `OBECNA` a `OMLUVENKA`.

Zpracování časů omluvenky školou, uznání absence ani vrácení ID skutečně odeslané zprávy tento report nepotvrzuje. Dokumentace odesílání API uvádí odpověď `{"Message": ""}` bez ID; integrace v takovém případě vrací `message_id: null`.
