"""Vygeneruje překlady a popisy akcí ze společného zdroje textů."""

import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from custom_components.bakalari.endpoints import READS  # noqa: E402

DEST = ROOT / "custom_components/bakalari"
translations = {}
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
                        "read_only": "Pouze pro čtení" if cs else "Read-only mode",
                        "expose_details": "Zveřejnit podrobnosti v atributech entit"
                        if cs
                        else "Expose detailed entity attributes",
                    },
                    "description": "Podrobnosti zahrnují omezená metadata a mohou se ukládat do historie. Názvy, nadpisy a odesílatelé mohou obsahovat osobní údaje viditelné ostatním uživatelům HA. Těla zpráv se nezveřejňují. Změny se použijí po uložení."
                    if cs
                    else "Details include limited metadata and may be stored in history. Names, titles and senders may contain personal information visible to other HA users. Message bodies are never exposed. Changes apply after saving.",
                }
            }
        },
    }
    translations[lang] = content


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
                "Parametry from a to zadávejte jako ISO datum. ID zadávejte bez URL kódování.",
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


# Stejné klíče používají entity i obě jazykové varianty.
entity_names = {
    "sensor": {
        "new_marks": ("Nové známky", "New marks"),
        "homework_count": ("Otevřené úkoly", "Open homeworks"),
        "homeworks_pending": (
            "Nedokončené úkoly v období",
            "Pending homeworks in period",
        ),
        "unread": ("Nepřečtené zprávy", "Unread messages"),
        "noticeboard_unread": ("Nepřečtená nástěnka", "Unread noticeboard messages"),
        "received": ("Přijaté zprávy", "Received messages"),
        "noticeboard": ("Zprávy na nástěnce", "Noticeboard messages"),
        "absence_unexcused": ("Neomluvené hodiny", "Unexcused lessons"),
        "absence_unresolved": ("Nevyřešené absence", "Unresolved absences"),
        "absence_excused": ("Omluvené hodiny", "Excused lessons"),
        "substitutions": ("Změny rozvrhu", "Timetable changes"),
        "subjects": ("Předměty", "Subjects"),
        "final_marks": ("Vysvědčení", "Certificates"),
        "measures": ("Výchovná opatření", "Pedagogical measures"),
        "balance": ("Zůstatek třídního fondu", "Class fund balance"),
        "subject_average": ("{subject} – průměr", "{subject} average"),
    },
    "calendar": {
        "timetable": ("Rozvrh", "Timetable"),
        "events": ("Školní akce", "School events"),
    },
    "binary_sensor": {"student_present": ("Ve škole", "At school")},
    "todo": {"homeworks": ("Domácí úkoly", "Homeworks")},
    "button": {"refresh": ("Aktualizovat", "Refresh")},
}
english_actions = {
    "refresh": ("Refresh", "Refreshes all enabled modules for the account."),
    "query": (
        "Query API",
        "Returns the documented endpoint response to response_variable.",
    ),
    "mark_message_read": (
        "Mark message as read",
        "Marks a message as read on the school server.",
    ),
    "set_homework_done": (
        "Set homework completion",
        "Changes the student's Finished flag on the school server.",
    ),
    "confirm_marks": (
        "Confirm marks",
        "Confirms the selected marks on the school server.",
    ),
    "predict_marks": (
        "Predict average",
        "Returns the school's prediction using existing and hypothetical marks.",
    ),
    "send_message": (
        "Send Komens message",
        "Sends a message to the selected recipients. Query message_types for available types and recipients.",
    ),
    "write_classbook": (
        "Write classbook",
        "Writes a classbook record using teacher permissions. record.Id must match record_id.",
    ),
    "get_attachment": (
        "Get attachment",
        "Returns Base64 content and MIME type for an attachment up to 5 MiB.",
    ),
    "web_login": (
        "Web login",
        "Returns a one-time login URL. Treat this URL as an account credential.",
    ),
}
english_fields = {
    "entry_id": "Bakaláři account",
    "endpoint": "Endpoint",
    "id": "Identifier",
    "parameters": "Query parameters",
    "message_id": "Message ID",
    "homework_id": "Homework ID",
    "done": "Completed",
    "mark_ids": "Mark IDs (list)",
    "marks": "Marks (list of objects)",
    "message_type": "Message type",
    "title": "Title",
    "text": "Text",
    "recipient_type": "Recipient type",
    "recipients": "Recipient IDs (list)",
    "options": "Additional message fields",
    "record_id": "Record ID",
    "record": "Record",
    "attachment_id": "Attachment ID",
}
for lang in ("cs", "en"):
    path = DEST / "translations" / f"{lang}.json"
    content = translations[lang]
    content["entity"] = {
        platform: {key: {"name": names[lang == "en"]} for key, names in entries.items()}
        for platform, entries in entity_names.items()
    }
    content["exceptions"] = {
        "read_only": {
            "message": "Účet je v režimu pouze pro čtení. Zápisy a vytváření webového přihlášení jsou zakázané."
            if lang == "cs"
            else "The account is in read-only mode. Writes and creating web login URLs are disabled."
        }
    }
    content["services"] = {}
    for key, service in services.items():
        content["services"][key] = {
            "name": service["name"] if lang == "cs" else english_actions[key][0],
            "description": service["description"]
            if lang == "cs"
            else english_actions[key][1],
            "fields": {
                field_key: {
                    "name": value["name"] if lang == "cs" else english_fields[field_key]
                }
                for field_key, value in service["fields"].items()
            },
        }
        if "parameters" in service["fields"]:
            content["services"][key]["fields"]["parameters"]["description"] = (
                service["fields"]["parameters"]["description"]
                if lang == "cs"
                else "Use ISO dates for from and to. Supply identifiers without URL encoding."
            )
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n")
    if lang == "en":
        (DEST / "strings.json").write_text(
            json.dumps(content, ensure_ascii=False, indent=2) + "\n"
        )

# services.yaml obsahuje schéma; názvy a popisy se načítají z překladů.
schemas = {
    key: {
        "fields": {
            field_key: {
                k: v for k, v in field.items() if k not in ("name", "description")
            }
            for field_key, field in value["fields"].items()
        }
    }
    for key, value in services.items()
}
(DEST / "services.yaml").write_text(
    yaml.safe_dump(schemas, allow_unicode=True, sort_keys=False)
)
