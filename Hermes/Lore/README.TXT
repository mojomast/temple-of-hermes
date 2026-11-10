CODEX OF NOUS -- lore for THE TEMPLE OF HERMES
version 0.1.0 -- original flavor, written for this fork

FILES
  Glbls.HC    shared banner and version
  Codex.HC    sourced and original lore entries
  MOTD.HC     message of the day
  Oracle.HC   a parlor-game oracle, fiction only
  Eggs.HC     caduceus, capybara, flight scene, badge, hidden latch
  Load.HC     include this to load every file
  Install.HC  copy hook; does not edit Once.HC

LOAD
  #include "/Hermes/Lore/Load";

INSTALL
  #include "/Hermes/Lore/Install";
  then, at every boot:
  #include "~/Lore/Load";

RULES
  SOURCED entries print a public URL with the claim.
  ORIGINAL entries are new fiction for this fork, not Nous Research
  statements and not quotations from real people.

The full citation table is docs/LORE.md in the source tree.
