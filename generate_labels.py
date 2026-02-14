#!/usr/bin/env python3
"""
3MF Label Generator with Pre-assigned Colors

Generates 3MF files for Gridfinity labels with colors already assigned,
eliminating the tedious import workflow in Bambu Studio.

Strategy:
1. Export base.3mf with Export_Mode="base"
2. Export text.3mf with Export_Mode="text"
3. Combine both into a single 3MF with separate objects
4. Assign filament slots to each object

Usage:
    python generate_labels.py              # Generate all labels (parallel)
    python generate_labels.py --label M2x10   # Generate specific label
    python generate_labels.py --test       # Test with one label
    python generate_labels.py --workers 4  # Specify number of threads
"""

import argparse
import concurrent.futures
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

# Script directory
SCRIPT_DIR = Path(__file__).parent.resolve()

# XML namespaces used in 3MF
NS_3MF = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
NS_MATERIAL = "http://schemas.microsoft.com/3dmanufacturing/material/2015/02"
NS_PRODUCTION = "http://schemas.microsoft.com/3dmanufacturing/production/2015/06"


def load_config(config_path: Path) -> dict:
    """Load label configuration from JSON file."""
    with open(config_path) as f:
        return json.load(f)


def generate_openscad_3mf(
    openscad_path: str,
    scad_file: Path,
    output_file: Path,
    text: str,
    text2: str,
    export_mode: str,  # "base" or "text"
    label_config: dict,  # merged defaults + per-label overrides
) -> bool:
    """
    Generate 3MF file using OpenSCAD.
    """
    # Build OpenSCAD command with variable overrides
    cmd = [
        openscad_path,
        "-o",
        str(output_file),
        # Enable experimental features for proper 3MF export
        "--enable=lazy-union",
        "--enable=manifold",
        # Override variables for this specific label
        "-D",
        f'Text1="{text}"',
        "-D",
        f'Text2="{text2}"',
        "-D",
        f'Fastener_Head="{label_config["fastener_head"]}"',
        "-D",
        f'Fastener_Shaft="{label_config["fastener_shaft"]}"',
        "-D",
        f'Fastener_Threads="{label_config["fastener_threads"]}"',
        "-D",
        f'Fastener_Driver="{label_config["fastener_driver"]}"',
        "-D",
        f'Fastener_Orientation="{label_config.get("fastener_orientation", "landscape")}"',
        "-D",
        f"Fastener_Scale={label_config.get('fastener_scale', 1.0)}",
        "-D",
        f"Show_Fastener={str(label_config.get('show_fastener', True)).lower()}",
        "-D",
        f'Select_Hardware="{label_config.get("hardware", "none")}"',
        "-D",
        f"Hardware_Scale={label_config.get('hardware_scale', 1.0)}",
        "-D",
        f'Text1_Font="{label_config["font"]}"',
        "-D",
        f'Text1_Font_Style="{label_config["font_style"]}"',
        "-D",
        f"Text1_Font_Size={label_config['font_size']}",
        "-D",
        "label_surface=02",  # Flush mode for multi-color
        "-D",
        f'Export_Mode="{export_mode}"',  # base or text
        str(scad_file),
    ]

    try:
        # Set font path environment variable
        env = os.environ.copy()
        fonts_dir = SCRIPT_DIR / "fonts"
        if fonts_dir.exists():
            # Add to existing path or create new
            if "OPENSCAD_FONT_PATH" in env:
                env["OPENSCAD_FONT_PATH"] = f"{fonts_dir}:{env['OPENSCAD_FONT_PATH']}"
            else:
                env["OPENSCAD_FONT_PATH"] = str(fonts_dir)

        # Reduced timeout for parallel execution
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180, env=env
        )

        if result.returncode != 0:
            return False, f"OpenSCAD error: {result.stderr}"

        if not output_file.exists():
            return False, "Output file not created"

        return True, None

    except subprocess.TimeoutExpired:
        return False, "OpenSCAD timed out"
    except Exception as e:
        return False, str(e)


def generate_preview_png(
    openscad_path: str,
    scad_file: Path,
    output_file: Path,
    text: str,
    text2: str,
    label_config: dict,
) -> tuple[bool, str]:
    """Generate a PNG preview using the same label settings."""
    cmd = [
        openscad_path,
        "-o",
        str(output_file),
        "--autocenter",
        "--viewall",
        "--projection=ortho",
        "--imgsize=1400,420",
        "-D",
        f'Text1="{text}"',
        "-D",
        f'Text2="{text2}"',
        "-D",
        f'Fastener_Head="{label_config["fastener_head"]}"',
        "-D",
        f'Fastener_Shaft="{label_config["fastener_shaft"]}"',
        "-D",
        f'Fastener_Threads="{label_config["fastener_threads"]}"',
        "-D",
        f'Fastener_Driver="{label_config["fastener_driver"]}"',
        "-D",
        f'Fastener_Orientation="{label_config.get("fastener_orientation", "landscape")}"',
        "-D",
        f"Fastener_Scale={label_config.get('fastener_scale', 1.0)}",
        "-D",
        f"Show_Fastener={str(label_config.get('show_fastener', True)).lower()}",
        "-D",
        f'Select_Hardware="{label_config.get("hardware", "none")}"',
        "-D",
        f"Hardware_Scale={label_config.get('hardware_scale', 1.0)}",
        "-D",
        f'Text1_Font="{label_config["font"]}"',
        "-D",
        f'Text1_Font_Style="{label_config["font_style"]}"',
        "-D",
        f"Text1_Font_Size={label_config['font_size']}",
        "-D",
        "label_surface=02",
        "-D",
        'Export_Mode="all"',
        str(scad_file),
    ]

    try:
        env = os.environ.copy()
        fonts_dir = SCRIPT_DIR / "fonts"
        if fonts_dir.exists():
            if "OPENSCAD_FONT_PATH" in env:
                env["OPENSCAD_FONT_PATH"] = f"{fonts_dir}:{env['OPENSCAD_FONT_PATH']}"
            else:
                env["OPENSCAD_FONT_PATH"] = str(fonts_dir)

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180, env=env
        )

        if result.returncode != 0:
            return False, f"OpenSCAD preview error: {result.stderr}"

        if not output_file.exists():
            return False, "Preview file not created"

        return True, None

    except subprocess.TimeoutExpired:
        return False, "OpenSCAD preview timed out"
    except Exception as e:
        return False, str(e)


def combine_3mf_files(
    base_3mf: Path,
    text_3mf: Path,
    output_3mf: Path,
    label_name: str,
    filament_base: int = 1,
    filament_text: int = 2,
) -> tuple[bool, str]:
    """
    Combine base and text 3MF files into a single multi-part 3MF.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)

            # Extract base 3MF
            with zipfile.ZipFile(base_3mf, "r") as zf:
                zf.extractall(tmpdir)

            # Parse the base model
            model_path = tmpdir / "3D" / "3dmodel.model"
            tree = ET.parse(model_path)
            root = tree.getroot()

            # --- METADATA SPOOFING FOR BAMBU STUDIO ---
            # Update Application metadata to suppress warnings
            ns = {"ns0": NS_3MF}

            # Find or create metadata items
            # Default might have: <metadata name="Application">OpenSCAD ...</metadata>

            # We want: <metadata name="Application">BambuStudio</metadata>

            # Helper to set metadata
            def set_metadata(name, value):
                found = False
                for meta in root.findall(f"{{{NS_3MF}}}metadata"):
                    if meta.get("name") == name:
                        meta.text = value
                        found = True
                        break
                if not found:
                    meta = ET.Element(f"{{{NS_3MF}}}metadata", name=name)
                    meta.text = value
                    # Insert at top
                    root.insert(0, meta)

            set_metadata("Application", "BambuStudio")
            set_metadata("ApplicationVersion", "01.09.00.00")
            # ------------------------------------------

            # Get base mesh
            base_obj = root.find(".//{%s}object" % NS_3MF)
            base_mesh = base_obj.find("{%s}mesh" % NS_3MF)

            # Clear existing objects in resources
            resources = root.find("{%s}resources" % NS_3MF)

            # Remove existing objects (we'll add new ones)
            for obj in list(resources.findall("{%s}object" % NS_3MF)):
                resources.remove(obj)

            # Create materials for base and text
            basematerials = resources.find("{%s}basematerials" % NS_3MF)
            if basematerials is None:
                basematerials = ET.SubElement(
                    resources, f"{{{NS_3MF}}}basematerials", id="1"
                )
            else:
                # Clear existing materials
                for mat in list(basematerials):
                    basematerials.remove(mat)

            # Add our materials
            ET.SubElement(
                basematerials,
                f"{{{NS_3MF}}}base",
                name="Base",
                displaycolor="#C0C0C0FF",
            )
            ET.SubElement(
                basematerials,
                f"{{{NS_3MF}}}base",
                name="Text",
                displaycolor="#333333FF",
            )

            # Add base object (ID=2)
            base_obj_new = ET.SubElement(
                resources,
                f"{{{NS_3MF}}}object",
                id="2",
                name="Base",
                type="model",
                pid="1",
                pindex="0",
            )
            base_obj_new.append(base_mesh)

            # Read text mesh from text_3mf
            with zipfile.ZipFile(text_3mf, "r") as zf:
                text_model_content = zf.read("3D/3dmodel.model").decode("utf-8")

            text_root = ET.fromstring(text_model_content)
            text_obj = text_root.find(".//{%s}object" % NS_3MF)
            text_mesh = text_obj.find("{%s}mesh" % NS_3MF)

            # Add text object (ID=3)
            # Ensure text is slightly higher in Z priority if needed (Bambu usually handles this by geometry)
            text_obj_new = ET.SubElement(
                resources,
                f"{{{NS_3MF}}}object",
                id="3",
                name="Text",
                type="model",
                pid="1",
                pindex="1",
            )
            text_obj_new.append(text_mesh)

            # Update build section to reference both objects
            build = root.find("{%s}build" % NS_3MF)
            if build is None:
                build = ET.SubElement(root, f"{{{NS_3MF}}}build")
            else:
                # Clear existing items
                for item in list(build):
                    build.remove(item)

            # Add build items for both objects
            ET.SubElement(build, f"{{{NS_3MF}}}item", objectid="2")
            ET.SubElement(build, f"{{{NS_3MF}}}item", objectid="3")

            # Register namespaces to avoid ns0: prefixes
            ET.register_namespace("", NS_3MF)
            ET.register_namespace("m", NS_MATERIAL)
            ET.register_namespace("p", NS_PRODUCTION)

            # Write updated model
            tree.write(model_path, xml_declaration=True, encoding="UTF-8")

            # Create Bambu Studio settings files
            metadata_dir = tmpdir / "Metadata"
            metadata_dir.mkdir(exist_ok=True)

            # Model settings with extruder assignments
            settings_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
  <object id="2">
    <metadata key="name" value="Base"/>
    <metadata key="extruder" value="{filament_base}"/>
  </object>
  <object id="3">
    <metadata key="name" value="Text"/>
    <metadata key="extruder" value="{filament_text}"/>
  </object>
</config>
'''
            with open(metadata_dir / "model_settings.config", "w") as f:
                f.write(settings_content)

            # Plate config
            plate_content = """<?xml version="1.0" encoding="UTF-8"?>
<plate>
  <metadata key="plater_id" value="1"/>
  <metadata key="locked" value="false"/>
  <model_instance>
    <metadata key="object_id" value="2"/>
    <metadata key="instance_id" value="0"/>
  </model_instance>
  <model_instance>
    <metadata key="object_id" value="3"/>
    <metadata key="instance_id" value="0"/>
  </model_instance>
</plate>
"""
            with open(metadata_dir / "plate_1.config", "w") as f:
                f.write(plate_content)

            # Create final 3MF
            with zipfile.ZipFile(output_3mf, "w", zipfile.ZIP_DEFLATED) as zf:
                for file_path in tmpdir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(tmpdir)
                        zf.write(file_path, arcname)

            return True, None

    except Exception as e:
        import traceback

        traceback.print_exc()
        return False, str(e)


def process_single_label(
    label, config, output_dir, preview_dir=None
) -> tuple[bool, str, str]:
    """
    Process a single label. intended for use in thread pool.
    Returns: (success, name, message)
    """
    name = label["name"]
    text = label["text"]
    text2 = label.get("text2", config["defaults"].get("text2", ""))

    # Merge defaults with per-label overrides
    label_config = {**config["defaults"]}
    for key in [
        "fastener_head",
        "fastener_shaft",
        "fastener_threads",
        "fastener_driver",
        "fastener_orientation",
        "fastener_scale",
        "font_size",
        "text2",
        "show_fastener",
        "hardware",
        "hardware_scale",
    ]:
        if key in label:
            label_config[key] = label[key]

    openscad_path = config["settings"]["openscad_path"]
    scad_file = SCRIPT_DIR / "labels.scad"

    try:
        # Each thread needs its own temp directory
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            base_3mf = tmpdir / f"{name}_base.3mf"
            text_3mf = tmpdir / f"{name}_text.3mf"
            output_3mf = output_dir / f"{name}.3mf"

            # Generate base
            ok, msg = generate_openscad_3mf(
                openscad_path, scad_file, base_3mf, text, text2, "base", label_config
            )
            if not ok:
                return False, name, f"Failed base export: {msg}"

            # Generate text
            ok, msg = generate_openscad_3mf(
                openscad_path, scad_file, text_3mf, text, text2, "text", label_config
            )
            if not ok:
                return False, name, f"Failed text export: {msg}"

            # Combine
            filaments = config["settings"]["filaments"]
            ok, msg = combine_3mf_files(
                base_3mf,
                text_3mf,
                output_3mf,
                name,
                filament_base=filaments["base"],
                filament_text=filaments["text"],
            )
            if not ok:
                return False, name, f"Failed combination: {msg}"

            if preview_dir is not None:
                preview_file = preview_dir / f"{name}.png"
                ok, msg = generate_preview_png(
                    openscad_path,
                    scad_file,
                    preview_file,
                    text,
                    text2,
                    label_config,
                )
                if not ok:
                    return False, name, f"Failed preview: {msg}"

        return True, name, f"Generated {name}.3mf"

    except Exception as e:
        return False, name, f"Exception: {str(e)}"


def main():
    parser = argparse.ArgumentParser(
        description="Generate 3MF label files with pre-assigned colors"
    )
    parser.add_argument(
        "--label", "-l", help="Generate only this specific label (by name)"
    )
    parser.add_argument(
        "--test",
        "-t",
        action="store_true",
        help="Test mode: generate only the first label",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=os.cpu_count() or 4,
        help="Number of parallel workers",
    )
    parser.add_argument(
        "--config",
        "-c",
        type=Path,
        required=True,
        help="Path to config JSON file (create one with: python create_config.py)",
    )
    parser.add_argument(
        "--output", "-o", type=Path, help="Output directory (default: from config)"
    )
    parser.add_argument(
        "--preview-dir",
        type=Path,
        help="Optional directory for PNG previews",
    )

    args = parser.parse_args()

    # Load configuration
    if not args.config.exists():
        print(f"Error: config file not found: {args.config}", file=sys.stderr)
        print("Create one with: python create_config.py", file=sys.stderr)
        sys.exit(1)
    config = load_config(args.config)

    # Determine output directory
    output_dir = args.output or SCRIPT_DIR / config["settings"]["output_dir"]
    output_dir.mkdir(exist_ok=True)

    preview_dir = None
    if args.preview_dir:
        preview_dir = args.preview_dir
        preview_dir.mkdir(parents=True, exist_ok=True)

    # Determine which labels to generate
    labels = config["labels"]

    if args.test:
        labels = labels[:1]
        print("Test mode: generating first label only")
    elif args.label:
        labels = [l for l in labels if l["name"] == args.label]
        if not labels:
            print(f"Error: label '{args.label}' not found in config", file=sys.stderr)
            sys.exit(1)

    # Check OpenSCAD exists
    openscad_path = config["settings"]["openscad_path"]
    if not Path(openscad_path).exists():
        print(f"Error: OpenSCAD not found at {openscad_path}", file=sys.stderr)
        sys.exit(1)

    # Generate labels in parallel
    print(
        f"Generating {len(labels)} label(s) to {output_dir}/ using {args.workers} workers"
    )
    print("-" * 60)

    start_time = time.time()
    success_count = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        future_to_label = {
            executor.submit(
                process_single_label, label, config, output_dir, preview_dir
            ): label
            for label in labels
        }

        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_label):
            success, name, message = future.result()
            symbol = "✓" if success else "✗"
            print(f"{symbol} {message}")
            if success:
                success_count += 1

    duration = time.time() - start_time
    print("-" * 60)
    print(f"Complete: {success_count}/{len(labels)} labels in {duration:.1f}s")

    if success_count < len(labels):
        sys.exit(1)


if __name__ == "__main__":
    main()
