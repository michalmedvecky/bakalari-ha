"""Konstanty integrace Bakalářů."""

from homeassistant.const import Platform

DOMAIN = "bakalari"
PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.CALENDAR,
    Platform.TODO,
    Platform.BUTTON,
]
CONF_MODULES = "modules"
CONF_EXPOSE_DETAILS = "expose_details"
CONF_READ_ONLY = "read_only"
DEFAULT_INTERVAL = 900
MODULES = [
    "Marks",
    "Homeworks",
    "Absence",
    "Komens",
    "Timetable",
    "Events",
    "Substitutions",
    "Subjects",
    "Payments",
    "AccessSystem",
]
