"""Button entity pro reset intervalu výměny filtru (C10007).

Z RD5 specs (tab.11): zapsání 1 do C10007 nastaví další interval výměny filtru
podle hodnoty H10910 (defaultně 90 dní). User stiskne tlačítko po fyzické
výměně filtru, integrace zapíše 1, RD5 restartuje 90denní (nebo jiný) clock
a D11183 (= Interval výměny filtru flag) přepne zpět na 0.
"""

from homeassistant.components.button import ButtonEntity
from homeassistant.util import slugify

from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([AtreaFilterResetButton(data, entry)])


class AtreaFilterResetButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Reset intervalu výměny filtru"
    _attr_translation_key = "filter_reset"
    _attr_icon = "mdi:air-filter"

    def __init__(self, data, entry):
        self._data = data
        self._atrea = data["atrea"]
        self._coordinator = data["coordinator"]
        self._entry_id = entry.entry_id
        self._ip = entry.data.get("ip_address")
        self._attr_unique_id = slugify(f"atrea_{self._ip}_filter_reset")

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, slugify(f"atrea_{self._ip}"))}}

    async def async_press(self):
        """Zapíše 1 do C10007 — Atrea restartuje filter clock."""
        LOGGER.info("Atrea: pressing reset filter interval (C10007=1)")
        self._atrea.commands.clear()
        self._atrea.setCommand("C10007", 1)
        await self.hass.async_add_executor_job(self._atrea.exec)
        await self._coordinator.async_refresh()
