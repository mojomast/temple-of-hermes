# Hermes app template

Minimal HolyC app pair for TempleOS / TinkerOS / THE TEMPLE OF HERMES.

- `Load.HC` defines code only and is safe to include.
- `Run.HC` includes `Load.HC` and calls the entry point.

Copy this directory, rename `HermesTemplateMain`, and follow
`docs/HOLYC-BEST-PRACTICES.md`.

In the guest:

```holyc
#include "C:/Hermes/Apps/Template/Run.HC";
```

Expected output:

```text
THE TEMPLE OF HERMES - HolyC app template
Load.HC compiled; Run.HC launched it.
```
