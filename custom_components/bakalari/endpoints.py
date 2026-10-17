"""Katalog dokumentovaných čtecích operací včetně POST seznamů."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoint:
    method: str
    path: str
    module: str | None = None
    right: str | None = None
    shape: str = "dict"


READS = {
    "api_versions": Endpoint("GET", "/api", shape="list"),
    "api_info": Endpoint("GET", "/api/3"),
    "user": Endpoint("GET", "/api/3/user"),
    "marks": Endpoint("GET", "/api/3/marks", "Marks", "ShowMarks"),
    "new_marks": Endpoint("GET", "/api/3/marks/count-new", "Marks", "ShowMarks", "int"),
    "final_marks": Endpoint("GET", "/api/3/marks/final", "Marks", "ShowFinalMarks"),
    "measures": Endpoint("GET", "/api/3/marks/measures", "Marks"),
    "homeworks": Endpoint("GET", "/api/3/homeworks", "Homeworks", "ShowHomeworks"),
    "homework_count": Endpoint(
        "GET", "/api/3/homeworks/count-actual", "Homeworks", "ShowHomeworks", "int"
    ),
    "absence": Endpoint("GET", "/api/3/absence/student", "Absence", "ShowAbsence"),
    "received": Endpoint(
        "POST", "/api/3/komens/messages/received", "Komens", "ShowReceivedMessages"
    ),
    "sent": Endpoint(
        "POST", "/api/3/komens/messages/sent", "Komens", "ShowSentMessages"
    ),
    "noticeboard": Endpoint(
        "POST",
        "/api/3/komens/messages/noticeboard",
        "Komens",
        "ShowNoticeBoardMessages",
    ),
    "unread": Endpoint(
        "GET",
        "/api/3/komens/messages/received/unread",
        "Komens",
        "ShowReceivedMessages",
        "int",
    ),
    "noticeboard_unread": Endpoint(
        "GET",
        "/api/3/komens/messages/noticeboard/unread",
        "Komens",
        "ShowNoticeBoardMessages",
        "int",
    ),
    "message_types": Endpoint(
        "GET", "/api/3/komens/message-types", "Komens", "SendMessages"
    ),
    "received_detail": Endpoint(
        "GET", "/api/3/komens/messages/received/{id}", "Komens", "ShowReceivedMessages"
    ),
    "sent_detail": Endpoint(
        "GET", "/api/3/komens/messages/sent/{id}", "Komens", "ShowSentMessages"
    ),
    "timetable": Endpoint(
        "GET", "/api/3/timetable/actual", "Timetable", "ShowTimetable"
    ),
    "permanent_timetable": Endpoint(
        "GET", "/api/3/timetable/permanent", "Timetable", "ShowTimetable"
    ),
    "events": Endpoint("GET", "/api/3/events", "Events", "ShowEvents"),
    "my_events": Endpoint("GET", "/api/3/events/my", "Events", "ShowEvents"),
    "public_events": Endpoint("GET", "/api/3/events/public", "Events", "ShowEvents"),
    "substitutions": Endpoint(
        "GET", "/api/3/substitutions", "Substitutions", "ShowSubstitutions"
    ),
    "subjects": Endpoint("GET", "/api/3/subjects", "Subjects", "ShowSubjects"),
    "themes": Endpoint(
        "GET", "/api/3/subjects/themes/{id}", "Subjects", "ShowSubjectThemes"
    ),
    "payments": Endpoint("GET", "/api/3/payments/classfund", "Payments"),
    "balance": Endpoint("GET", "/api/3/payments/classfund/summary", "Payments"),
    "payment_info": Endpoint(
        "GET", "/api/3/payments/classfund/paymentsinfo", "Payments"
    ),
    "student_present": Endpoint(
        "GET",
        "/api/3/user/student-at-school",
        "AccessSystem",
        "CanShowStudentPresentAtSchool",
        "bool",
    ),
    "commissioners": Endpoint(
        "GET", "/api/3/gdpr/commissioners", "Gdpr", "ShowCommissioners"
    ),
    "new_consents": Endpoint(
        "GET", "/api/3/gdpr/consents/person/new", "Gdpr", shape="int"
    ),
    "web_modules": Endpoint("GET", "/api/3/webmodule"),
    "classbook": Endpoint("GET", "/api/3/classbook", "ClassBook"),
    "lesson_tags": Endpoint(
        "GET", "/api/3/classbook/lessonTags", "ClassBook", shape="list"
    ),
    "lesson_absence": Endpoint("GET", "/api/3/lesson/{id}/absence", "ClassBook"),
    "lesson_past": Endpoint("GET", "/api/3/lesson/{id}/past", "ClassBook"),
    "lesson_timetable": Endpoint(
        "GET", "/api/3/lesson/{id}/studentsTimetable", "ClassBook"
    ),
}


def validate_result(key, result):
    """Chybějící či chybnou odpověď nepřevádí na platný prázdný stav."""
    expected = {"dict": dict, "list": list, "int": int, "bool": bool}[READS[key].shape]
    if type(result) is not expected:
        from .api import BakalariError

        raise BakalariError("Neočekávaná struktura odpovědi API")
    collections = {
        "marks": "Subjects",
        "final_marks": "CertificateTerms",
        "measures": "PedagogicalMeasures",
        "homeworks": "Homeworks",
        "absence": "Absences",
        "received": "Messages",
        "sent": "Messages",
        "noticeboard": "Messages",
        "timetable": "Days",
        "permanent_timetable": "Days",
        "events": "Events",
        "my_events": "Events",
        "public_events": "Events",
        "substitutions": "Changes",
        "subjects": "Subjects",
        "payments": "MonthlyData",
        "commissioners": "Commissioners",
        "classbook": "Days",
        "themes": "Themes",
    }
    if field := collections.get(key):
        if (
            field not in result
            or not isinstance(result[field], list)
            or not all(isinstance(item, dict) for item in result[field])
        ):
            from .api import BakalariError

            raise BakalariError("Neočekávaná struktura seznamu v odpovědi API")
    return result
