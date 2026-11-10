# Dist output

`dist/TempleOfHermes-0.1.1.ISO` is the 0.1.1 PC artifact built by the
in-guest `Adam/Hermes/MakeDistro` path (FAT32 overlay + `D:/RUN.HC`), not by a
host-side ISO remaster.

- size: 14,026,752 bytes
- sha256: `70ded88b90de9ff2f5fe43de562e99aeac2e329aa73b03a8eccbad4f07a1110f`
- volume id: `THE_TEMPLE_OF_HERMES`

This build fixes the 0.1.0 late-boot task-ring freeze and the five live-ISO
read-only state failures (BBS, Caduceus, Spoon, Token Rain, Dojo Duel).

See `docs/ISO-BUILD.md` for the exact install/overlay/MakeDistro steps and how
to boot it under QEMU TCG. The ISO itself is gitignored and is not committed,
released, or deployed.
