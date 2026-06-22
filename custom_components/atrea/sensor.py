"""Senzory pro Atrea — analogové výstupy 0–10 V.

Z RD5 specs (tab.7 stavové registry, holding registry 2.x Výstupy):
- H10207 = Výstup DA1, analogový 0–10 V (U = DATA/1000). Nese řídicí napětí
  modulace tepelného čerpadla (jednotka řídí TČ signálem 0–10 V — viz H12100
  „TČ-ovládání 0-10V"). 10,0 V = TČ jede na max, méně = má rezervu.

Směr (topí/chladí) NEvystavujeme zvlášť — climate entity ho už ukazuje přes
hvac_action (mapuje C10215 SE → HEATING, C10216 SC → COOLING).

Průtoky vzduchu (tab. 4.1 input registry, hodnota = m³/h přímo, 1:1):
- I11600/I11602 = požadovaný/aktuální průtok SUP (přívod)
- I11601/I11603 = požadovaný/aktuální průtok ETA (odtah)
- I11604/I11605 = požadovaný/aktuální průtok ODA (venkovní) — pouze pro R_5

Teploty (tab.7 input registry, hodnota = °C × 10, tj. /10):
- I10211 = T-ODA, venkovní vzduch. Vodičové čidlo: pro záporné teploty
  hodnota „přeteče" > 1300 → vzorec (50 - (raw - 65036) / 10) * -1.
"""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfTemperature,
    UnitOfVolumeFlowRate,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import DOMAIN, LOGGER


VOLTAGE_SENSORS = [
    {
        "register": "H10207",
        "key": "hp_voltage",
        "name": "Napětí TČ",
        "translation_key": "hp_voltage",
    },
]

FLOW_SENSORS = [
    {
        "register": "I11600",
        "key": "flow_sup_req",
        "name": "Požadovaný průtok přívod (SUP)",
        "translation_key": "flow_sup_req",
    },
    {
        "register": "I11602",
        "key": "flow_sup_act",
        "name": "Aktuální průtok přívod (SUP)",
        "translation_key": "flow_sup_act",
    },
    {
        "register": "I11601",
        "key": "flow_eta_req",
        "name": "Požadovaný průtok odtah (ETA)",
        "translation_key": "flow_eta_req",
    },
    {
        "register": "I11603",
        "key": "flow_eta_act",
        "name": "Aktuální průtok odtah (ETA)",
        "translation_key": "flow_eta_act",
    },
    {
        "register": "I11604",
        "key": "flow_oda_req",
        "name": "Požadovaný průtok venkovní (ODA)",
        "translation_key": "flow_oda_req",
    },
    {
        "register": "I11605",
        "key": "flow_oda_act",
        "name": "Aktuální průtok venkovní (ODA)",
        "translation_key": "flow_oda_act",
    },
]


TEMP_SENSORS = [
    {
        "register": "I10211",
        "key": "outdoor_temp",
        "name": "Venkovní teplota",
        "translation_key": "outdoor_temp",
    },
]


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    entities = [AtreaVoltageSensor(data, entry, spec) for spec in VOLTAGE_SENSORS]
    entities += [AtreaFlowSensor(data, entry, spec) for spec in FLOW_SENSORS]
    entities += [AtreaTemperatureSensor(data, entry, spec) for spec in TEMP_SENSORS]
    async_add_entities(entities)


class AtreaVoltageSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.VOLTAGE
    _attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
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
    def native_value(self):
        status = self._data.get("status")
        if not status or self._register not in status:
            return None
        try:
            # Analogový výstup: U = DATA/1000 (0–10000 → 0,0–10,0 V)
            return int(status[self._register]) / 1000
        except (TypeError, ValueError):
            LOGGER.debug(
                "Atrea sensor %s: unexpected value %r",
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


class AtreaFlowSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_native_unit_of_measurement = (
        UnitOfVolumeFlowRate.CUBIC_METERS_PER_HOUR
    )
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0
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
    def native_value(self):
        status = self._data.get("status")
        if not status or self._register not in status:
            return None
        try:
            # Průtok: hodnota = m³/h přímo (0..65535 ~ 0..65535 m³/h)
            return int(status[self._register])
        except (TypeError, ValueError):
            LOGGER.debug(
                "Atrea sensor %s: unexpected value %r",
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


class AtreaTemperatureSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 1
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
    def native_value(self):
        status = self._data.get("status")
        if not status or self._register not in status:
            return None
        try:
            raw = int(status[self._register])
        except (TypeError, ValueError):
            LOGGER.debug(
                "Atrea sensor %s: unexpected value %r",
                self._register,
                status.get(self._register),
            )
            return None
        # Teplota = °C × 10. Vodičové venkovní čidlo „přetéká" pro záporné
        # hodnoty > 1300 → korekce dle RD5 spec.
        if raw > 1300:
            return round((50 - (raw - 65036) / 10) * -1, 1)
        return raw / 10

    @property
    def available(self):
        status = self._data.get("status")
        return bool(status) and self._register in status

    @property
    def device_info(self):
        # Share device with the climate entity so all Atrea entities cluster
        # under one device card in HA UI.
        return {"identifiers": {(DOMAIN, slugify(f"atrea_{self._ip}"))}}
