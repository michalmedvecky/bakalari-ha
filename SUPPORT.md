# Podpora

Začněte v [návodu](README.md) a části Řešení potíží. Podporované funkce a záměrná omezení popisuje [pokrytí API](docs/API_COVERAGE.md).

## Hlášení chyby

Použijte [český formulář hlášení](https://github.com/michalmedvecky/bakalari-ha/issues/new?template=chyba.yml). Uveďte verzi integrace, verzi Home Assistantu, typ účtu a kroky k zopakování. Před přiložením diagnostiky nebo logu ověřte, že neobsahují osobní údaje a přihlašovací údaje. URL školy není pro veřejné hlášení potřeba.

U nefunkčního modulu pomůže HTTP kód: 403 obvykle znamená zamítnuté oprávnění, 404 nedostupný endpoint a 429 omezení počtu požadavků. Konkrétní dostupnost funkcí určuje školní server a jeho licence.

## Nová funkce

Vytvořte [návrh vylepšení](https://github.com/michalmedvecky/bakalari-ha/issues/new?template=navrh.yml), popište situaci a požadované chování. Máte-li dokumentaci příslušné operace API, přiložte veřejný odkaz.

## Bezpečnost

Pro únik přihlašovacích údajů a zranitelnosti platí postup v [SECURITY.md](SECURITY.md). Neposílejte je do veřejných hlášení.

Jde o komunitní projekt bez garantované doby odpovědi. Přístup ke skutečnému školnímu účtu není součástí automatických testů.
