# First RE9 test — experimental v0.1.0

**Standing visual loading confirmed; movement testing is underway.** The user's 9 October screenshot shows Bela's face, hood, sleeves, gloves and dress in a rendered game scene with REFramework FreeCam enabled. All 80 installed native files match this build. The view does not establish movement, weapons, normal player cameras or covered feet. Evidence is in `reports/runtime_test_01.json`.

**Weapon update:** the user subsequently reports "weapon physics seem to be perfect" and supplies a handgun-holding screenshot. Hands/grip and visible wrist/sleeve/shoulder attachments look aligned in that pose. This is a positive weapon-handling report, with specific firing/reload/holster sequences not yet enumerated. Evidence is in `reports/runtime_test_02.json`. Walking/turning, crouching and stairs are the next garment/foot checks.

The ZIP replaces standard Grace asset slots with Bela geometry/materials on Grace's skeleton. It retains Grace's boots, static hair, a neutral face and a skinned dress. Smaller offline cloth artifacts remain; expressions, cloth simulation, authentic heels, alternate outfits and dedicated cutscene parts are unfinished.

Package, current location: [BelaGrace_RE9_Prototype_0.1.0.zip](<<LOCAL_MOD_MANAGER_PATH>). It is no longer in the workspace `dist` directory. Its SHA256 remains `83fdcaca860fc30d2dc10dab36c18b57beb46aba2dda769688147be23f4f9fc0`. The native/ZIP file list is in `reports/package_manifest.json`; that manifest's installation/test flags describe the earlier archive-creation state.

## Install through your existing Fluffy manager

1. Exit RE9. Select Resident Evil Requiem/RE9 in Fluffy Mod Manager.
2. Copy the ZIP into `<LOCAL_MOD_MANAGER_PATH>
3. Refresh the mod list and enable **Bela for Grace - Experimental v0.1.0**.
4. Keep GraceBun disabled as already confirmed. Select Grace's standard base outfit and set **Hair Strands OFF**.
5. Start/restart the game. The existing REFramework loose-file/texture loader settings are required and were inspected earlier; this package does not replace the framework.

The project created the ZIP locally; the user has installed it through Fluffy. No project tool wrote game or manager files. Use the ZIP as the sole representation of this mod; do not also copy the staging `natives` tree into the game. Keep the current build unchanged while collecting movement results.

## Test in this order

| Test | What to record |
|---|---|
| Load an ordinary Grace gameplay save | Game build, save/chapter, outfit, camera mode, active mods; whether the game loads and all parts change |
| Third-person idle, front/side/rear | Neck/hood, shoulders, wrists, pelvis coverage, hair cards, textures and boots |
| Walk, turn, run, stairs | Limb motion, skirt clipping, foot contact and shadows |
| Aim, fire, reload, holster | Hand grip, weapon/holster attachment and first-person arms |
| Crouch, interact, take damage | Dress/body/floor clipping, interaction alignment, unexpected mesh switching |

Send a front/side/rear screenshot or a short clip for an incorrect part or action. If loading crashes or fails, disable this mod through Fluffy and provide the newly written REFramework log. If only some parts change, include the outfit and camera mode. The installed game path is `<RE9_INSTALL_DIR>`.

A menu/model-viewer success does not establish a playable replacement. Cutscene, expressions, wetness, hair physics and alternative-outfit testing follow a stable ordinary-gameplay baseline.

## Roll back

Exit RE9 and disable **Bela for Grace - Experimental v0.1.0** in Fluffy. Official game archives are not supplied or replaced by this package. Preserve test logs/screenshots before retrying.

Latest results: handgun ADS is visible with hair/hood penetration; one cutscene is reported visually correct, including lighting, with static facial animation. See [runtime results](RUNTIME_TESTS.md). The separate [headwear candidate](HEADWEAR.md) is not installed; continue testing v0.1.0.

The next complete test build is v0.1.1: [ZIP](<<LOCAL_PROJECT_ROOT>/dist/BelaGrace_RE9_Prototype_0.1.1.zip>). Follow [its installation and test instructions](releases/0.1.1/README.txt). Disable v0.1.0 before enabling v0.1.1; no base mod or patch layering is required.

