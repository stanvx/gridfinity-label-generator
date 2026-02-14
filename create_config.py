#!/usr/bin/env python3
"""
Interactive wizard for creating Gridfinity label config files.

Run with:
    python create_config.py
"""

import json
import sys
from pathlib import Path

FASTENER_HEADS = ["pan", "countersunk", "button", "hex"]
FASTENER_SHAFTS = ["machine", "wood", "self-tapping"]
FASTENER_THREADS = ["full", "partial"]
FASTENER_DRIVERS = ["phillips", "hex", "slot", "torx"]
HARDWARE_TYPES = ["none", "nut"]
ORIENTATIONS = ["landscape", "portrait"]

DEFAULT_OPENSCAD_PATH = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"


def prompt(question: str, default=None, choices: list = None) -> str:
    if choices:
        choices_display = " | ".join(
            f"[{c}]" if c == default else c for c in choices
        )
        hint = f" ({choices_display})"
    elif default is not None:
        hint = f" [{default}]"
    else:
        hint = ""

    while True:
        try:
            value = input(f"  {question}{hint}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)

        if not value and default is not None:
            return str(default)
        if choices and value not in choices:
            print(f"    Choose from: {', '.join(choices)}")
            continue
        if value:
            return value
        print("    Value required.")


def prompt_float(question: str, default: float) -> float:
    while True:
        raw = prompt(question, default=default)
        try:
            return float(raw)
        except ValueError:
            print(f"    Enter a number (e.g. {default})")


def prompt_int(question: str, default: int) -> int:
    while True:
        raw = prompt(question, default=default)
        try:
            return int(raw)
        except ValueError:
            print(f"    Enter a whole number (e.g. {default})")


def prompt_yes_no(question: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        try:
            value = input(f"  {question} [{hint}]: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)
        if not value:
            return default
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        print("    Enter y or n.")


def print_header(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def collect_label_overrides() -> dict:
    overrides = {}

    head = input("    Fastener head override (blank to skip): ").strip()
    if head in FASTENER_HEADS:
        overrides["fastener_head"] = head
    elif head:
        print(f"      Unrecognised head type, skipping.")

    driver = input("    Driver type override (blank to skip): ").strip()
    if driver in FASTENER_DRIVERS:
        overrides["fastener_driver"] = driver
    elif driver:
        print(f"      Unrecognised driver type, skipping.")

    scale = input("    Fastener scale 0.1–1.0 (blank to skip): ").strip()
    if scale:
        try:
            overrides["fastener_scale"] = float(scale)
        except ValueError:
            print("      Not a number, skipping.")

    orientation = input("    Orientation landscape/portrait (blank to skip): ").strip()
    if orientation in ORIENTATIONS:
        overrides["fastener_orientation"] = orientation
    elif orientation:
        print("      Unrecognised orientation, skipping.")

    show = input("    Show fastener icon? y/n (blank to skip): ").strip().lower()
    if show == "n":
        overrides["show_fastener"] = False
        hw = input("    Hardware type none/nut (blank to skip): ").strip()
        if hw in HARDWARE_TYPES:
            overrides["hardware"] = hw

    font_size = input("    Font size in mm (blank to skip): ").strip()
    if font_size:
        try:
            overrides["font_size"] = float(font_size)
        except ValueError:
            print("      Not a number, skipping.")

    return overrides


def main() -> None:
    print("Gridfinity Label Config Wizard")
    print("=" * 40)
    print("Creates a JSON config file for generate_labels.py")

    # --- Output file ---
    print_header("Output file")
    name = prompt("Config name (without .json)", default="my_labels")
    output_file = Path(f"{name}.json")
    if output_file.exists():
        if not prompt_yes_no(f"{output_file} already exists. Overwrite?", default=False):
            print("Aborted.")
            return

    # --- Settings ---
    print_header("Settings")
    openscad_path = prompt("OpenSCAD path", default=DEFAULT_OPENSCAD_PATH)
    output_dir = prompt("Output directory", default=f"exports/{name}")
    filament_base = prompt_int("Filament slot for label body", default=1)
    filament_text = prompt_int("Filament slot for text/icon", default=2)

    # --- Defaults ---
    print_header("Label defaults  (apply to all labels unless overridden per-label)")
    fastener_head = prompt(
        "Fastener head type", default="pan", choices=FASTENER_HEADS
    )
    fastener_shaft = prompt(
        "Shaft type", default="machine", choices=FASTENER_SHAFTS
    )
    fastener_threads = prompt(
        "Thread coverage", default="full", choices=FASTENER_THREADS
    )
    fastener_driver = prompt(
        "Driver type", default="phillips", choices=FASTENER_DRIVERS
    )
    fastener_orientation = prompt(
        "Icon orientation", default="landscape", choices=ORIENTATIONS
    )
    font_size = prompt_float("Font size (mm)", default=4.5)

    defaults = {
        "fastener_head": fastener_head,
        "fastener_shaft": fastener_shaft,
        "fastener_threads": fastener_threads,
        "fastener_driver": fastener_driver,
        "fastener_orientation": fastener_orientation,
        "fastener_scale": 1.0,
        "font": "Open Sans",
        "font_style": "ExtraBold",
        "font_size": font_size,
    }

    # --- Labels ---
    print_header("Labels")
    print("  Enter labels one at a time. Leave name blank to finish.")
    print("  Name:  used for the output filename  (e.g. M3x10)")
    print("  Text:  printed on the label          (e.g. M3×10  -- use × not x)")
    print()

    labels = []
    while True:
        try:
            raw_name = input("  Label name (or blank to finish): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted.")
            sys.exit(0)

        if not raw_name:
            if not labels:
                print("    At least one label is required.")
                continue
            break

        # Suggest × substitution automatically
        suggested_text = raw_name.replace("x", "×") if "x" in raw_name.lower() else raw_name
        text = prompt(f"Display text for {raw_name}", default=suggested_text)

        label: dict = {"name": raw_name, "text": text}

        if prompt_yes_no(f"  Override any defaults for {raw_name}?", default=False):
            label.update(collect_label_overrides())

        labels.append(label)
        print(f"    Added {raw_name}")

    # --- Build and save ---
    config = {
        "settings": {
            "openscad_path": openscad_path,
            "output_dir": output_dir,
            "filaments": {
                "base": filament_base,
                "text": filament_text,
            },
        },
        "defaults": defaults,
        "labels": labels,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print()
    print(f"Saved {output_file}  ({len(labels)} label(s))")
    print(f"Generate with:  python generate_labels.py --config {output_file}")


if __name__ == "__main__":
    main()
