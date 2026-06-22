"""Button entity pro Atrea — reset filtru (C10007) + reset alarmů (C10006).

Z RD5 specs:
- C10007 (tab.11): zapsání 1 nastaví další interval výměny filtru podle H10910
  (defaultně 90 dní). User stiskne po fyzické výměně filtru → RD5 restartuje
  clock a D11183 přepne zpět na 0.
- C10006: zapsání 1 provede reset vybraných alarmů (např. nevyrovnaný průtok
  D11114, porucha manometru D11105 — viz serv. dokumentace). User stiskne po
  odstranění příčiny, aby se jednotka znovu spustila.
"""

from homeassistant.components.button import ButtonEntity
from homeassistant.util import slugify

from .const import DOMAIN, LOGGER


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            AtreaFilterResetButton(data, entry),
            AtreaAlarmResetButton(data, entry),
        ]
    )


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


class AtreaAlarmResetButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_name = "Reset alarmů"
    _attr_translation_key = "alarm_reset"
    _attr_icon = "mdi:alarm-light"

    def __init__(self, data, entry):
        self._data = data
        self._atrea = data["atrea"]
        self._coordinator = data["coordinator"]
        self._entry_id = entry.entry_id
        self._ip = entry.data.get("ip_address")
        self._attr_unique_id = slugify(f"atrea_{self._ip}_alarm_reset")

    @property
    def device_info(self):
        return {"identifiers": {(DOMAIN, slugify(f"atrea_{self._ip}"))}}

    async def async_press(self):
        """Zapíše 1 do C10006 — reset vybraných alarmů (např. D11114)."""
        LOGGER.info("Atrea: pressing reset alarms (C10006=1)")
        self._atrea.commands.clear()
        self._atrea.setCommand("C10006", 1)
        await self.hass.async_add_executor_job(self._atrea.exec)
        await self._coordinator.async_refresh()
