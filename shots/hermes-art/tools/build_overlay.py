#!/usr/bin/env python3
"""Build a 64 MiB MBR+FAT32 overlay holding Hermes/Art plus a HolyC copy+verify script."""
from __future__ import annotations
import json, struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SHOTS = ROOT / "shots" / "hermes-art"
OUT = SHOTS / "raw" / "hermes-art-overlay.img"
MANIFEST = SHOTS / "raw" / "overlay-manifest.json"

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
    stem, ext = (name.upper().split(".", 1) + [""])[:2] if "." in name else (name.upper(), "")
    if len(stem) > 8 or len(ext) > 3 or not stem:
        raise ValueError(f"bad 8.3 name {name!r}")
    return stem.ljust(8).encode("ascii") + ext.ljust(3).encode("ascii")


def _fat_sectors() -> int:
    return (PART_SECTS - RESERVED + 2 + 129) // 130


FAT_SECTS = _fat_sectors()
DATA_SECTS = PART_SECTS - RESERVED - NFATS * FAT_SECTS
CLUSTERS = DATA_SECTS // SPC


def _boot_sector() -> bytes:
    b = bytearray(BPS)
    b[0:3] = b"\xeb\x58\x90"
    b[3:11] = b"MSDOS5.0"
    struct.pack_into("<H", b, 11, BPS)
    b[13] = SPC
    struct.pack_into("<H", b, 14, RESERVED)
    b[16] = NFATS
    struct.pack_into("<H", b, 17, 0)
    struct.pack_into("<H", b, 19, 0)
    b[21] = MEDIA
    struct.pack_into("<H", b, 22, 0)
    struct.pack_into("<H", b, 24, 63)
    struct.pack_into("<H", b, 26, 16)
    struct.pack_into("<I", b, 28, PART_LBA)
    struct.pack_into("<I", b, 32, PART_SECTS)
    struct.pack_into("<I", b, 36, FAT_SECTS)
    struct.pack_into("<H", b, 40, 0)
    struct.pack_into("<H", b, 42, 0)
    struct.pack_into("<I", b, 44, ROOT_CLUS)
    struct.pack_into("<H", b, 48, FSINFO_SEC)
    struct.pack_into("<H", b, 50, BACKUP_BOOT)
    b[64] = 0x80
    b[65] = 0
    b[66] = 0x29
    struct.pack_into("<I", b, 67, 0x534D5248)
    b[71:82] = b"HERMESART  "
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
    img[part:part + BPS] = boot
    img[part + BACKUP_BOOT * BPS:part + BACKUP_BOOT * BPS + BPS] = boot

    fat = bytearray(FAT_SECTS * BPS)

    def fat_set(cl: int, val: int) -> None:
        struct.pack_into("<I", fat, cl * 4, val)

    fat_set(0, 0x0FFFFFF8)
    fat_set(1, EOC)

    next_cl = ROOT_CLUS
    n_ents = 1 + len(files)
    root_bytes = max(BPS * SPC, ((n_ents * 32 + BPS * SPC - 1) // (BPS * SPC)) * BPS * SPC)
    root_nclus = root_bytes // (BPS * SPC)
    root_start = next_cl
    root = bytearray(root_bytes)
    root[0:11] = b"HERMESART  "
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
            img[data_off:data_off + len(data)] = data
            next_cl = first + nclus
        ent = bytearray(32)
        ent[0:11] = _83(name83)
        ent[11] = 0x20
        struct.pack_into("<H", ent, 20, (first >> 16) & 0xFFFF)
        struct.pack_into("<H", ent, 26, first & 0xFFFF)
        struct.pack_into("<I", ent, 28, len(data))
        off = dir_index * 32
        root[off:off + 32] = ent
        dir_index += 1

    data_base = part + (RESERVED + NFATS * FAT_SECTS) * BPS
    root_off = data_base + (root_start - 2) * SPC * BPS
    img[root_off:root_off + len(root)] = root

    fat_off = part + RESERVED * BPS
    img[fat_off:fat_off + len(fat)] = fat
    img[fat_off + len(fat):fat_off + 2 * len(fat)] = fat

    free = CLUSTERS - (next_cl - 2)
    fsinfo = _fsinfo(free, next_cl)
    img[part + FSINFO_SEC * BPS:part + FSINFO_SEC * BPS + BPS] = fsinfo
    return bytes(img)


def hc_str(s: str) -> str:
    return '"' + s + '"'


def main() -> int:
    art = ROOT / "Hermes" / "Art"
    files = sorted(p for p in art.rglob("*") if p.is_file())
    by_rel = {p.relative_to(art).as_posix(): p for p in files}
    required = [
        "Wallpaper/toh-temple-night.GR",
        "Splash/toh-boot-splash.GR",
        "Icons/32/hermes-chat.GR",
    ]
    for rel in required:
        if rel not in by_rel:
            raise SystemExit(f"missing required asset {rel}")

    dirs = sorted({(art / p).relative_to(art).parent.as_posix() for p in by_rel} |
                  {"", "Icons", "Icons/32", "Icons/16", "Wallpaper", "Splash", "Sprites", "UI"})
    dirs = sorted(d for d in dirs if d not in ("",))

    copy_pairs = []
    for i, rel in enumerate(sorted(by_rel), start=1):
        src = f"F{i:04d}.BIN"
        copy_pairs.append((src, "C:/Hermes/Art/" + rel))

    lines = ["// Auto-generated by shots/hermes-art/tools/build_overlay.py\n",
             "U0 ArtStage()\n{\n"]
    for d in ["C:/Hermes", "C:/Hermes/Art", "C:/Tmp"] + [f"C:/Hermes/Art/{x}" for x in dirs]:
        lines.append(f'  DirMk({hc_str(d)});\n')
    for src, dest in copy_pairs:
        lines.append(f'  Copy("C:/{src}",{hc_str(dest)});\n')
    lines.append('  FileWrite("C:/Tmp/HERMES_ART_STAGED","ok",2);\n')
    lines.append("}\nArtStage;\n")

    verify = r'''
U0 ArtResult(U8 *name,U8 *text)
{
  U8 *path=MStrPrint("C:/Tmp/%s",name);
  FileWrite(path,text,StrLen(text));
  Free(path);
}

U0 ArtVerify()
{
  CDC *dc;
  U8 *s;
  I64 ok=0;

  Cd("C:/Hermes/Art/Wallpaper");
  dc=GRRead("toh-temple-night");
  if (dc) {
    s=MStrPrint("GRRead non-NULL ptr=%X width=%d winternal=%d height=%d",
      dc,dc->width,dc->width_internal,dc->height);
    ArtResult("R_WALLPAPER_OK",s);
    Free(s);
    GrBlot(gr.dc,0,0,dc);
    ok++;
  } else
    ArtResult("R_WALLPAPER_NULL","GRRead returned NULL");
  Sleep(8000);
  if (dc) DCDel(dc);

  Cd("C:/Hermes/Art/Icons/32");
  dc=GRRead("hermes-chat");
  if (dc) {
    s=MStrPrint("GRRead non-NULL ptr=%X width=%d winternal=%d height=%d",
      dc,dc->width,dc->width_internal,dc->height);
    ArtResult("R_ICON_OK",s);
    Free(s);
    GrBlot(gr.dc,16,16,dc);
    ok++;
  } else
    ArtResult("R_ICON_NULL","GRRead returned NULL");
  Sleep(8000);
  if (dc) DCDel(dc);

  Cd("C:/Hermes/Art/Splash");
  dc=GRRead("toh-boot-splash");
  if (dc) {
    s=MStrPrint("GRRead non-NULL ptr=%X width=%d winternal=%d height=%d",
      dc,dc->width,dc->width_internal,dc->height);
    ArtResult("R_SPLASH_OK",s);
    Free(s);
    GrBlot(gr.dc,0,0,dc);
    ok++;
  } else
    ArtResult("R_SPLASH_NULL","GRRead returned NULL");
  Sleep(8000);
  if (dc) DCDel(dc);

  if (ok==3)
    ArtResult("R_ALL_OK","3/3 assets loaded and blitted");
  else
    ArtResult("R_FAIL","fewer than 3 assets loaded");
}
ArtVerify;
'''
    run_hc = ("".join(lines) + verify).encode("ascii")
    files_out = [("RUN.HC", run_hc)]
    for i, rel in enumerate(sorted(by_rel), start=1):
        files_out.append((f"F{i:04d}.BIN", by_rel[rel].read_bytes()))

    img = build(files_out)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_bytes(img)
    MANIFEST.write_text(json.dumps({
        "image_bytes": len(img),
        "art_files": len(by_rel),
        "required": required,
        "copy_pairs": copy_pairs,
        "run_hc_bytes": len(run_hc),
    }, indent=2))
    print(f"wrote {OUT.name} ({len(img)} bytes), {len(files_out)} FAT entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
