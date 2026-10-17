# Bezpečnost a ochrana údajů

Integrace pracuje s přihlašovacími údaji a potenciálně citlivými školními daty. Bezpečnostní problém neposílejte do veřejného hlášení s konkrétním účtem, tokenem nebo odpovědí školního serveru.

## Nahlášení problému

Pokud repozitář nabízí tlačítko **Report a vulnerability** na kartě **Security**, použijte soukromé hlášení. Dostupnost tohoto kanálu závisí na nastavení GitHubu; projekt ji automaticky nepředpokládá.

Jestliže soukromé hlášení není dostupné, použijte soukromý kontakt zveřejněný správcem na [jeho profilu](https://github.com/michalmedvecky). Pokud tam vhodný kontakt není, založte pouze obecné hlášení s žádostí o bezpečný kontakt, bez postupu zneužití a citlivých příloh. Správce následně domluví soukromé předání podrobností.

Užitečné jsou verze integrace a HA, popis dopadu a minimální ukázka se smyšlenými daty. Projekt nemá smluvní dobu reakce ani placenou podporu.

## Podporované verze

Bezpečnostní opravy se připravují pro nejnovější vydanou verzi. Před hlášením ověřte, zda problém přetrvává po aktualizaci. Starší verze nemusí opravy obdržet samostatně.

## Práce s údaji

- Heslo ukládá standardní úložiště konfiguračních záznamů Home Assistantu. Tokeny klient drží v paměti.
- Od verze 1.0.2 se těla Komens zpráv do atributů vůbec nezveřejňují. Volitelné přehledy mají limit 8 KiB, ale nadpisy a jména mohou stále obsahovat osobní údaje dostupné ostatním uživatelům HA a historii.
- Jednorázová URL z akce `web_login` poskytuje přístup k účtu. Zacházejte s ní jako s přihlašovacím údajem.
- Diagnostiku před sdílením vždy zkontrolujte. Úplné odpovědi z `query` mohou obsahovat osobní údaje.
- TLS ověřování je zapnuté a přesměrování se automaticky nenásledují. Používejte cílovou HTTPS adresu školy.

Pokud omylem zveřejníte platné heslo nebo token, odstraňte zveřejněný obsah a změňte přihlašovací údaje přímo u školy. Samotné smazání Git commitu nemusí odstranit všechny dostupné kopie.

## Změna zveřejňování atributů ve verzi 1.0.2

Uživatel upozornil, že školní zpráva může obsahovat platné přihlašovací údaje. Starší verze při zapnutém `expose_details` vkládaly celé tělo zprávy do stavových atributů. Verze 1.0.2 tento postup ruší a používá pouze povolená metadata. Příznak `_unrecorded_attributes` by sám nestačil, protože by nezabránil čtení těla z aktuálního stavu entity.

Aktualizace sama nemaže dřívější historii, zálohy ani dříve získané odpovědi API. Pokud v nich bylo platné heslo, změňte ho nebo požádejte jeho správce o změnu. Úplná odpověď z výslovné akce `query` může nadále obsahovat text a citlivé údaje; nesdílejte ji veřejně.
