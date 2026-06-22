"""Binary sensors pro Atrea — výměna filtru + alarmy (device_class=problem).

Z RD5 specs (tab.9 Alarmy a upozornění):
- D11122 = Zanesený filtr (TR mode — tlakové čidlo přes filtr).
- D11183 = Interval výměny filtru (Perioda mode — uplynul nastavený interval H10910).
- D11114 = Nevyrovnaný průtok (alarm) — jednotka se kvůli němu vypíná. Reset přes
  tlačítko C10005 (registr z odposlechu web UI; viz button.py).

Atrea filtr může běžet buď v TR módu (= D11122 reaguje na fyzické zanesení) nebo
Perioda módu (= D11183 reaguje na uplynulý interval, default 90 dní). Nastavení
je v registru H10512. Vystavujeme oba flagy — user uvidí ten relevantní podle
toho, který mód jeho jednotka má aktivní (a druhý zůstane vždy off).
"""

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN, LOGGER


PROBLEM_BINARY_SENSORS = [
    {
        "register": "D11122",
        "key": "filter_dirty",
        "name": "Filtr zanesený",
        "translation_key": "filter_dirty",
    },
    {
        "register": "D11183",
        "key": "filter_period_expired",
        "name": "Filtr — interval výměny",
        "translation_key": "filter_period_expired",
    },
    {
        "register": "D11114",
        "key": "unbalanced_flow",
        "name": "Nevyrovnaný průtok",
        "translation_key": "unbalanced_flow",
    },
]


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [
        AtreaProblemBinarySensor(data, entry, spec) for spec in PROBLEM_BINARY_SENSORS
    ]
    async_add_entities(entities)


class AtreaProblemBinarySensor(CoordinatorEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_has_entity_name = True

    def __init__(self, data, entry, spec):
        super().__init__(data["coordinator"])
        self._data = data
        self._atrea = data["atrea"]
        self._register = spec["register"]
        self._entry_id = entry.entry_id
        self._ip = entry.data.get("ip_address")
        self._attr_name = spec["name"]
        self._attr_translation_key = spec["translation_key"]
        self._attr_unique_id = slugify(f"atrea_{self._ip}_{spec['key']}")

    @property
    def is_on(self):
        status = self._data.get("status")
        if not status or self._register not in status:
            return None
        try:
            return int(status[self._register]) == 1
        except (TypeError, ValueError):
            LOGGER.debug(
                "Atrea binary_sensor %s: unexpected value %r",
                self._register,
                status.get(self._register),
            )
            return None

    @property
    def available(self):
        status = self._data.get("status")
        return bool(status) and self._register in status

    @property
    def device_info(self):
        # Share device with the climate entity so all Atrea entities cluster
        # under one device card in HA UI.
        return {"identifiers": {(DOMAIN, slugify(f"atrea_{self._ip}"))}}
