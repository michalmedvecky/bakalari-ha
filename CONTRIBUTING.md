# Jak přispívat

Děkujeme za pomoc s integrací Bakalářů pro Home Assistant. Hlášení chyb, návrhy, dokumentaci a popisy změn pište česky. Názvy rozhraní Home Assistantu, polí API, Python identifikátorů a standardních souborů zachovávejte podle technických konvencí. Anglický jazykový soubor zůstává součástí lokalizačního mechanismu Home Assistantu.

## Než začnete

Projděte [návod](README.md), [pokrytí API](docs/API_COVERAGE.md) a existující [hlášení](https://github.com/michalmedvecky/bakalari-ha/issues). U větší změny nejprve založte návrh, aby bylo možné dohodnout požadované chování. Pro drobnou opravu můžete rovnou otevřít pull request.

## Vývojové prostředí

Požadován je Python 3.14 a Git. Home Assistant a ostatní vývojové závislosti se instalují pouze do virtuálního prostředí.

```sh
git clone git@github.com:michalmedvecky/bakalari-ha.git
cd bakalari-ha
python3.14 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
git switch -c oprava/strucny-popis
```

Na Windows používejte odpovídající příkazy v `.venv\Scripts\`.

## Zásady implementace

- Zachovávejte asynchronní komunikaci a sdílenou HTTP relaci Home Assistantu.
- Nový endpoint opřete o doloženou metodu, cestu, parametry a odpověď. Nezdokumentované chování označte jako neověřené.
- Upravte katalog v `endpoints.py` a [přehled API](docs/API_COVERAGE.md), pokud změna ovlivňuje pokrytí.
- Nevkládejte přihlašovací údaje, školní URL ani osobní záznamy do logů, testů a příloh. Používejte smyšlené údaje a doménu `school.example`.
- Souběžné obnovy tokenů musí zůstat synchronizované. Výpadek volitelného modulu nesmí vyřadit ostatní moduly.
- Zápisy do Bakalářů mají být vyvolané konkrétní akcí uživatele nebo automatizace. Běžné načítání nesmí měnit stav zpráv, známek a úkolů.
- U opravy chování přidejte test, který odhalí původní problém. Není nutné přidávat testy pouze pro textové změny.

Komentáře a dokumentaci v kódu pište česky; názvy API a programové identifikátory nepřekládejte. Uživatelské překlady a popisy akcí generuje `scripts/generate_metadata.py`. Při jejich změně upravte zdroj skriptu a spusťte ho ve vývojovém prostředí.

## Kontroly před pull requestem

```sh
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/pytest -q
.venv/bin/python scripts/build_release.py
git diff --check
```

Testy používají skutečné třídy HA a simulovaná data. Pokud jste změnu ověřili proti vlastní škole, stačí uvést verzi API a typ účtu; nepřikládejte citlivá data ani název školy. Změny posílejte do větve `main` a stručně popište problém, řešení a ověření.

## Vydání nové verze

1. Upravte verzi v `custom_components/bakalari/manifest.json` a doplňte stejné číslo do `CHANGELOG.md`.
2. Počkejte na úspěšné kontroly větve `main`.
3. Vytvořte anotovanou značku, například `git tag -a v1.0.1 -m 'Vydání verze 1.0.1'`, a nahrajte ji příkazem `git push origin v1.0.1`.
4. Workflow **Vydání verze** znovu spustí kontroly, ověří shodu značky s manifestem a zveřejní české poznámky spolu s instalačním ZIPem a SHA-256 kontrolním součtem.

Závislosti oficiálních GitHub Actions jsou připnuté na konkrétní revize. Jejich aktualizace navrhuje Dependabot; stejně jako ostatní změny podléhají kontrole.
