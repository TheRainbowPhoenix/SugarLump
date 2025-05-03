#!/usr/bin/env python3
"""
Launcher script to automate the three steps for every MapData.slf under an input directory:
 1. Extract layers: python loafed.py <slf> <outdir>
 2. Generate TSX files:   python gen_tsx.py -i <outdir> -o <outdir>/Tiled
 3. Merge into TMX:       python merger.py   -i <outdir> -o <outdir>/Tiled/<MapName>.tmx

Usage:
    python run_all.py --input-dir /path/to/Maps --output-dir /path/to/Out
"""
import os
import sys
import argparse
import subprocess


def parse_args():
    p = argparse.ArgumentParser(
        description="Process all MapData.slf files under a directory"
    )
    p.add_argument('-i', '--input-dir', required=True,
                   help='Root directory containing map subfolders with MapData.slf')
    p.add_argument('-o', '--output-dir', required=True,
                   help='Directory where outputs (layers, TSX, TMX) will be generated')
    return p.parse_args()


def main():
    args = parse_args()
    input_root = os.path.abspath(args.input_dir)
    output_root = os.path.abspath(args.output_dir)

    # Locate helper scripts relative to this launcher
    script_dir = os.path.dirname(os.path.abspath(__file__))
    loafed_py = os.path.join(script_dir, 'loafed.py')
    gen_tsx_py = os.path.join(script_dir, 'gen_tsx.py')
    merger_py = os.path.join(script_dir, 'merger.py')

    if not os.path.isdir(input_root):
        print(f"Error: input directory does not exist: {input_root}")
        sys.exit(1)

    # Walk the input directory tree
    for root, dirs, files in os.walk(input_root):
        if 'MapData.slf' in files:
            slf_path = os.path.join(root, 'MapData.slf')
            # Compute relative subpath
            rel_dir = os.path.relpath(root, input_root)
            # Output directory for this map
            out_dir = os.path.join(output_root, rel_dir)
            tiled_dir = os.path.join(out_dir, 'Tiled')
            os.makedirs(tiled_dir, exist_ok=True)

            map_name = os.path.basename(root)
            tmx_path = os.path.join(tiled_dir, f"{map_name}.tmx")

            print(f"\nProcessing map: {rel_dir}")
            # 1) loafed.py
            subprocess.run([sys.executable, loafed_py, slf_path, out_dir], check=True)
            # 2) gen_tsx.py
            subprocess.run([sys.executable, gen_tsx_py, '-i', out_dir, '-o', tiled_dir], check=True)
            # 3) merger.py
            subprocess.run([sys.executable, merger_py, '-i', out_dir, '-o', tmx_path], check=True)

    print("\nAll maps processed successfully.")


if __name__ == '__main__':
    main()
