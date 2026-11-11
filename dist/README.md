# Dist output

`dist/TempleOfHermes-0.1.2.ISO` is the 0.1.2 PC artifact built by the
in-guest `Adam/Hermes/MakeDistro` path (FAT32 overlay + `D:/RUN.HC`), not by a
host-side ISO remaster.

- size: 14,030,848 bytes
- sha256: `9afc98ed2bb15a3ff26ebaca12ea392079292df6667b3c1c527fdd30d80cdb13`
- volume id: `THE_TEMPLE_OF_HERMES`

This build adds the full-screen 18-entry Hermes home launcher, keeps
AutoComplete and the boot terminals off the icon grid, launches every app by
mouse click or shortcut key, and returns to the launcher when the app exits.

See `docs/ISO-BUILD.md` for the exact install/overlay/MakeDistro steps and how
to boot it under QEMU TCG. The ISO itself is gitignored and is not committed,
released, or deployed.
