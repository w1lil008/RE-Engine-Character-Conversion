BELA FOR GRACE - PROTOTYPE v0.1.3 - 10 October 2026

Complete standalone Fluffy Mod Manager package: 80 native assets.
Every native payload is identical to the user-tested v0.1.2 baseline.
This is a stabilization/documentation release; no blink, physics or animation
conversion is included. It does not need any earlier Bela package enabled.

INSTALL / REPLACE
1. Exit RE9. Preserve the v0.1.2 ZIP before changing enabled mods.
2. In Fluffy Mod Manager, select RE9 and disable the previous Bela release.
3. Place this ZIP in Games/RE9/Mods and refresh the mod list.
4. Enable only "Bela for Grace - Prototype v0.1.3". Keep GraceBun and conflicting
   Grace body/face/hair replacements disabled. Use the standard base outfit.
5. Set Hair Strands OFF. Retain the established REFramework loose-file/texture
   loading configuration used for the working baseline. Restart the game.

EVIDENCE
The v0.1.2 hair/hood ADS fix has recorded user acceptance with installed-file
hash verification. The user reports working gameplay, cutscenes, textures,
lighting, aiming and weapon handling in tested scenes. Full action-by-action
coverage is not established. v0.1.3 has fresh automated/offline validation but
has NOT itself been installed or runtime-tested by the engineering tools.
The supplied screenshot is v0.1.2 runtime evidence, not a new v0.1.3 test.

RELEASE CONTENTS
8 meshes, 31 material variants, 41 textures. Grace's 611-bone skeleton and
bind matrices are retained. Hair/hood weights and the thigh-clearance/dress
correction are preserved. Costume sleeve/glove gaps and source cutouts are
intentional. See CHANGELOG, KNOWN_LIMITATIONS and MANUAL_TEST_CHECKLIST.
BUILD_MANIFEST lists every native payload and source/configuration hashes.
Detailed engineering diagnostics stay in the project, outside this package.

ROLLBACK
Exit RE9, disable v0.1.3 in Fluffy, refresh and enable only v0.1.2 from the
preserved BelaGrace_RE9_Prototype_0.1.2.zip. Restore the same outfit/settings
and conflict exclusions. Do not stack releases or manually delete game data.
Disabling all Bela releases returns to the manager's original Grace assets.
Project tools have not changed official archives, installed mods or saves.

The exact known-working ZIP SHA256 is:
77693eef1878c4ae68a2e69b54521d0ca8f0f257be0713680e1539d50e253165
Project recovery copies: dist/BelaGrace_RE9_Prototype_0.1.2.zip and
build/checkpoints/accepted_0.1.2/BelaGrace_RE9_Prototype_0.1.2.zip.
Git source checkpoint: codex/accepted-v0.1.2 (prepared game-derived inputs
and binaries are local build/checkpoint files, intentionally outside Git).

Generated from the user's local owned games. Keep this prototype local.

