#!/usr/bin/env python3
"""Build a 64MB MBR+FAT32 disk image of overlay files (8.3 names + RUN.HC)."""
from __future__ import annotations

import struct
import sys
from pathlib import Path

ROOT = Path("/workspace/temple-of-hermes")
sys.path.insert(0, str(ROOT / "scripts"))
from build_iso import overlay_files  # noqa: E402

BPS = 512
SPC = 1
RESERVED = 32
NFATS = 2
MEDIA = 0xF8
PART_LBA = 63
TOTAL_SECTS = 131072  # 64 MiB
PART_SECTS = TOTAL_SECTS - PART_LBA
BACKUP_BOOT = 6
FSINFO_SEC = 1
ROOT_CLUS = 2
EOC = 0x0FFFFFFF


def _83(name: str) -> bytes:
    if "." in name:
        stem, ext = name.upper().split(".", 1)
    else:
        stem, ext = name.upper(), ""
    if len(stem) > 8 or len(ext) > 3 or not stem:
        raise ValueError(f"bad 8.3 name {name!r}")
    return stem.ljust(8).encode("ascii") + ext.ljust(3).encode("ascii")


def _fat_sectors() -> int:
    data_and_fat = PART_SECTS - RESERVED
    # fat_sec * 130 >= data_and_fat + 2
    return (data_and_fat + 2 + 129) // 130


FAT_SECTS = _fat_sectors()
DATA_SECTS = PART_SECTS - RESERVED - NFATS * FAT_SECTS
CLUSTERS = DATA_SECTS // SPC


def make_run_hc(items: list[tuple[str, bytes]], src_drv: str = "D") -> bytes:
    lines = [
        f"// Copy overlay files from {src_drv}: 8.3 names onto C:.\n",
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
        src = f"{src_drv}:/F{i:02d}.BIN"
        lines.append(f'Copy("{src}","{dest}");\n')
        lines.append(f'Del("{dest}.Z");\n')
    lines.append('FileWrite("C:/Tmp/HERMES_OVL_DONE","ok",2);\n')
    lines.append('"OVERLAY DONE\\n";\n')
    return "".join(lines).encode("ascii")


def _boot_sector() -> bytes:
    b = bytearray(BPS)
    b[0:3] = b"\xeb\x58\x90"
    b[3:11] = b"MSDOS5.0"
    struct.pack_into("<H", b, 11, BPS)
    b[13] = SPC
    struct.pack_into("<H", b, 14, RESERVED)
    b[16] = NFATS
    struct.pack_into("<H", b, 17, 0)  # root entries
    struct.pack_into("<H", b, 19, 0)  # total 16
    b[21] = MEDIA
    struct.pack_into("<H", b, 22, 0)  # fat sz 16
    struct.pack_into("<H", b, 24, 63)  # spt
    struct.pack_into("<H", b, 26, 16)  # heads
    struct.pack_into("<I", b, 28, PART_LBA)  # hidden
    struct.pack_into("<I", b, 32, PART_SECTS)
    struct.pack_into("<I", b, 36, FAT_SECTS)
    struct.pack_into("<H", b, 40, 0)  # ext flags
    struct.pack_into("<H", b, 42, 0)  # version
    struct.pack_into("<I", b, 44, ROOT_CLUS)
    struct.pack_into("<H", b, 48, FSINFO_SEC)
    struct.pack_into("<H", b, 50, BACKUP_BOOT)
    b[64] = 0x80
    b[65] = 0
    b[66] = 0x29
    struct.pack_into("<I", b, 67, 0x534D5248)
    b[71:82] = b"HERMESOVL  "
    b[82:90] = b"FAT32   "
    b[510] = 0x55
    b[511] = 0xAA
    return bytes(b)


def _fsinfo(free_count: int, next_free: int) -> bytes:
    b = bytearray(BPS)
    struct.pack_into("<I", b, 0, 0x41615252)
    struct.pack_into("<I", b, 484, 0x61417272)
    struct.pack_into("<I", b, 488, free_count)
    struct.pack_into("<I", b, 492, next_free)
    struct.pack_into("<I", b, 508, 0xAA550000)
    return bytes(b)


def _mbr() -> bytes:
    b = bytearray(BPS)
    # partition 0: FAT32 LBA, start PART_LBA, size PART_SECTS
    # CHS dummy
    p = 446
    b[p] = 0x80
    b[p + 1] = 1
    b[p + 2] = 1
    b[p + 3] = 0
    b[p + 4] = 0x0C
    b[p + 5] = 0xFE
    b[p + 6] = 0xFF
    b[p + 7] = 0xFF
    struct.pack_into("<I", b, p + 8, PART_LBA)
    struct.pack_into("<I", b, p + 12, PART_SECTS)
    b[510] = 0x55
    b[511] = 0xAA
    return bytes(b)


def build(files: list[tuple[str, bytes]]) -> bytes:
    img = bytearray(TOTAL_SECTS * BPS)
    img[0:BPS] = _mbr()
    boot = _boot_sector()
    part = PART_LBA * BPS
    img[part : part + BPS] = boot
    img[part + BACKUP_BOOT * BPS : part + BACKUP_BOOT * BPS + BPS] = boot

    fat = bytearray(FAT_SECTS * BPS)
    def fat_set(cl: int, val: int) -> None:
        struct.pack_into("<I", fat, cl * 4, val)

    fat_set(0, 0x0FFFFFF8)
    fat_set(1, EOC)

    next_cl = ROOT_CLUS
    # Pre-size root dir to enough clusters
    n_ents = 1 + len(files)  # volume label + files
    root_bytes = max(BPS * SPC, ((n_ents * 32 + BPS * SPC - 1) // (BPS * SPC)) * BPS * SPC)
    root_nclus = root_bytes // (BPS * SPC)
    root_start = next_cl
    root = bytearray(root_bytes)
    # volume label
    root[0:11] = b"HERMESOVL  "
    root[11] = 0x08
    for i in range(root_nclus):
        cl = root_start + i
        fat_set(cl, EOC if i == root_nclus - 1 else cl + 1)
    next_cl = root_start + root_nclus

    dir_index = 1
    for name83, data in files:
        nclus = (len(data) + BPS * SPC - 1) // (BPS * SPC) if data else 0
        first = 0
        if nclus:
            first = next_cl
            for i in range(nclus):
                cl = first + i
                fat_set(cl, EOC if i == nclus - 1 else cl + 1)
            data_off = part + (RESERVED + NFATS * FAT_SECTS) * BPS + (first - 2) * SPC * BPS
            img[data_off : data_off + len(data)] = data
            next_cl = first + nclus
        ent = bytearray(32)
        ent[0:11] = _83(name83)
        ent[11] = 0x20
        struct.pack_into("<H", ent, 20, (first >> 16) & 0xFFFF)
        struct.pack_into("<H", ent, 26, first & 0xFFFF)
        struct.pack_into("<I", ent, 28, len(data))
        off = dir_index * 32
        root[off : off + 32] = ent
        dir_index += 1

    # write root dir clusters
    data_base = part + (RESERVED + NFATS * FAT_SECTS) * BPS
    root_off = data_base + (root_start - 2) * SPC * BPS
    img[root_off : root_off + len(root)] = root

    # FATs
    fat_off = part + RESERVED * BPS
    img[fat_off : fat_off + len(fat)] = fat
    img[fat_off + len(fat) : fat_off + 2 * len(fat)] = fat

    free = CLUSTERS - (next_cl - 2)
    fsinfo = _fsinfo(free, next_cl)
    img[part + FSINFO_SEC * BPS : part + FSINFO_SEC * BPS + BPS] = fsinfo
    print(f"clusters={CLUSTERS} fat_sects={FAT_SECTS} next_cl={next_cl} free={free}")
    return bytes(img)


def main() -> int:
    items = overlay_files()
    files: list[tuple[str, bytes]] = []
    run = make_run_hc(items, "D")
    files.append(("RUN.HC", run))
    for i, (dest, data) in enumerate(items, start=1):
        files.append((f"F{i:02d}.BIN", data))
        print(f"  F{i:02d}.BIN -> {dest} ({len(data)} bytes)")
    img = build(files)
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "run" / "overlay-fat32.img"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(img)
    print(f"wrote {out} ({len(img)} bytes, {len(files)} files, RUN.HC {len(run)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
