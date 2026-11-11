#!/usr/bin/env python3
"""Minimal MBR + FAT32 reader so we can extract files from a TinkerOS qcow2
after qemu-img convert, without root or nbd."""
from __future__ import annotations

import struct
import sys
from pathlib import Path


def _u16(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def _u32(b: bytes, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


class Fat32:
    def __init__(self, raw: Path, lba0: int = 0):
        self.f = raw.open("rb")
        self.base = lba0 * 512
        boot = self._read(0, 512)
        self.bps = _u16(boot, 11) or 512
        self.spc = boot[13] or 1
        self.reserved = _u16(boot, 14)
        self.nfats = boot[16]
        self.fat_sz = _u32(boot, 36)
        self.root_clus = _u32(boot, 44)
        self.fat_off = self.reserved * self.bps
        self.data_off = (self.reserved + self.nfats * self.fat_sz) * self.bps
        fat = self._read(self.fat_off, self.fat_sz * self.bps)
        self.fat = fat

    def close(self) -> None:
        self.f.close()

    def _read(self, off: int, n: int) -> bytes:
        self.f.seek(self.base + off)
        return self.f.read(n)

    def _fat(self, clus: int) -> int:
        o = clus * 4
        if o + 4 > len(self.fat):
            return 0x0FFFFFFF
        return _u32(self.fat, o) & 0x0FFFFFFF

    def _cluster_bytes(self, clus: int) -> bytes:
        off = self.data_off + (clus - 2) * self.spc * self.bps
        return self._read(off, self.spc * self.bps)

    def _chain(self, start: int) -> bytes:
        out = bytearray()
        clus = start
        seen = set()
        while 2 <= clus < 0x0FFFFFF8 and clus not in seen:
            seen.add(clus)
            out += self._cluster_bytes(clus)
            clus = self._fat(clus)
        return bytes(out)

    def listdir(self, clus: int | None = None) -> list[tuple[str, int, int, int]]:
        """Return (name, cluster, size, attr) for a directory cluster."""
        if clus is None:
            clus = self.root_clus
        data = self._chain(clus)
        entries: list[tuple[str, int, int, int]] = []
        lfn_parts: list[str] = []
        for i in range(0, len(data), 32):
            e = data[i : i + 32]
            if len(e) < 32:
                break
            if e[0] in (0x00, 0xE5):
                lfn_parts = []
                if e[0] == 0x00:
                    break
                continue
            if e[11] == 0x0F:
                raw = e[1:11] + e[14:26] + e[28:32]
                chars = []
                for j in range(0, len(raw), 2):
                    ch = raw[j] | (raw[j + 1] << 8)
                    if ch in (0x0000, 0xFFFF):
                        break
                    chars.append(chr(ch))
                lfn_parts.insert(0, "".join(chars))
                continue
            attr = e[11]
            cl = _u16(e, 26) | (_u16(e, 20) << 16)
            size = _u32(e, 28)
            if lfn_parts:
                name = "".join(lfn_parts)
            else:
                name83 = e[0:11].decode("ascii", "replace")
                n, ext = name83[:8].rstrip(), name83[8:].rstrip()
                name = f"{n}.{ext}" if ext else n
            lfn_parts = []
            if name in (".", ".."):
                continue
            entries.append((name, cl, size, attr))
        return entries

    def resolve(self, path: str) -> tuple[int, int, int] | None:
        parts = [p for p in path.replace("\\", "/").split("/") if p]
        clus = self.root_clus
        if not parts:
            return clus, 0, 0x10
        entries = self.listdir(clus)
        for i, part in enumerate(parts):
            match = None
            for name, c, size, attr in entries:
                if name.lower() == part.lower() or name.lower().rstrip(".") == part.lower():
                    match = (name, c, size, attr)
                    break
            if not match:
                return None
            if i == len(parts) - 1:
                return match[1], match[2], match[3]
            if not (match[3] & 0x10):
                return None
            entries = self.listdir(match[1])
        return None

    def read_file(self, path: str) -> bytes:
        got = self.resolve(path)
        if not got:
            raise FileNotFoundError(path)
        clus, size, attr = got
        if attr & 0x10:
            raise IsADirectoryError(path)
        data = self._chain(clus)
        return data[:size]

    def tree(self, clus: int | None = None, prefix: str = "") -> list[str]:
        out = []
        for name, c, size, attr in self.listdir(clus):
            p = f"{prefix}/{name}"
            out.append(f"{p} {'<DIR>' if attr & 0x10 else size}")
            if attr & 0x10:
                out.extend(self.tree(c, p))
        return out


def mbr_partitions(raw: Path) -> list[tuple[int, int, int]]:
    data = raw.read_bytes()[:512]
    if data[510:512] != b"\x55\xaa":
        # maybe a superfloppy FAT32
        return [(0, 0, (raw.stat().st_size // 512))]
    parts = []
    for i in range(4):
        e = data[0x1BE + i * 16 : 0x1BE + (i + 1) * 16]
        typ, lba, nsec = e[4], _u32(e, 8), _u32(e, 12)
        if typ and nsec:
            parts.append((typ, lba, nsec))
    return parts


def open_first_fat(raw: Path) -> Fat32:
    parts = mbr_partitions(raw)
    for typ, lba, _n in parts:
        if typ in (0x0B, 0x0C, 0x0E, 0x1C, 0x0F, 0x00):
            try:
                fs = Fat32(raw, lba)
                if fs.bps in (512, 1024, 2048, 4096) and 1 <= fs.spc <= 128:
                    return fs
            except Exception:
                continue
    # try LBA 0 anyway
    return Fat32(raw, 0)


def extract(raw: Path, guest_path: str, dest: Path) -> Path:
    fs = open_first_fat(raw)
    try:
        data = fs.read_file(guest_path)
    finally:
        fs.close()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: fat32_read.py RAW [PATH] [--tree] [--out FILE]")
        sys.exit(2)
    raw = Path(sys.argv[1])
    if "--tree" in sys.argv:
        fs = open_first_fat(raw)
        print("\n".join(fs.tree()[:400]))
        fs.close()
    elif len(sys.argv) >= 3:
        out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else Path("extracted.bin")
        extract(raw, sys.argv[2], out)
        print(f"wrote {out} ({out.stat().st_size} bytes)")
