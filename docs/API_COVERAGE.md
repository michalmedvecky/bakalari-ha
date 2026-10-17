# Pokrytí API

Zdroj: [bakalari-api-v3](https://github.com/bakalari-api/bakalari-api-v3/tree/d4b12ddda3cd7c65c6c1b14723b432a1a2da906f). Cesty jsou relativní k URL školy. `{id}` je jediný zakódovaný segment, nikoli libovolná cesta.

## Dotazy `bakalari.query`

| endpoint | Metoda | Cesta |
| --- | --- | --- |
| `api_versions` | GET | `/api` |
| `api_info` | GET | `/api/3` |
| `user` | GET | `/api/3/user` |
| `marks` | GET | `/api/3/marks` |
| `new_marks` | GET | `/api/3/marks/count-new` |
| `final_marks` | GET | `/api/3/marks/final` |
| `measures` | GET | `/api/3/marks/measures` |
| `homeworks` | GET | `/api/3/homeworks` |
| `homework_count` | GET | `/api/3/homeworks/count-actual` |
| `absence` | GET | `/api/3/absence/student` |
| `received` | POST | `/api/3/komens/messages/received` |
| `sent` | POST | `/api/3/komens/messages/sent` |
| `noticeboard` | POST | `/api/3/komens/messages/noticeboard` |
| `unread` | GET | `/api/3/komens/messages/received/unread` |
| `noticeboard_unread` | GET | `/api/3/komens/messages/noticeboard/unread` |
| `message_types` | GET | `/api/3/komens/message-types` |
| `received_detail` | GET | `/api/3/komens/messages/received/{id}` |
| `sent_detail` | GET | `/api/3/komens/messages/sent/{id}` |
| `timetable` | GET | `/api/3/timetable/actual` |
| `permanent_timetable` | GET | `/api/3/timetable/permanent` |
| `events` | GET | `/api/3/events` |
| `my_events` | GET | `/api/3/events/my` |
| `public_events` | GET | `/api/3/events/public` |
| `substitutions` | GET | `/api/3/substitutions` |
| `subjects` | GET | `/api/3/subjects` |
| `themes` | GET | `/api/3/subjects/themes/{id}` |
| `payments` | GET | `/api/3/payments/classfund` |
| `balance` | GET | `/api/3/payments/classfund/summary` |
| `payment_info` | GET | `/api/3/payments/classfund/paymentsinfo` |
| `student_present` | GET | `/api/3/user/student-at-school` |
| `commissioners` | GET | `/api/3/gdpr/commissioners` |
| `new_consents` | GET | `/api/3/gdpr/consents/person/new` |
| `web_modules` | GET | `/api/3/webmodule` |
| `classbook` | GET | `/api/3/classbook` |
| `lesson_tags` | GET | `/api/3/classbook/lessonTags` |
| `lesson_absence` | GET | `/api/3/lesson/{id}/absence` |
| `lesson_past` | GET | `/api/3/lesson/{id}/past` |
| `lesson_timetable` | GET | `/api/3/lesson/{id}/studentsTimetable` |

Parametry jako `date`, `from`, `to`, `sort` a `search` předávejte v `parameters` podle dokumentace endpointu. `classbook` vyžaduje `from` a `to` včetně času. `received_detail`, `sent_detail`, `themes` a dotazy `lesson_*` vyžadují `id`. POST pro seznam Komens je čtecí požadavek s prázdným formulářovým tělem.

## Zápisy a zvláštní operace

Volitelný režim **Pouze pro čtení** blokuje zápisy a akci `web_login`. Čtecí dotazy včetně POST seznamů a výpočet `predict_marks` ponechává dostupné.

| Akce | Metoda | Cesta |
| --- | --- | --- |
| `mark_message_read` | PUT | `/api/3/komens/message/{id}/mark-as-read` |
| `set_homework_done` | PUT | `/api/3/homeworks/{id}/student-done/{true,false}` |
| `confirm_marks` | POST | `/api/3/marks/SetClassificationConfirmation` |
| `predict_marks` | POST | `/api/3/marks/what-if` |
| `send_message` | POST | `/api/3/komens/message` |
| `write_classbook` | POST | `/api/3/classbook/{id}` |
| `get_attachment` | GET | `/api/3/komens/attachment/{id}` |
| `web_login` | GET | `/api/3/logintoken`; vrací odkaz `/api/3/login/{token}` |

Přihlášení a obnova používají `POST /api/login`, `client_id=ANDR` a dokumentované granty `password` a `refresh_token`. Přihlášení na web má otevřít prohlížeč; klient si nevytváří webovou relaci.

## Hranice pokrytí

Podporované jsou výše uvedené dokumentované JSON operace API v3. Samotné uvedení cesty v seznamu endpointů bez metody, formátu a odpovědi nestačí pro spolehlivou implementaci.

- Neimplementované nedostatečně popsané operace: GDPR souhlasy a námitky/reporty kromě čítače a pověřenců; `marking/atoms`, `marking/marks`; registrace mobilních push notifikací; `komens/rating-templates`; kategorie Komens apology/rating; varianty `message-types/edit` a `/reply`.
- Veřejný HTML rozvrh `/Timetable/Public/...` není JSON API a není použit jako zdroj osobního kalendáře.
- Centrální seznam škol na `sluzby.bakalari.cz` a reklamní kanál `campaign.bakalari.cz` nejsou moduly účtu. Škola se zadává vlastní URL; reklamy integrace nenačítá.
- Není implementován nezdokumentovaný upload nových příloh, mazání zpráv, změny GDPR souhlasů, úpravy jednotlivých známek ani změny docházky. Podpis známek a zápis třídní knihy mají výslovně dokumentované akce.

Učitelské endpointy lze vyvolat přes `query`/`write_classbook`; jejich data se automaticky nepromítají do žákovských senzorů. Oprávnění ověřuje server. Integrace negarantuje funkcionalitu, kterou nepodporuje server školy.
