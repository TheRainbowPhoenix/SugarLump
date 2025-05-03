#!/usr/bin/env python3
"""
CLI tool to merge JSON map layers and AMapInfo into a TMX file for Tiled.

Merge JSON map layers and AMapInfo into a single TMX file for Tiled Editor.
Assumes all JSON and PNG/TSX files are in the current directory.

Usage:
    merger.py --input-dir /path/to/maps --output-file /path/to/merged_map.tmx
"""
import os
import json
import glob
import argparse

# Constants for Tiled map
TILE_WIDTH = 16
TILE_HEIGHT = 16
TILED_VERSION = "1.9"
TILED_EDITOR_VERSION = "1.9.2"

def parse_args():
    parser = argparse.ArgumentParser(
        description="Merge JSON layers and AMapInfo into a Tiled TMX map")
    parser.add_argument(
        '--input-dir', '-i', required=True,
        help='Directory containing AMapInfo.json, Layer *.json, Tileset_*.tsx files')
    parser.add_argument(
        '--output-file', '-o', required=True,
        help='Path to write the generated TMX file')
    return parser.parse_args()

def load_amap(input_dir):
    path = os.path.join(input_dir, 'AMapInfo.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('maps', [])

def find_layer_files(input_dir):
    pattern = os.path.join(input_dir, 'Layer *.json')
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No Layer *.json files in {input_dir}")
    return files

def determine_dimensions(layer_files):
    for lf in layer_files:
        with open(lf, encoding='utf-8') as f:
            d = json.load(f)
        if d.get('type') == 'Tile':
            return d['width'], d['height']
    raise ValueError("No Tile layer found to determine map dimensions")

def build_tilesets(maps):
    # returns list of (firstgid, source)
    tilesets = []
    for m in maps:
        name = m['name']
        firstgid = m['start_id'] + 1
        source = f"Tileset_{name}.tsx"
        tilesets.append((firstgid, source))
    return tilesets

def merge_to_tmx(maps, tilesets, layer_files, width, height):
    lines = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        f'<map version="{TILED_VERSION}" tiledversion="{TILED_EDITOR_VERSION}" '
        f'orientation="orthogonal" renderorder="right-down" '
        f'width="{width}" height="{height}" '
        f'tilewidth="{TILE_WIDTH}" tileheight="{TILE_HEIGHT}" '
        f'infinite="0" nextlayerid="{len(layer_files)+1}" nextobjectid="1">'
    )
    # Tilesets
    for gid, src in tilesets:
        lines.append(f'  <tileset firstgid="{gid}" source="{src}"/>')

    layer_id = 1
    object_id = 1
    # Process each layer file
    for lf in layer_files:
        with open(lf, encoding='utf-8') as f:
            data = json.load(f)
        ltype = data.get('type')
        name = data.get('layer') or data.get('layer_name') or os.path.splitext(os.path.basename(lf))[0]

        if ltype == 'Tile' and 'tiles' in data:
            tiles = data['tiles']
            # Convert empty tiles (65535) to 0, else increment by 1
            tiles = [0 if t >= 65535 else t+1 for t in tiles]
            w, h = data['width'], data['height']
            
            # Hide Collision layer by default
            extra_props = ' visible="0"' if "Collision" in name else ""

            lines.append(f'  <layer id="{layer_id}" name="{name}" width="{w}" height="{h}"{extra_props}>')
            lines.append('    <data encoding="csv">')
            for y in range(h):
                row = tiles[y*w:(y+1)*w]
                csv_line = ','.join(str(v) for v in row)
                if y < h-1:
                    csv_line += ','
                lines.append('      ' + csv_line)
            lines.append('    </data>')
            lines.append('  </layer>')
            layer_id += 1

        elif ltype == 'Object' and 'objects' in data:
            lines.append(f'  <objectgroup id="{layer_id}" name="{name}">')
            for obj in data['objects']:
                x = int(obj.get('x', 0))
                y = int(obj.get('y', 0))
                w = int(obj.get('w', 0))
                h = int(obj.get('h', 0))
                r = obj.get('resource', '')
                t = obj.get('type', '')
                lines.append(
                    f'    <object id="{object_id}" name="{r}" class="{t}" '
                    f'x="{x}" y="{y}" width="{w}" height="{h}">'
                )
                extra = obj.get('extra', {})
                if extra:
                    lines.append('      <properties>')
                    for k, v in extra.items():
                        try:
                            float(v)
                            ptype = 'float'
                        except:
                            ptype = None
                        if ptype:
                            lines.append(f'        <property name="{k}" type="{ptype}" value="{v}"/>')
                        else:
                            lines.append(f'        <property name="{k}" value="{v}"/>')
                    lines.append('      </properties>')
                lines.append('    </object>')
                object_id += 1
            lines.append('  </objectgroup>')
            layer_id += 1

    lines.append('</map>')
    return '\n'.join(lines)


def main():
    args = parse_args()
    inp = args.input_dir
    out = args.output_file
    maps = load_amap(inp)
    layer_files = find_layer_files(inp)
    width, height = determine_dimensions(layer_files)
    tilesets = build_tilesets(maps)
    tmx_content = merge_to_tmx(maps, tilesets, layer_files, width, height)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, 'w', encoding='utf-8') as f:
        f.write(tmx_content)
    print(f"Written TMX file: {out}")


if __name__ == '__main__':
    main()

