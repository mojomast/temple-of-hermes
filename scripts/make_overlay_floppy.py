#!/usr/bin/env python3
"""Build a 1.44MB FAT12 floppy with 8.3 names plus RUN.HC that copies onto C:."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path("/workspace/temple-of-hermes")
sys.path.insert(0, str(ROOT / "scripts"))
from build_iso import overlay_files  # noqa: E402

FLOPPY_BYTES = 1474560
BPS = 512
SPC = 1  # sectors per cluster
RESERVED = 1
NFATS = 2
ROOT_ENT = 224
TOTAL = 2880
MEDIA = 0xF0
FAT_SECTS = 9
SPT = 18
HEADS = 2
ROOT_SECTS = (ROOT_ENT * 32 + BPS - 1) // BPS  # 14
DATA_START = RESERVED + NFATS * FAT_SECTS + ROOT_SECTS  # 33


def _fat12_set(fat: bytearray, cluster: int, value: int) -> None:
    offset = (cluster * 3) // 2
    if cluster & 1:
        fat[offset] = (fat[offset] & 0x0F) | ((value << 4) & 0xF0)
        fat[offset + 1] = (value >> 4) & 0xFF
    else:
        fat[offset] = value & 0xFF
        fat[offset + 1] = (fat[offset + 1] & 0xF0) | ((value >> 8) & 0x0F)


def _83(name: str) -> bytes:
    if "." in name:
        stem, ext = name.upper().split(".", 1)
    else:
        stem, ext = name.upper(), ""
    if len(stem) > 8 or len(ext) > 3 or not stem:
        raise ValueError(f"bad 8.3 name {name!r}")
    return stem.ljust(8).encode("ascii") + ext.ljust(3).encode("ascii")


def build_floppy(files: list[tuple[str, bytes]]) -> bytes:
    img = bytearray(FLOPPY_BYTES)
    # Boot sector / BPB
    bpb = bytearray(BPS)
    bpb[0:3] = b"\xeb\x3c\x90"
    bpb[3:11] = b"MSDOS5.0"
    struct.pack_into("<H", bpb, 11, BPS)
    bpb[13] = SPC
    struct.pack_into("<H", bpb, 14, RESERVED)
    bpb[16] = NFATS
    struct.pack_into("<H", bpb, 17, ROOT_ENT)
    struct.pack_into("<H", bpb, 19, TOTAL)
    bpb[21] = MEDIA
    struct.pack_into("<H", bpb, 22, FAT_SECTS)
    struct.pack_into("<H", bpb, 24, SPT)
    struct.pack_into("<H", bpb, 26, HEADS)
    struct.pack_into("<I", bpb, 28, 0)  # hidden
    struct.pack_into("<I", bpb, 32, 0)  # total sectors 32
    bpb[36] = 0  # drive number
    bpb[37] = 0
    bpb[38] = 0x29  # ext boot sig
    struct.pack_into("<I", bpb, 39, 0x534D5248)  # serial 'HRMS'
    bpb[43:54] = b"HERMESOVL  "
    bpb[54:62] = b"FAT12   "
    bpb[510] = 0x55
    bpb[511] = 0xAA
    img[0:BPS] = bpb

    fat = bytearray(FAT_SECTS * BPS)
    _fat12_set(fat, 0, 0xFF0)
    _fat12_set(fat, 1, 0xFFF)

    root = bytearray(ROOT_SECTS * BPS)
    # volume label entry
    root[0:11] = b"HERMESOVL  "
    root[11] = 0x08

    next_cluster = 2
    dir_index = 1  # 0 is volume label

    for name83, data in files:
        nclus = max(1, (len(data) + BPS * SPC - 1) // (BPS * SPC)) if data else 1
        if not data:
            nclus = 1  # empty file still gets a cluster (or 0). Use cluster 0 + size 0.
        first = next_cluster
        if not data:
            first = 0
            nclus = 0
        # chain
        for i in range(nclus):
            cl = first + i
            val = 0xFFF if i == nclus - 1 else cl + 1
            _fat12_set(fat, cl, val)
        if nclus:
            start = (DATA_START + (first - 2) * SPC) * BPS
            img[start : start + len(data)] = data
            next_cluster = first + nclus

        ent = bytearray(32)
        ent[0:11] = _83(name83)
        ent[11] = 0x20
        struct.pack_into("<H", ent, 26, first)
        struct.pack_into("<I", ent, 28, len(data))
        off = dir_index * 32
        if off + 32 > len(root):
            raise RuntimeError("root directory full")
        root[off : off + 32] = ent
        dir_index += 1

    fat_off = RESERVED * BPS
    img[fat_off : fat_off + len(fat)] = fat
    img[fat_off + len(fat) : fat_off + 2 * len(fat)] = fat
    root_off = (RESERVED + NFATS * FAT_SECTS) * BPS
    img[root_off : root_off + len(root)] = root
    return bytes(img)


def make_run_hc(items: list[tuple[str, bytes]]) -> str:
    lines = [
        "// Copy overlay files from the 8.3 floppy names onto C:.\n",
        'DirMk("C:/Adam");\n',
        'DirMk("C:/Adam/Hermes");\n',
        'DirMk("C:/Adam/Opt");\n',
        'DirMk("C:/Adam/Opt/Boot");\n',
        'DirMk("C:/Kernel");\n',
        'DirMk("C:/Kernel/BlkDev");\n',
        'DirMk("C:/Misc");\n',
        'DirMk("C:/Doc");\n',
        'DirMk("C:/Home");\n',
        'DirMk("C:/Tmp");\n',
    ]
    for i, (dest, _data) in enumerate(items, start=1):
        src = f"A:/F{i:02d}.BIN"
        # Escape quotes not needed; dest has none.
        lines.append(f'Copy("{src}","{dest}");\n')
        lines.append(f'Del("{dest}.Z");\n')
    lines.append('FileWrite("C:/Tmp/HERMES_OVL_DONE","ok",2);\n')
    lines.append('"OVERLAY DONE\\n";\n')
    return "".join(lines)


def main() -> int:
    items = overlay_files()
    files: list[tuple[str, bytes]] = []
    run = make_run_hc(items).encode("ascii")
    files.append(("RUN.HC", run))
    for i, (dest, data) in enumerate(items, start=1):
        files.append((f"F{i:02d}.BIN", data))
        print(f"  F{i:02d}.BIN -> {dest} ({len(data)} bytes)")
    img = build_floppy(files)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "run" / "overlay.img"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img)
    print(f"wrote {out} ({len(img)} bytes, {len(files)} entries, RUN.HC {len(run)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
