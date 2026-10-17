from datetime import datetime
from zoneinfo import ZoneInfo

from custom_components.bakalari.models import (
    homework_finished,
    in_range,
    parse_datetime,
    school_events,
    timetable_events,
)

TZ = ZoneInfo("Europe/Prague")


def timetable(day="2026-10-19T00:00:00+02:00", change=None):
    return {
        "Hours": [{"Id": 3, "BeginTime": "8:00", "EndTime": "8:45"}],
        "Subjects": [{"Id": " 6", "Name": "Matematika"}],
        "Teachers": [{"Id": "U 1", "Name": "Teacher"}],
        "Rooms": [{"Id": "A", "Abbrev": "101"}],
        "Days": [
            {
                "Date": day,
                "Atoms": [
                    {
                        "HourId": 3,
                        "SubjectId": " 6",
                        "TeacherId": "U 1",
                        "RoomId": "A",
                        "Change": change,
                    }
                ],
            }
        ],
    }


def test_timetable_opaque_ids_and_timezone():
    result = timetable_events(timetable())
    assert len(result) == 1
    assert result[0]["summary"] == "Matematika"
    assert result[0]["location"] == "101"
    assert result[0]["start"].isoformat() == "2026-10-19T08:00:00+02:00"
    winter = timetable_events(timetable("2026-10-26T00:00:00+01:00"))
    assert winter[0]["start"].isoformat().endswith("+01:00")


def test_removed_and_canceled_lessons():
    for kind in ("Removed", "Canceled"):
        assert timetable_events(timetable(change={"ChangeType": kind})) == []
    assert timetable_events(timetable(change={"ChangeType": "Substitution"}))


def test_holiday_and_invalid_dates():
    assert timetable_events({"Hours": [], "Days": []}) == []
    assert timetable_events(timetable("2020-02-30")) == []
    assert parse_datetime("0001-01-01T00:00:00+01:00") is None


def test_all_day_end_is_exclusive():
    result = school_events(
        {
            "Events": [
                {
                    "Id": "1",
                    "Title": "Volno",
                    "Times": [
                        {
                            "WholeDay": True,
                            "StartTime": "2026-10-28T00:00:00+01:00",
                            "EndTime": "2026-10-28T23:59:00+01:00",
                        }
                    ],
                }
            ]
        }
    )
    assert result[0]["start"].isoformat() == "2026-10-28"
    assert result[0]["end"].isoformat() == "2026-10-29"
    assert (
        in_range(
            result, datetime(2026, 10, 28, tzinfo=TZ), datetime(2026, 10, 29, tzinfo=TZ)
        )
        == result
    )
    assert (
        in_range(
            result, datetime(2026, 10, 29, tzinfo=TZ), datetime(2026, 10, 30, tzinfo=TZ)
        )
        == []
    )


def test_range_deduplicates_week_results():
    events = timetable_events(timetable())
    assert (
        len(
            in_range(
                events * 2,
                datetime(2026, 10, 19, tzinfo=TZ),
                datetime(2026, 10, 20, tzinfo=TZ),
            )
        )
        == 1
    )


def test_student_finished_is_not_teacher_done():
    assert homework_finished({"Done": True, "Closed": True}) is False
    assert homework_finished({"Finished": True, "Done": False}) is True
