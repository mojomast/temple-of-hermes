# Dist output

`dist/TempleOfHermes-0.1.0.ISO` is the 0.1.0 PC artifact built by the
in-guest `Adam/Hermes/MakeDistro` path (FAT32 overlay + `D:/RUN.HC`), not by a
host-side ISO remaster.

- size: 14,020,608 bytes
- sha256: `83bc2bba8d4c65c4884e3c8d6b4239e09cdcf5eafdba1bcf47392ab3b941f79d`
- volume id: `THE_TEMPLE_OF_HERMES`

See `docs/ISO-BUILD.md` for the exact install/overlay/MakeDistro steps and how
to boot it under QEMU TCG. The ISO itself is gitignored and is not committed.
