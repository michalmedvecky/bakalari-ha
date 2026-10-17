"""Vygeneruje překlady a popisy akcí ze společného zdroje textů."""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from custom_components.bakalari.endpoints import READS  # noqa: E402

DEST = ROOT / "custom_components/bakalari"
for lang in ("cs", "en"):
    cs = lang == "cs"
    labels = {
        "url": "Adresa školy" if cs else "School URL",
        "username": "Uživatelské jméno" if cs else "Username",
        "password": "Heslo" if cs else "Password",
    }
    step = {
        "title": "Připojení Bakalářů" if cs else "Connect Bakaláři",
        "description": "Zadejte adresu webu Bakalářů vaší školy a přihlašovací údaje. Pro další účet přidejte další integraci."
        if cs
        else "Enter your school's Bakaláři URL and credentials. Add a separate integration entry for another account.",
        "data": labels,
    }
    content = {
        "title": "Bakaláři",
        "config": {
            "step": {key: step for key in ("user", "reauth_confirm", "reconfigure")},
            "error": {
                "invalid_url": "Zadejte platnou adresu HTTP(S) bez parametrů."
                if cs
                else "Enter a valid HTTP(S) school URL without query parameters.",
                "invalid_auth": "Nesprávné jméno nebo heslo."
                if cs
                else "Invalid username or password.",
                "cannot_connect": "Školní server je nedostupný nebo vrátil neplatná data."
                if cs
                else "Cannot connect or the server returned invalid data.",
            },
            "abort": {
                "already_configured": "Tento účet už je nastavený."
                if cs
                else "This account is already configured.",
                "wrong_account": "Údaje patří jinému účtu nebo serveru. Přidejte ho jako novou integraci."
                if cs
                else "These credentials belong to another account or server. Add a separate integration.",
                "reauth_successful": "Přihlašovací údaje byly aktualizovány."
                if cs
                else "Credentials updated.",
                "reconfigure_successful": "Nastavení bylo aktualizováno."
                if cs
                else "Configuration updated.",
            },
        },
        "options": {
            "step": {
                "init": {
                    "title": "Nastavení aktualizací" if cs else "Polling options",
                    "data": {
                        "scan_interval": "Interval aktualizace (sekundy)"
                        if cs
                        else "Update interval (seconds)",
                        "modules": "Načítané moduly" if cs else "Polled modules",
                        "expose_details": "Zveřejnit podrobnosti v atributech entit"
                        if cs
                        else "Expose detailed entity attributes",
                    },
                    "description": "Podrobnosti mohou obsahovat osobní údaje a ukládat se do historie. Změny se použijí po uložení."
                    if cs
                    else "Details may contain personal information and be stored in history. Changes apply after saving.",
                }
            }
        },
    }
    (DEST / "translations" / f"{lang}.json").write_text(
        json.dumps(content, ensure_ascii=False, indent=2) + "\n"
    )
    if lang == "en":
        (DEST / "strings.json").write_text(
            json.dumps(content, ensure_ascii=False, indent=2) + "\n"
        )


def field(name, selector, required=True, description=None):
    result = {"name": name, "required": required, "selector": selector}
    if description:
        result["description"] = description
    return result


text = {"text": {}}
obj = {"object": {}}
entry = field("Účet Bakalářů", {"config_entry": {"integration": "bakalari"}})
actions = {
    "refresh": ("Aktualizovat", "Načte znovu všechny povolené moduly.", {}),
    "query": (
        "Načíst data API",
        "Vrací neupravená data dokumentovaného endpointu do response_variable.",
        {
            "endpoint": field("Endpoint", {"select": {"options": list(READS)}}),
            "id": field("Identifikátor", text, False),
            "parameters": field(
                "Parametry dotazu",
                obj,
                False,
                "Například {from: '2026-10-01', to: '2026-10-31'}. ID zadávejte bez URL kódování.",
            ),
        },
    ),
    "mark_message_read": (
        "Označit zprávu jako přečtenou",
        "Změní stav zprávy v Bakalářích.",
        {"message_id": field("ID zprávy", text)},
    ),
    "set_homework_done": (
        "Dokončení úkolu",
        "Nastaví žákovský příznak Finished.",
        {
            "homework_id": field("ID úkolu", text),
            "done": field("Hotovo", {"boolean": {}}),
        },
    ),
    "confirm_marks": (
        "Podepsat známky",
        "Odešle podpis vybraných známek.",
        {"mark_ids": field("ID známek (seznam)", obj)},
    ),
    "predict_marks": (
        "Předvídat průměr",
        "Vrací předpověď školy; seznam obsahuje existující i hypotetické známky.",
        {"marks": field("Známky (seznam objektů)", obj)},
    ),
    "send_message": (
        "Odeslat Komens",
        "Odešle zprávu zvoleným příjemcům. Typy a příjemce zjistíte dotazem message_types.",
        {
            "message_type": field("Typ zprávy", text),
            "title": field("Nadpis", text),
            "text": field("Text", {"text": {"multiline": True}}),
            "recipient_type": field("Typ příjemce", text),
            "recipients": field("ID příjemců (seznam)", obj),
            "options": field("Další pole zprávy", obj, False),
        },
    ),
    "write_classbook": (
        "Zapsat třídní knihu",
        "Pro učitele: zapíše záznam podle oprávnění účtu. record.Id musí odpovídat record_id.",
        {"record_id": field("ID záznamu", text), "record": field("Záznam", obj)},
    ),
    "get_attachment": (
        "Načíst přílohu",
        "Vrací Base64 a MIME typ přílohy (nejvýše 5 MiB).",
        {"attachment_id": field("ID přílohy", text)},
    ),
    "web_login": (
        "Přihlášení na web",
        "Vrací jednorázovou přihlašovací URL. Uchovávejte ji jako přihlašovací údaj.",
        {},
    ),
}
services = {
    key: {
        "name": name,
        "description": description,
        "fields": {"entry_id": entry, **fields},
    }
    for key, (name, description, fields) in actions.items()
}
(DEST / "services.yaml").write_text(
    yaml.safe_dump(services, allow_unicode=True, sort_keys=False)
)
