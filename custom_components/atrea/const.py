import logging
from datetime import timedelta

from homeassistant.components.climate.const import ClimateEntityFeature, HVACMode
from pyatrea import AtreaMode

DOMAIN = "atrea"
LOGGER = logging.getLogger(__name__)
UPDATE_DELAY = 1  # update delay disabled
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=10)
SUPPORT_FLAGS = (
    ClimateEntityFeature.TARGET_TEMPERATURE
    | ClimateEntityFeature.FAN_MODE
    | ClimateEntityFeature.PRESET_MODE
    | ClimateEntityFeature.TURN_OFF
    | ClimateEntityFeature.TURN_ON
)
DEFAULT_NAME = "Atrea"
STATE_MANUAL = "manual"
STATE_UNKNOWN = "unknown"
CONF_FAN_MODES = "fan_modes"
CONF_PRESETS = "presets"
DEFAULT_FAN_MODE_LIST = "12,20,30,40,50,60,70,80,90,100"
ALL_PRESET_LIST = [
    "Off",
    "Automatic",
    "Ventilation",
    "Circulation and Ventilation",
    "Circulation",
    "Night precooling",
    "Disbalance",
    "Overpressure",
    "Periodic ventilation",
    "Startup",
    "Rundown",
    "Defrosting",
    "External",
    "HP defrosting",
    "IN1",
    "IN2",
    "D1",
    "D2",
    "D3",
    "D4",
]

# CZ display labels — mapping z EN internal IDs na CZ názvy podle RD5 ovládací jednotky.
# ALL_PRESET_LIST zůstává EN (stable internal IDs, nerozbíjí existing config entries).
# Display překlad se aplikuje v climate.py preset_mode/preset_modes properties.
PRESET_LABELS_CZ = {
    "Off": "Vypnuto",
    "Automatic": "Automat",
    "Ventilation": "Větrání",
    "Circulation and Ventilation": "Cirkulace s větráním",
    "Circulation": "Cirkulace",
    "Night precooling": "Noční předchlazení",
    "Disbalance": "Rozvážení",
    "Overpressure": "Přetlakové větrání",
    "Periodic ventilation": "Periodické větrání",
    "Startup": "Náběh",
    "Rundown": "Doběh",
    "Defrosting": "Odmrazování",
    "External": "Externí",
    "HP defrosting": "Odmrazování TČ",
    # IN1, IN2, D1-D4 zůstávají jako technické identifikátory bez překladu
}

ICONS = {
    AtreaMode.OFF: "mdi:fan-off",
    AtreaMode.AUTOMATIC: "mdi:fan",
    AtreaMode.VENTILATION: "mdi:fan-chevron-up",
    AtreaMode.CIRCULATION_AND_VENTILATION: "mdi:fan",
    AtreaMode.CIRCULATION: "mdi:fan-chevron-down",
    AtreaMode.NIGHT_PRECOOLING: "mdi:fan-speed-1",
    AtreaMode.DISBALANCE: "mdi:fan-speed-2",
    AtreaMode.OVERPRESSURE: "mdi:fan-speed-3",
    AtreaMode.STARTUP: "mdi:chevron-up",
    AtreaMode.RUNDOWN: "mdi:chevron-down",
    AtreaMode.DEFROSTING: "mdi:car-defrost-rear",
    AtreaMode.EXTERNAL: "mdi:fan-alert",
    AtreaMode.HP_DEFROSTING: "mdi:car-defrost-front",
    AtreaMode.IN1: "mdi:fan-chevron-up",
    AtreaMode.IN2: "mdi:fan-chevron-up",
    AtreaMode.D1: "mdi:fan-chevron-up",
    AtreaMode.D2: "mdi:fan-chevron-up",
    AtreaMode.D3: "mdi:fan-chevron-up",
    AtreaMode.D4: "mdi:fan-chevron-up",
}

HVAC_MODES = [HVACMode.OFF, HVACMode.AUTO, HVACMode.FAN_ONLY]


# === RD5 Fan Mode Support pro R_5 jednotky (H10510=4) ===
# Pro R_5 série Atrea nepoužívá procenta, ale discrete hodnoty H10704/H10708.
# Reference: RD5 Modbus parameters dokumentace, tab.4.

# Control mode register hodnoty (z H10510)
CONTROL_MODE_DIRECT = 0       # Přímé řízení (procenta 12-100%)
CONTROL_MODE_CONST_FLOW = 1   # Konstantní průtok (1-100%)
CONTROL_MODE_CONST_PRESSURE = 2  # Konstantní tlak (1=NOC, 2=DEN)
CONTROL_MODE_IN1_IN2 = 3      # Dle IN1/IN2 (12-100%)
CONTROL_MODE_R_5 = 4          # R_5 jednotky (discrete + kombinace)

# Modbus hodnoty pro H10704/H10708 v R_5 módu (label → register value)
R5_FAN_VENTILATION = {
    "Vypnuto": 0,
    "Min": 10,
    "Norm": 11,
    "Max": 12,
}

R5_FAN_CIRCULATION = {
    "Vypnuto": 0,
    "Min": 20,
    "Norm": 21,
    "Max": 22,
}

# Cirkulace s větráním — formát "cirkulace/větrání" (= výkon cirk / výkon vět)
R5_FAN_CIRC_VENT = {
    "Vypnuto": 0,
    "Min/Min": 30,
    "Min/Norm": 31,
    "Min/Max": 32,
    "Norm/Min": 33,
    "Norm/Norm": 34,
    "Norm/Max": 35,
    "Max/Min": 36,
    "Max/Norm": 37,
    "Max/Max": 38,
}

# Default fan_modes pro generic preset (Off, Automatic, Night precooling, ...) v R_5
R5_FAN_GENERIC = {
    "Vypnuto": 0,
    "Min": 10,
    "Norm": 11,
    "Max": 12,
}

# Reverse mapping pro decode H10704 read value → label
def r5_decode_fan_value(value, preset_en=None):
    """Decode H10704 numeric value na human-readable label.

    preset_en (volitelný): aktuální předvolba. Při přepínání H10704 chvíli drží
    hodnotu STARÉ předvolby (jiný formát) — dekódovaná hodnota pak není v
    fan_modes nové předvolby → dropdown se „rozbije" na prázdno. Když je preset
    zadaný, zkoerceujeme hodnotu tak, aby vždy patřila do jeho seznamu:
    kombinaci (cirk/vět) rozložíme na komponentu odpovídající předvolbě, a
    naopak single hodnotu v kombinované předvolbě zdvojíme na combo.
    """
    if value is None:
        return None
    v = int(value)
    if v == 0:
        return "Vypnuto"
    levels = {0: "Min", 1: "Norm", 2: "Max"}
    # Kombinace cirk+vět (30-38), formát "cirkulace/větrání"
    if 30 <= v <= 38:
        circ = levels[(v - 30) // 3]
        vent = levels[(v - 30) % 3]
        if preset_en == "Circulation":
            return circ
        if preset_en in (None, "Circulation and Ventilation"):
            return f"{circ}/{vent}"
        # Ventilation / Automatic / generic single-fan → větrací komponenta
        return vent
    # Single: větrání (10-12) nebo cirkulace (20-22)
    if 10 <= v <= 12:
        single = levels[v - 10]
    elif 20 <= v <= 22:
        single = levels[v - 20]
    else:
        return f"Neznámý ({v})"
    # Opačný směr: single hodnota, ale předvolba je kombinovaná → udělej combo
    if preset_en == "Circulation and Ventilation":
        return f"{single}/{single}"
    return single


def r5_fan_modes_for_preset(preset_en):
    """Vrátí dostupné fan_modes labels pro daný preset (EN ID)."""
    if preset_en == "Off":
        return ["Vypnuto"]
    elif preset_en == "Automatic":
        # Auto = řízeno týdenním plánem, výkon se nenastavuje ručně
        return list(R5_FAN_VENTILATION.keys())
    elif preset_en == "Ventilation":
        return list(R5_FAN_VENTILATION.keys())
    elif preset_en == "Circulation":
        return list(R5_FAN_CIRCULATION.keys())
    elif preset_en == "Circulation and Ventilation":
        return list(R5_FAN_CIRC_VENT.keys())
    else:
        # Pro presets typu Night precooling, Disbalance, Overpressure, ...
        return list(R5_FAN_GENERIC.keys())


def r5_fan_value_for_preset(preset_en, fan_label):
    """Map (preset, label) → Modbus value pro H10708 zápis."""
    if fan_label == "Vypnuto":
        return 0
    if preset_en == "Ventilation":
        return R5_FAN_VENTILATION.get(fan_label)
    elif preset_en == "Circulation":
        return R5_FAN_CIRCULATION.get(fan_label)
    elif preset_en == "Circulation and Ventilation":
        return R5_FAN_CIRC_VENT.get(fan_label)
    else:
        return R5_FAN_GENERIC.get(fan_label)


def _r5_levels(v):
    """Rozloží H10704 hodnotu na (circ_level, vent_level), 0=Min/1=Norm/2=Max.
    Pro single vrátí jen relevantní složku, druhá = None."""
    if 10 <= v <= 12:
        return (None, v - 10)   # větrání single
    if 20 <= v <= 22:
        return (v - 20, None)   # cirkulace single
    if 30 <= v <= 38:
        return ((v - 30) // 3, (v - 30) % 3)  # kombinace cirk/vět
    return (None, None)


def r5_map_power_to_preset(old_value, target_en):
    """Level-preserving mapování výkonu při změně předvolby.

    Vezme výkon PŘED přepnutím (old_value = H10704) a překóduje jeho úroveň
    (Min/Norm/Max) do rozsahu nové předvolby, aby jednotka po přepnutí běžela
    dál (nespadla do off) a hodnota byla platná pro nový fan_modes seznam.

    - 0 (vypnuto) → 0 (zůstává vypnuto)
    - → Cirkulace: 20 + cirk. úroveň (z combo cirk složka; ze single ta úroveň)
    - → Cirk+vět: 30 + circ*3 + vent (single → ta složka, druhá Min)
    - → Větrání / generic: 10 + vět. úroveň (z combo vět složka)
    Vrací None pro neznámou hodnotu (volající pak nechá stávající chování).
    """
    if old_value is None:
        return None
    v = int(old_value)
    if v == 0:
        return 0
    cl, vl = _r5_levels(v)
    if cl is None and vl is None:
        return None
    if target_en == "Off":
        return 0
    if target_en == "Circulation":
        lvl = cl if cl is not None else vl
        return 20 + lvl
    if target_en == "Circulation and Ventilation":
        circ = cl if cl is not None else 0
        vent = vl if vl is not None else 0
        return 30 + circ * 3 + vent
    # Větrání / Automatický / generic (Noční předchlazení, ...)
    lvl = vl if vl is not None else cl
    return 10 + lvl
