import os
import struct
import json
from dataclasses import dataclass
from typing import List, Any
from PIL import Image

# --- helper routines ---

def read_u8(buf: bytes, pos: int):
    return buf[pos], pos+1

def read_u16(buf: bytes, pos: int):
    return struct.unpack_from("<H", buf, pos)[0], pos+2

def read_u32(buf: bytes, pos: int):
    return struct.unpack_from("<I", buf, pos)[0], pos+4

def read_f32(buf: bytes, pos: int):
    return struct.unpack_from("<f", buf, pos)[0], pos+4

def read_lstr(buf: bytes, pos: int):
    # LStr = [u8 len][len bytes of UTF-8]
    length, pos = read_u8(buf, pos)
    s = buf[pos:pos+length].decode("utf-8")
    return s, pos+length

# --- Fixers ---

def normalize_tiles(tiles, width, height):
    """
    Convert column-major tiles (x then y) into row-major (y then x).
    """
    new_tiles = []
    for y in range(height):
        for x in range(width):
            # original index in column-major = x*height + y
            original_idx = x * height + y
            new_tiles.append(tiles[original_idx])
    return new_tiles

# --- parsers ---

def parse_mapinfo(body: bytes) -> Any:
    pos = 0
    s1, pos = read_u8(body, pos)
    s2, pos = read_u8(body, pos)
    s3, pos = read_u8(body, pos)

    names = []
    for _ in range(s2):
        name, pos = read_lstr(body, pos)
        start_id, pos   = read_u16(body, pos)
        id_count, pos   = read_u16(body, pos)
        names.append({"name": name, "start_id": start_id, "id_count": id_count})

    return {"s1": s1, "count": s2, "s3": s3, "maps": names}


def parse_layerdata(body: bytes) -> Any:
    pos = 0
    layer_type, pos = read_lstr(body, pos)
    out = {"type": layer_type}

    if layer_type == "Tile":
        layer_name, pos = read_lstr(body, pos)
        prop_count, pos = read_u16(body, pos)
        props = {}
        for _ in range(prop_count):
            k, pos = read_lstr(body, pos)
            v, pos = read_lstr(body, pos)
            props[k] = v

        e1, pos = read_u32(body, pos)   # unused in C
        width, pos = read_u16(body, pos)
        height, pos  = read_u16(body, pos)

        # tile IDs
        count = width * height
        tiles = list(struct.unpack_from(f"<{count}H", body, pos))
        pos += 2 * count

        # collision IDs only if there’s still data
        cols = []
        if pos + 2 <= len(body):
            colcount = count
            cols = list(struct.unpack_from(f"<{colcount}H", body, pos))
            pos += 2 * colcount

        out.update({
            "layer": layer_name,
            "props": props,
            "width": width,
            "height": height,
            "tiles": normalize_tiles(tiles, width, height),
            "collision": cols or None
        })

    elif layer_type == "Object":
        layer_name, pos = read_lstr(body, pos)
        out["layer_name"] = layer_name

        group_count, pos = read_u16(body, pos)
        groups = []
        if group_count > 0:
            pass # TODO: is that a real use case ??
            # for _ in range(group_count):
            #     k, pos = read_lstr(body, pos)
            #     v, pos = read_lstr(body, pos)
            #     groups.append({"key": k, "value": v})
        out["groups"] = groups

        obj_count, pos = read_u16(body, pos)
        objects = []
        for _ in range(obj_count):
            type_name, pos = read_lstr(body, pos)
            res_key, pos = read_lstr(body, pos)
            x, pos = read_f32(body, pos)
            y, pos = read_f32(body, pos)
            w, pos = read_f32(body, pos)
            h, pos = read_f32(body, pos)
            frame, pos = read_u16(body, pos)
            if frame > 99:
                frame -= 1
            # 4) extra data - read KV values
            extra_count, pos = read_u16(body, pos)
            extra = {}

            if extra_count > 0:
                for _ in range(extra_count):
                    key_name, pos = read_lstr(body, pos)
                    key_val, pos = read_lstr(body, pos)
                    extra[key_name] = key_val
                

            objects.append({
                "type": type_name,
                "resource": res_key,
                "x": x, "y": y,
                "w": w, "h": h,
                "frame": frame,
                "extra": extra
            })
        out["objects"] = objects

    else:
        out["note"] = f"Unsupported layer type: {layer_type}"

    return out

def parse_rce(body: bytes) -> Any:
    pos = 0
    ray_count, pos = read_u32(body, pos)
    rays = []
    for _ in range(ray_count):
        x, pos = read_u32(body, pos)
        y, pos = read_u32(body, pos)
        w, pos = read_u32(body, pos)
        h, pos = read_u32(body, pos)
        flags, pos = read_u32(body, pos)
        rays.append({"x":x,"y":y,"w":w,"h":h,"flags":flags})

    col_count, pos = read_u32(body, pos)
    row_count, pos = read_u32(body, pos)
    # skip unk0, unk1
    pos += 8

    grid = []
    # TODO: this is not complete
    for c in range(col_count):
        col = []
        for r in range(row_count):
            seg, pos = read_u32(body, pos)
            # segs = []
            # for _ in range(seg_count):
            #     sid, pos = read_u32(body, pos)
            #     segs.append(sid)
            col.append(seg)
        grid.append(col)

    return {"rays": rays, "cols": col_count, "rows": row_count, "grid": grid}


# --- Decompression routines for images ---

def decompress_type8(src: bytes, width: int, height: int) -> bytes:
    out = bytearray(width * height * 4)
    y = height - 1
    i = 0
    src_size = len(src)
    while i + 2 <= src_size and y >= 0:
        run_len = src[i] | (src[i+1] << 8); i += 2
        if run_len == 0:
            y -= 1
            continue
        if i + 2 > src_size: break
        x_off = src[i] | (src[i+1] << 8); i += 2
        for k in range(run_len):
            if i + 4 > src_size: break
            r, g, b, a = src[i:i+4]; i += 4
            x = x_off + k
            if 0 <= x < width and 0 <= y < height:
                idx = (y*width + x)*4
                out[idx:idx+4] = (r, g, b, a)
    return bytes(out)

def decompress_type9(src: bytes, width: int, height: int) -> bytes:
    out = bytearray(width * height * 4)
    src_pos = 0; x = 0; src_size = len(src)
    while src_pos+2 <= src_size and x < width:
        run_len = struct.unpack_from("<H", src, src_pos)[0]; src_pos += 2
        if run_len == 0:
            x += 1
            continue
        if src_pos+2 > src_size: break
        y_start = struct.unpack_from("<H", src, src_pos)[0]; src_pos += 2
        for k in range(run_len):
            if src_pos+4 > src_size: break
            r, g, b, a = struct.unpack_from("4B", src, src_pos)
            src_pos += 4
            y = height - (y_start + k) - 1
            if 0 <= x < width and 0 <= y < height:
                idx = (y*width + x)*4
                out[idx:idx+4] = (r, g, b, a)
    return bytes(out)

# --- SLF Entry and File definitions ---

@dataclass
class SLFEntry:
    name: str
    offset: int

    @classmethod
    def from_bytes(cls, data: bytes, pos: int):
        name_len = data[pos]; pos += 1
        name = data[pos:pos+name_len].decode('utf-8'); pos += name_len
        offset, _ = struct.unpack_from("<II", data, pos); pos += 8
        return cls(name, offset), pos

class SLFFile:
    def __init__(self, entries: List[SLFEntry], data: bytes):
        self.entries, self.data = entries, data

    @classmethod
    def load(cls, path: str):
        with open(path, "rb") as f:
            raw = f.read()
        
        if raw[:16] != b"SugarLumpFile100":
            raise ValueError("Not SLF")
        count = struct.unpack_from("<I", raw, 16)[0]
        entries = []
        pos = 20
        for _ in range(count):
            e, pos = SLFEntry.from_bytes(raw, pos)
            entries.append(e)
        return cls(entries, raw)
# --- Main extraction routine ---

def extract_slf(path: str, out_dir: str):
    slf = SLFFile.load(path)
    data = slf.data
    # sort by offset so we know each lump's size
    entries = sorted(slf.entries, key=lambda e: e.offset)
    file_size = len(data)

    os.makedirs(out_dir, exist_ok=True)
    for idx, e in enumerate(entries):
        start = e.offset
        end   = entries[idx+1].offset if idx+1 < len(entries) else file_size
        lump  = data[start:end]
        header = lump[:10]
        body   = lump[10:]

        name = e.name.replace("|","_")
        outp = os.path.join(out_dir, name)

        # IMAGE
        if header == b"IMAGE00000":
            comp = body[0]
            stat1, stat2 = struct.unpack_from("<II", body, 1)
            field1,field2, field3,field4 = struct.unpack_from("<4I", body, 9)
            size = struct.unpack_from("<I", body, 25)[0]
            pix = body[29:29+size]
            w,h = field3, field4

            if comp==1:
                rgba = pix
            elif comp==8:
                rgba = decompress_type8(pix,w,h)
            elif comp==9:
                rgba = decompress_type9(pix,w,h)
            else:
                print(f"!!! Unknown compression mode : {comp}")
                continue

            img = Image.frombytes("RGBA",(w,h),rgba).transpose(Image.FLIP_TOP_BOTTOM)
            img = img.transpose(Image.FLIP_TOP_BOTTOM)
            img.save(outp+".png")
            continue

        # MAPINFO000
        if header == b"MAPINFO000":
            info = parse_mapinfo(body)
            with open(outp+".json","w") as o:
                json.dump(info, o, indent=2)
            continue

        # LAYERDATAxx
        if header.startswith(b"LAYERDATA"):
            info = parse_layerdata(body)
            with open(outp+".json","w") as o:
                json.dump(info, o, indent=2)
            continue

        # RCEDATA000
        if header == b"RCEDATA000":
            info = parse_rce(body)
            with open(outp+".json","w") as o:
                json.dump(info, o, indent=2)
            continue

        # otherwise dump raw
        with open(outp+".bin","wb") as o:
            o.write(body)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("slf", help="SLF file path")
    p.add_argument("out", help="Output directory")
    args = p.parse_args()
    extract_slf(args.slf, args.out)
    # extract_slf("Games/AdventureMode/Chapter C/Maps/Debug/Sample/MapData.slf", "ExtOut")
    # extract_slf("Games/AdventureMode/Chapter C/Maps/Village/VillageA/MapData.slf", "VillageA")

    
print("Extraction complete.")
