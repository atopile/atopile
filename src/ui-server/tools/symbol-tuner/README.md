# Symbol Tuner (Dev Tool)

Standalone visual editor for tuning canonical KiCad symbol rendering parameters:

- move symbol body (`bodyOffsetX`, `bodyOffsetY`)
- rotate symbol body (`bodyRotationDeg`)
- shorten/lengthen leads (`leadDelta`)

The preview now uses the same geometry path as the schematic canvas, including:

- canonical symbol scaling/orientation logic,
- component pin-grid normalization (`2.54mm`),
- per-component grid alignment offset,
- instance rotation/mirror transform.

## Run

From `src/ui-server`:

```bash
npm run dev:symbol-tuner
```

Then open:

- `http://localhost:5173/tools/symbol-tuner.html`

Use **Copy JSON** to export the per-family tuning map.
