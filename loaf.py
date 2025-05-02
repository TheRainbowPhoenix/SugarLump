import os
import struct
from dataclasses import dataclass
from typing import List
from PIL import Image


def decompress_type8(src: bytes, width: int, height: int) -> bytes:
    out = bytearray(width * height * 4)
    y = height - 1
    i = 0
    src_size = len(src)

    while i + 2 <= src_size and y >= 0:
        run_len = src[i] | (src[i+1] << 8)
        i += 2
        if run_len == 0:
            y -= 1
            continue
        if i + 2 > src_size:
            break
        x_off = src[i] | (src[i+1] << 8)
        i += 2
        for k in range(run_len):
            if i + 4 > src_size:
                break
            r, g, b, a = src[i:i+4]
            i += 4
            x = x_off + k
            if 0 <= x < width and 0 <= y < height:
                idx = (y * width + x) * 4
                out[idx    ] = r
                out[idx + 1] = g
                out[idx + 2] = b
                out[idx + 3] = a
    return bytes(out)

def decompress_type9(src: bytes, width: int, height: int) -> bytes:
    """
    Decompress 'type 9' RLE-like vertical-run format:
    Records:
      [run_len:2][y_start:2] then run_len pixels (4 bytes each).
      A run_len of 0 marks end-of-column (x += 1).
    Pixels are placed at (x, y) where y = height - (y_start + k) - 1
    """
    out = bytearray(width * height * 4)
    src_pos = 0
    x = 0
    src_size = len(src)

    while src_pos + 2 <= src_size and x < width:
        run_len = src[src_pos] | (src[src_pos+1] << 8)
        src_pos += 2
        if run_len == 0:
            # Move to next column
            x += 1
            continue

        if src_pos + 2 > src_size:
            break
        y_start = src[src_pos] | (src[src_pos+1] << 8)
        src_pos += 2

        # Copy run_len pixels vertically
        for k in range(run_len):
            if src_pos + 4 > src_size:
                break
            r, g, b, a = src[src_pos:src_pos+4]
            src_pos += 4
            y = height - (y_start + k) - 1
            if 0 <= x < width and 0 <= y < height:
                idx = (y * width + x) * 4
                out[idx    ] = r
                out[idx + 1] = g
                out[idx + 2] = b
                out[idx + 3] = a

    return bytes(out)

@dataclass
class SLFEntry:
    name: str
    offset: int

    @classmethod
    def from_bytes(cls, data: bytes, pos: int):
        name_len = data[pos]
        pos += 1
        name = data[pos:pos+name_len].decode("utf-8")
        pos += name_len
        offset, _ = struct.unpack_from("<II", data, pos)
        pos += 8
        return cls(name, offset), pos

@dataclass
class SLFFile:
    entries: List[SLFEntry]

    @classmethod
    def load(cls, path: str):
        with open(path, "rb") as f:
            data = f.read()
        # Verify magic
        if data[:16] != b"SugarLumpFile100":
            raise ValueError("Not a SLF file")
        count = struct.unpack_from("<I", data, 16)[0]
        entries = []
        pos = 20
        for _ in range(count):
            e, pos = SLFEntry.from_bytes(data, pos)
            entries.append(e)
        return cls(entries)

    def extract_images(self, slf_path: str, out_dir: str):
        os.makedirs(out_dir, exist_ok=True)
        with open(slf_path, "rb") as f:
            for e in self.entries:
                # if not e.name.startswith("IMAGE"):
                #     continue
                f.seek(e.offset)
                hdr = f.read(10)
                if not hdr.startswith(b"IMAGE"):
                    print(f"[!] {e.name}: bad header {hdr!r}")
                    continue

                # parse internal IMAGE header
                comp_type = struct.unpack("<B", f.read(1))[0]
                stat1, stat2 = struct.unpack("<II", f.read(8))

                field1, field2, field3, field4 = struct.unpack("<4I", f.read(16))
                data_size = struct.unpack("<I", f.read(4))[0]
                
                
                width = field3
                height = field4

                # now read the raw pixel data
                pixel_data = f.read(data_size)

                # write it out
                safe_name = e.name.replace("|", "_")
                

                try:
                    img_path = os.path.join(out_dir, f"{safe_name}.png")

                    if comp_type == 1:
                        img = Image.frombytes("RGBA", (width, height), pixel_data)
                        img = img.transpose(Image.FLIP_TOP_BOTTOM)
                        img.save(img_path)
                        print(f"Saved {img_path} ({width}x{height})")
                        
                    elif comp_type == 8:
                        rgba = decompress_type8(pixel_data, width, height)
                        img = Image.frombytes("RGBA", (width, height), rgba)
                        img = img.transpose(Image.FLIP_TOP_BOTTOM)

                        img.save(img_path)
                        print(f"Saved {img_path} ({width}x{height})")
                    elif comp_type == 9:
                        rgba = decompress_type9(pixel_data, width, height)
                        img = Image.frombytes("RGBA", (width, height), rgba)
                        img = img.transpose(Image.FLIP_TOP_BOTTOM)

                        img.save(img_path)
                        print(f"Saved {img_path} ({width}x{height})")
                    else:
                        print(f"Compress {comp_type}")
                except Exception as e:
                    print(e)

                    out_path = os.path.join(out_dir, f"{safe_name}.bin")
                    with open(out_path, "wb") as out:
                        print(out_path)
                        out.write(pixel_data)

                    print(f"Extracted {e.name} → {out_path} ({data_size} bytes)")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Extract all lumps from an SLF.")
    p.add_argument("slf_file", help="Path to .slf file")
    p.add_argument("-o", "--out", default="slf_extracted", help="Output directory")
    args = p.parse_args()

    slf = SLFFile.load(args.slf_file)
    # slf_file = "Games/AdventureMode/Datafiles/ElectrospriteAdventure.slf"
    slf_file = "Data/UIControls.slf"
    # out = "DATAExt/ElectrospriteAdventure"
    slf = SLFFile.load(slf_file)
    print(f"Found {len(slf.entries)} lumps, extracting IMAGE* only…")
    # for i,e in enumerate(slf.entries):
    #     print(f"  {i:3}: {e.name} @ 0x{e.offset:X} (+{e.size} bytes)")

    slf.extract_images(args.slf_file, args.out)
    # slf.extract_images(slf_file, out)
