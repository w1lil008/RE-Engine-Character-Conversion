# Protected v0.1.x rebuild — current procedure

Use `scripts/rebuild_v01.py --output build/rebuild_verify_new` with pinned
Python to regenerate all accepted natives in a fresh isolated directory.
Accepted prepared sidecars are hashed build inputs. The old
`scripts/pipeline.ps1 -Step Build` below writes original development staging.
`scripts/finalize_v01.py` verifies current rebuild/review evidence and creates
the patch stage; `scripts/package_mod.py --release-config config/releases/0.1.3.json`
creates a one-shot ZIP. Read `docs/STABILIZATION_V0.1.3.md` for exact commands
and limitations. Earlier instructions below remain as development history.

# Rebuild and validation procedure

The controlled v0.1.0 test package was created under `dist` and is now in the user's Fluffy `Games/RE9/Mods` directory. Its original SHA256 and all 80 installed native file hashes match. The user's first screenshot confirms standing visual loading; dynamic gameplay remains unverified. See [FIRST_TEST.md](FIRST_TEST.md) for the current ZIP location and remaining checks. Preserve the tested build while collecting results. Do not copy the staging directory directly into the game.

The second observation adds a positive user report for weapon handling and a visibly aligned handgun pose (`reports/runtime_test_02.json`). Locomotion, crouching, foot contact and specific firing/reload/holster sequences remain to be recorded. No native or package changes were made for either observation.

## Portable environment

`scripts/pipeline.ps1` always invokes `tools/blender-4.3.2-windows-x64/blender.exe` with factory startup. It never searches for global Blender. A Python 3.12 runtime with numpy and Pillow is needed; the wrapper defaults to the tested local Codex dependency runtime. Supply `-Python 'C:/path/python.exe'` on a different machine. Project-scoped zstandard is under `tools/python-deps`.

The saved Blender scene is editable for inspection and preparation. The current native build is generated from source assets and script/configuration inputs; arbitrary manual edits in that scene are not automatically exported back into the mod.

Repository archives are pinned by commit and SHA256 in `config/toolchain.lock.json`; extracted source directories and official portable Blender are already present locally. Restore a missing tool from the recorded upstream repository commit, verify its archive hash, and retain its license. Do not substitute newer tools silently.

## Stages

1. **Extract:** read official base/sub/patch/DLC archives, excluding installed mod PAKs; resolve names with the game's own filename list; choose latest official patches; extract selected resources and streaming companions into the project. Each extracted resource records archive, offset, byte length and SHA256. No original archive is written.
2. **Analyze:** parse source/target meshes, matrices, material declarations and texture dependencies. Resolve dependency names and extract them. The clothing selection includes the shared `ch02_0201_gpucloth` mesh and its MDF, outside Bela's immediate folder.
3. **Prepare:** portable Blender builds a BVH over Bela's body surface. Only `skirt_*` influences are initially replaced with barycentric body weights. Save this raw surface-transfer sidecar separately. The next step preserves the pelvis field, blends a broad lower-skirt field without foot influences, diffuses weights across garment topology for 40 steps, and adds an explicit radial clearance of up to 25 mm around the pelvis. Coincident vertices share weight nodes; geometry is not welded. Original geometry fitting weights remain separate from runtime weights. Source hashes and all preparation settings are checked before build.
4. **Build:** merge consistent original Grace bind definitions; fit source geometry through corresponding joint directions; remap/merge/normalize weights; combine body/garment with original Grace boots; partition triangles into target asset slots. Recompute normals/tangents, quantize tangent bytes explicitly, and export with the pinned native writer. Rebuild MDF variants with RE9 presets and relocated original boot materials, convert source TEX via DDS, and verify decompressed mip payloads. Extract original material dependencies and decode boot base textures for an honest preview.
5. **Preview:** reopen exported native meshes and generated MDFs, construct a neutral editable scene, render front/rear and a synthetic arm pose. This checks the actual staged binaries, not a separate prettier source model.
6. **Align:** render 14 synthetic fixtures covering neck/arms, steps, rear flexion, deep crouch, stride, leg spreading and uncovered ankle/leg inspection. Measure 92 known source-coincident skin groups in six poses and 1,450 exported rest-coincident garment groups across all 14 poses. Hidden clothing in diagnostic views is intentional. Review images and source segmentation before diagnosing holes. The current review is in `docs/ALIGNMENT.md`; numerical continuity does not prove collision-free cloth or game compatibility.
7. **Validate:** check native versions, hierarchy/inverse matrices, weights, indices, material agreement, texture dependencies, path safety and file hashes. This is an offline gate only.

```powershell
./scripts/pipeline.ps1 -Step AllOffline
```

Individual stages are `Extract`, `Analyze`, `Prepare`, `Build`, `Preview`, `Align`, `Validate`, `Test`. The wrapper has no deployment step. Packaging is a separate `scripts/package_mod.py` command, guarded by the manual assembled review and its signature over the validated native file set. A changed build requires a fresh review; do not manufacture approval by editing the gate. Successful binary validation does not override failed assembled visual review.

## Positioning versus segmentation

Original body cutouts under sleeves and the dress are expected. Mesh/material groups and separate Grace asset slots do not imply detached geometry. `reports/segmentation.json` counts all included body/clothing triangles across the unique output parts. Seam vertices are copied without changing coordinates at the split.

Actual failures include a surface piercing its covering garment, a joint pivot sitting outside its limb, a seam separating under a pose, or a heel passing below the original floor plane. Source baseline comparison, joint positions and assembled posed views establish these issues. A finite-coordinate test alone cannot.

The initial shoe fit compressed geometry below Grace's ankle pivot; visual review rejected its flattened high heels. The current functional fallback retains Grace's original boots, their original weights/materials and sole plane. Covered Bela foot triangles are masked from the build while the source remains intact. This is recorded explicitly in `reports/footwear_fit.json`. Authentic Bela heels need a separate footwear/IK pass.

## Later installation and first in-game test

The current alignment gate allows a local experimental Fluffy ZIP with one mod folder, 80 validated native files, `modinfo.ini`, a readme and an approximate Blender preview. Package contents, CRCs and payload hashes are checked after writing. No installation is automatic. Install with the existing Fluffy manager as described in [FIRST_TEST.md](FIRST_TEST.md), keeping original PAKs intact.

The user confirmed GraceBun is disabled. Use Grace's ordinary base outfit and Hair Strands OFF. Existing loader settings were inspected; do not replace REFramework blindly. Fully restart after enabling the test mod. Record the game build, outfit, camera mode, settings and active mods.

Test idle, walk, run, turn, crouch, stairs, aiming, firing, reloading, weapon holstering, item pickup, door interaction, damage and recovery. Check neck and wrists in first and third person; confirm correct grip, feet contacting the floor and no limb/skirt intersections. Check shadow casting separately. Only after normal gameplay passes, test face/lips/eyes, rain/blood/wetness, alternate outfits, damage meshes and cutscenes. Dedicated cutscene parts and runtime constraints may override normal gameplay assumptions.

Capture REFramework logs and front/side/rear images or a short clip for failed actions. A successful menu/model-viewer screenshot does not establish playable functionality. Roll back by disabling the eventual mod through Fluffy; never delete official archives or patch them manually.

A separate [headwear correction procedure](HEADWEAR.md) now produces two native hair candidates without changing the active staging directory or installed build. The tested cutscene's visual result and lighting are positively reported; facial animation remains static. See [runtime results](RUNTIME_TESTS.md) for exact scope.

For the complete v0.1.1 build, use `assemble_release.py --release-config config/releases/0.1.1.json`, then `package_mod.py --release-config config/releases/0.1.1.json`. The assembler validates the separate 80-file stage and combines the unchanged-body alignment evidence with the reviewed native hair correction. Native/report signatures bind the package to that reviewed stage. The ZIP is full and standalone, with only two assets changed; it must replace the old enabled mod. Existing ZIPs are not overwritten.
# Second hair correction / v0.1.2

The release recipe now selects `hair_validation`, `hair_review` and `hair_scope`
reports explicitly. Tagged diagnostics/exports/audits preserve the v0.1.1
reference while checking all cards and shoulder/arm poses. See
[HEADWEAR.md](HEADWEAR.md) for preparation commands and limitations.
After native and visual review:

```powershell
& 'python' ./scripts/assemble_release.py --release-config config/releases/0.1.2.json
& 'python' ./scripts/package_mod.py --release-config config/releases/0.1.2.json
```

The result is a complete 80-native-file mod plus metadata, not an overlay patch.
Existing version ZIPs cannot be overwritten. Neither command installs the mod.

