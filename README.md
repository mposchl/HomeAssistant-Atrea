# HomeAssistant-Atrea (fork: česká lokalizace + R_5)

Custom component - climate platform - for Atrea ventilation units for Home Assistant

## Tento fork

Fork od [JurajNyiri/HomeAssistant-Atrea](https://github.com/JurajNyiri/HomeAssistant-Atrea) s těmito úpravami:

- **Česká lokalizace** — kompletní překlad config flow, dialogu nastavení, názvů předvoleb (Větrání / Cirkulace / Cirkulace s větráním / Noční předchlazení / Rozvážení / Přetlakové větrání), HVAC módů (Vypnuto / Týdenní program / Ruční) a labelů atributů (Výkon / Režim / Řízení VZT).
- **Nativní podpora jednotek řady R_5** (Modbus parameter `H10510=4`) — discrete výkonové stupně podle RD5 specifikace místo procent:
  - Větrání / Cirkulace / další předvolby: `Vypnuto / Min / Norm / Max`
  - Cirkulace s větráním: 9 kombinací (`Min/Min`, `Min/Norm`, ..., `Max/Max`) — formát „výkon cirkulace / výkon větrání"
- **Oprava kompatibility s HA 2025.12+** — odstraněn deprecated `self.config_entry = config_entry` v `OptionsFlow.__init__`, který v HA 2025.12+ vedl k HTTP 500 v dialogu Konfigurace.

**Backward compatibility:** Jednotky Duplex (H10510 ∈ {0, 1, 2, 3}) zachovávají původní procentuální logiku — nic se pro ně nemění.

## Instalace přes HACS

1. HACS → Integrations → ⋮ → **Custom repositories**
2. URL: `https://github.com/mposchl/HomeAssistant-Atrea`
3. Category: **Integration**
4. Add → Install → restart Home Assistant
5. Settings → Devices & Services → Add Integration → vyhledat „Atrea"

## Installation using HACS

HACS is a community store for Home Assistant. You can install [HACS](https://github.com/custom-components/hacs) and then install Atrea from the HACS store.

## Installation:

1. In your Home Assistant instance, create directory `/custom_components/atrea` in your `/config` directory.
2. Copy all files from [/custom_components/atrea](https://github.com/JurajNyiri/HomeAssistant-Atrea/tree/master/custom_components/atrea) of this repository to the newly created directory in your Home Assistant.

## Usage:

Add climate unit via Integrations (search for Atrea) in Home Assistant UI. You can also simply click the button below if you have MyHomeAssistant redirects set up.

[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=atrea)
