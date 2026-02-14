# Gridfinity Label Generator

Generate **multi-color 3MF files** for Gridfinity storage labels with filament slots pre-assigned -- open in Bambu Studio and print.

## Examples

| Countersunk hex screw | Knurled insert nut |
|---|---|
| ![M3x10 Countersunk Hex](examples/M3x10_countersunk_hex.png) | ![M3x5x4 Knurled Nut](examples/M3x5x4_knurled_nut.png) |

Labels can show different fastener icons (screws, nuts) or no icon at all -- controlled entirely by the config file.

## How It Works

Each label is generated in two passes through OpenSCAD, then merged into a single 3MF:

1. **Pass 1 -- Base**: exports the label body (background + fastener icon) with `Export_Mode="base"`
2. **Pass 2 -- Text**: exports the raised text only with `Export_Mode="text"`
3. **Merge**: Python combines both into a single 3MF with two material slots and Bambu Studio extruder assignments baked in

## Quick Start

### Prerequisites

- [OpenSCAD](https://openscad.org/) installed (default macOS path assumed, configurable)
- Python 3.10+
- Bambu Studio for printing

### Create a config, then generate

```bash
# Step 1: create your config
python create_config.py

# Step 2: generate labels
python generate_labels.py --config my_labels.json
```

Output goes to the directory specified in your config. Open any `.3mf` in Bambu Studio -- colors are already assigned:

- **Filament 1**: label body
- **Filament 2**: text and fastener icon

### Other options

```bash
# Single label from a config
python generate_labels.py --config my_labels.json --label M3x10

# First label only (quick test)
python generate_labels.py --config my_labels.json --test

# Custom output directory (overrides config)
python generate_labels.py --config my_labels.json --output exports/MyKit

# Save PNG previews alongside the 3MFs
python generate_labels.py --config my_labels.json --preview-dir exports/previews

# Control parallelism
python generate_labels.py --config my_labels.json --workers 4
```

## Creating a Config File

### Using the wizard

```bash
python create_config.py
```

The wizard walks through settings, defaults, and labels interactively and saves a ready-to-use JSON file.

### Editing by hand

Config files are JSON with three sections: `settings`, `defaults`, and `labels`.

```json
{
  "settings": {
    "openscad_path": "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD",
    "output_dir": "exports/MyKit",
    "filaments": {
      "base": 1,
      "text": 2
    }
  },
  "defaults": {
    "fastener_head": "pan",
    "fastener_shaft": "machine",
    "fastener_threads": "full",
    "fastener_driver": "phillips",
    "fastener_orientation": "landscape",
    "fastener_scale": 1.0,
    "font": "Open Sans",
    "font_style": "ExtraBold",
    "font_size": 4.5
  },
  "labels": [
    {"name": "M3x10", "text": "M3×10"},
    {"name": "M3x16", "text": "M3×16", "fastener_scale": 0.85}
  ]
}
```

Per-label keys override the defaults for that label only. Any key omitted on a label falls back to the default.

**Note:** use `×` (the multiplication sign U+00D7) rather than `x` in display text for correct typographic rendering.

## Config Parameter Reference

### `settings`

| Key | Description | Example |
|-----|-------------|---------|
| `openscad_path` | Path to OpenSCAD binary | `/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD` |
| `output_dir` | Where to write the 3MF files | `exports/MyKit` |
| `filaments.base` | Filament slot for label body | `1` |
| `filaments.text` | Filament slot for text and icon | `2` |

### `defaults` and per-label overrides

| Key | Values | Description |
|-----|--------|-------------|
| `fastener_head` | `pan` `countersunk` `button` `hex` | Screw head shape |
| `fastener_shaft` | `machine` `wood` `self-tapping` | Shaft style |
| `fastener_threads` | `full` `partial` | Thread coverage along shaft |
| `fastener_driver` | `phillips` `hex` `slot` `torx` | Drive type |
| `fastener_orientation` | `landscape` `portrait` | Icon layout direction |
| `fastener_scale` | `0.1` – `1.0` | Icon size multiplier |
| `show_fastener` | `true` `false` | Whether to show any fastener icon |
| `hardware` | `none` `nut` | Hardware icon type (for nuts, inserts) |
| `hardware_scale` | `0.1` – `1.0` | Hardware icon size multiplier |
| `font` | font name string | Text font (bundled: `Open Sans`) |
| `font_style` | `Regular` `Bold` `ExtraBold` | Font weight |
| `font_size` | number (mm) | Text size in millimetres |
| `text2` | string | Optional second line of text |

## Example Configs

A few configs are included as starting points:

| File | Description |
|------|-------------|
| `labels_m3_countersunk_hex_config.json` | M3 countersunk screws, hex socket driver |
| `labels_m3_flathead_hex_config.json` | M3 countersunk screws, hex socket driver, extended range |
| `labels_m3_flathead_screwdriver_config.json` | M3 countersunk screws, slot driver |

## Print Settings

- Layer height: 0.2 mm
- Infill: 10–15%
- Supports: not needed
- Filament 1: label body color (e.g. white, light grey)
- Filament 2: text/icon color (e.g. black, dark grey)

## Credits

- OpenSCAD label model and fastener icons by [CullenJWebb](https://makerworld.com/en/models/578922) (Cullenect Labels)
- Open Sans font by Steve Matteson, licensed under Apache License 2.0

## License

MIT
