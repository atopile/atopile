# LED Autopick Plan

Stdlib component:

- `/Users/narayanpowderly/projects/atopile/src/faebryk/library/LED.py`

## JLC Scope

Use LED-like subcategories across multiple top-level categories (not only `Photoelectric Devices`):

- `Light Emitting Diodes (LED)`
- `LED Indication - Discrete`
- `Infrared (IR) LEDs`
- `Ultra Violet LEDs`
- `RGB LEDs`
- `Infrared LED Emitters`

Reason:

- JLC has LED inventory spread across category trees; restricting to one category misses many valid rows.

## Proposed Filter Strategy

Hard required (MVP fast table):

- `stock > 0`
- package present (`package` not empty, not `-`)
- parseable:
  - `color_code`
  - `forward_voltage_v`
  - `max_current_a`

Optional:

- `max_brightness_cd` (or radiant intensity fallback for IR/UV)
- `dominant_wavelength_nm` / `peak_wavelength_nm`

## Counts (Expanded Scope)

- raw rows in scope: `49,245`
- in-stock + valid package: `4,813`
- hard-required set (`color + Vf + I`): `624`
- with brightness additionally required: `513`

## Data Notes

- Low count is mostly stock/package/category-noise, not numeric parsing quality.
- Color normalization needs aggressive mapping:
  - examples seen: `White`, `Emerald`, `Ice Blue`, `Green-yellow`, `RGB`, Chinese text
- Brightness fields are inconsistent:
  - `Luminous Intensity` (cd/mcd style)
  - `Radiant Intensity` (IR/UV family)
