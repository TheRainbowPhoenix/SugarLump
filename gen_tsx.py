#!/usr/bin/env python3
"""
CLI tool to generate Tiled tilesets.

Usage:
    gen_tsx.py --input-dir /path/to/maps --output-file /path/to/tiled_maps
"""

from PIL import Image
import os
import json
import argparse

TILED_VERSION="1.9"
TILED_EDITOR_VERSION="1.9.2"


def parse_args():
    parser = argparse.ArgumentParser(description="Generate TSX tileset files from AMapInfo.json")
    parser.add_argument(
        '--input-dir', '-i', required=True,
        help='Directory containing AMapInfo.json and Tileset_*.png files'
    )
    parser.add_argument(
        '--output-dir', '-o', default=None,
        help='Directory to write .tsx files (defaults to input directory)'
    )
    return parser.parse_args()

def main():
    args = parse_args()
    input_dir = args.input_dir
    output_dir = args.output_dir or input_dir

    # Load maps info
    amap_path = os.path.join(input_dir, 'AMapInfo.json')
    with open(amap_path, 'r', encoding='utf-8') as f:
        amap = json.load(f)
    maps = amap.get('maps', [])

    os.makedirs(output_dir, exist_ok=True)

    for m in maps:
        name = m['name']
        tilecount = m['id_count']
        png_filename = f"Tileset_{name}.png"
        png_path = os.path.join(input_dir, png_filename)
        # Read image dimensions
        with Image.open(png_path) as img:
            width, height = img.size

        columns = width // 16

        # Compute relative path from TSX file to PNG
        tsx_path = os.path.join(output_dir, f"Tileset_{name}.tsx")
        rel_path = os.path.relpath(png_path, start=os.path.dirname(tsx_path)).replace("\\", "/")

        # Generate XML content
        content = f'''<?xml version="1.0" encoding="UTF-8"?>
<tileset version="{TILED_VERSION}" tiledversion="{TILED_EDITOR_VERSION}" name="Tileset_{name}" tilewidth="16" tileheight="16" tilecount="{tilecount}" columns="{columns}">
 <image source="{rel_path}" width="{width}" height="{height}"/>
</tileset>
'''
        with open(tsx_path, 'w', encoding='utf-8') as tsx_file:
            tsx_file.write(content)
        print(f"Generated {tsx_path}")

if __name__ == "__main__":
    main()
