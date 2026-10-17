"""Počítadla a průměry předmětů vrácené školním serverem."""

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import callback

from .const import CONF_EXPOSE_DETAILS
from .entity import BakalariEntity
from .models import homework_finished

# Klíč, název, ikona a převod hodnoty; podrobné atributy jsou volitelné.
DESCRIPTIONS = (
    ("new_marks", "Nové známky", "mdi:numeric", lambda d: d),
    ("homework_count", "Otevřené úkoly", "mdi:clipboard-text", lambda d: d),
    (
        "homeworks",
        "Nedokončené úkoly v období",
        "mdi:clipboard-check",
        lambda d: sum(
            not homework_finished(h) and not h.get("Closed", False)
            for h in d.get("Homeworks", []) or []
        ),
    ),
    ("unread", "Nepřečtené zprávy", "mdi:email", lambda d: d),
    ("noticeboard_unread", "Nepřečtená nástěnka", "mdi:bulletin-board", lambda d: d),
    (
        "received",
        "Přijaté zprávy",
        "mdi:email-outline",
        lambda d: len(d.get("Messages", []) or []),
    ),
    (
        "noticeboard",
        "Zprávy na nástěnce",
        "mdi:bulletin-board",
        lambda d: len(d.get("Messages", []) or []),
    ),
    (
        "absence",
        "Neomluvené hodiny",
        "mdi:account-alert",
        lambda d: sum(x.get("Missed", 0) or 0 for x in d.get("Absences", []) or []),
    ),
    (
        "absence",
        "Nevyřešené absence",
        "mdi:account-question",
        lambda d: sum(x.get("Unsolved", 0) or 0 for x in d.get("Absences", []) or []),
    ),
    (
        "absence",
        "Omluvené hodiny",
        "mdi:account-clock",
        lambda d: sum(x.get("Ok", 0) or 0 for x in d.get("Absences", []) or []),
    ),
    (
        "substitutions",
        "Změny rozvrhu",
        "mdi:calendar-edit",
        lambda d: len(d.get("Changes", []) or []),
    ),
    (
        "subjects",
        "Předměty",
        "mdi:bookshelf",
        lambda d: len(d.get("Subjects", []) or []),
    ),
    (
        "final_marks",
        "Vysvědčení",
        "mdi:certificate",
        lambda d: len(d.get("CertificateTerms", []) or []),
    ),
    (
        "measures",
        "Výchovná opatření",
        "mdi:school",
        lambda d: len(d.get("PedagogicalMeasures", []) or []),
    ),
    ("balance", "Zůstatek třídního fondu", "mdi:cash", lambda d: d.get("Balance")),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = entry.runtime_data
    added = set()

    @callback
    def discover():
        entities = []
        for index, (key, name, icon, extract) in enumerate(DESCRIPTIONS):
            identity = f"{key}_{index}"
            if key in coordinator.data and identity not in added:
                added.add(identity)
                entities.append(
                    BakalariSensor(coordinator, key, name, icon, extract, index)
                )
        for subject in coordinator.data.get("marks", {}).get("Subjects", []) or []:
            subject_id = str((subject.get("Subject") or {}).get("Id", ""))
            if subject_id and f"subject_{subject_id}" not in added:
                added.add(f"subject_{subject_id}")
                entities.append(
                    SubjectSensor(
                        coordinator,
                        subject_id,
                        subject["Subject"].get("Name") or subject_id,
                    )
                )
        if entities:
            async_add_entities(entities)

    discover()
    entry.async_on_unload(coordinator.async_add_listener(discover))


class BakalariSensor(BakalariEntity, SensorEntity):
    def __init__(self, coordinator, key, name, icon, extract, index):
        super().__init__(coordinator, key, name, icon)
        self._attr_unique_id += f"_{index}"
        self.extract = extract

    @property
    def native_value(self):
        if self.key not in self.coordinator.data:
            return None
        return self.extract(self.coordinator.data[self.key])

    @property
    def extra_state_attributes(self):
        if self.coordinator.entry.options.get(CONF_EXPOSE_DETAILS, False):
            value = self.coordinator.data.get(self.key)
            if isinstance(value, dict):
                # Omezí velikost seznamů ukládaných do historie.
                return {
                    "data": {
                        k: v[:50] if isinstance(v, list) else v
                        for k, v in value.items()
                    }
                }
        return None


class SubjectSensor(BakalariEntity, SensorEntity):
    def __init__(self, coordinator, subject_id, name):
        super().__init__(coordinator, "marks", f"{name} – průměr", "mdi:counter")
        self.subject_id = subject_id
        self._attr_unique_id += f"_{subject_id}"

    def subject(self):
        return next(
            (
                s
                for s in self.coordinator.data.get("marks", {}).get("Subjects", [])
                or []
                if str((s.get("Subject") or {}).get("Id")) == self.subject_id
            ),
            None,
        )

    @property
    def available(self):
        return super().available and self.subject() is not None

    @property
    def native_value(self):
        # Zachová slovní, procentuální i bodové hodnocení v původním tvaru.
        return str((self.subject() or {}).get("AverageText", "")).strip() or None

    @property
    def extra_state_attributes(self):
        subject = self.subject() or {}
        attributes = {
            "subject_id": self.subject_id,
            "mark_count": len(subject.get("Marks", []) or []),
            "temporary_mark": subject.get("TemporaryMark"),
            "points_only": subject.get("PointsOnly"),
        }
        if self.coordinator.entry.options.get(CONF_EXPOSE_DETAILS, False):
            attributes["marks"] = (subject.get("Marks") or [])[-50:]
        return attributes
